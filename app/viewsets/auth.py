# app/viewsets/auth.py — endpoints de autenticação, registro, confirmação de e-mail, reset de senha, login social, 2FA.
import base64
import io
import logging
import secrets
from http.client import CREATED

import pyotp
import qrcode
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils import timezone
from google.auth.transport import requests
from google.oauth2 import id_token
from knox.models import AuthToken
from knox.views import LogoutView as KnoxLogoutView
from rest_framework import (generics, permissions, serializers,
                            status)
from rest_framework.decorators import (api_view, permission_classes)
from rest_framework.response import Response
from rest_framework.views import APIView

from app.constants import (RESET_PASSWORD_EMAIL_TEMPLATE)
from app.serializers import (LoginSerializer,
                             PreLoginSerializer,
                             RegisterSerializer, UserSerializer)
from app.logging_utils import audit_exception, audit_log
from app.utils import (create_limited_notification, initialize_user_chat, send_mail_confirmation_email)


logger = logging.getLogger(__name__)


class GoogleLoginView(APIView):

    def post(self, request):
        User = get_user_model()
        token = request.data.get('token')
        if not token:
            return Response({'error': 'Token é obrigatório.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            idinfo = id_token.verify_oauth2_token(token, requests.Request(), clock_skew_in_seconds=30)
            email = idinfo['email']
            name = idinfo.get('name', '')
            # picture = idinfo.get('picture', '')

            if not email:
                return Response({'error': 'Google token inválido: sem e-mail'}, status=status.HTTP_400_BAD_REQUEST)

            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email.split('@')[0],
                    'first_name': name,
                    'is_email_confirmed': True,
                }
            )
            if created:
                user.is_active = True
                user.save()

            audit_log('auth.google_login', user=user, message='Login com Google concluído', created=created)

            return initialize_user_chat(user)
        except Exception as e:
            audit_exception('auth.google_login', message='Falha no login com Google', exc=e, email=request.data.get('token'))
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ResetPasswordRequestAPI(APIView):
    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'error': 'Email é obrigatório.'}, status=status.HTTP_400_BAD_REQUEST)
        User = get_user_model()
        try:
            user = User.objects.get(email=email)
            token = secrets.token_urlsafe(32)
            user.reset_password_token = token
            user.reset_password_expiry = timezone.now() + timezone.timedelta(hours=1)
            user.save()
            reset_link = f"{settings.FRONTEND_URL}/reset-password/{token}"
            subject = "🔑 Redefinição de senha - Marriplan"
            plain_message = f"Redefina sua senha: {reset_link}"
            html_message = RESET_PASSWORD_EMAIL_TEMPLATE.format(
                email=user.email,
                reset_link=reset_link
            )
            send_mail(
                subject,
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=html_message,
            )
            return Response({'message': 'E-mail de redefinição enviado.'})
        except User.DoesNotExist:
            # Não revelar se o email existe ou não
            return Response({'message': 'E-mail de redefinição enviado.'})


class ResetPasswordConfirmAPI(APIView):
    def post(self, request):
        token = request.data.get('token')
        new_password = request.data.get('password')
        if not token or not new_password:
            return Response({'error': 'Token e nova senha são obrigatórios.'}, status=status.HTTP_400_BAD_REQUEST)
        User = get_user_model()
        try:
            user = User.objects.get(reset_password_token=token)
            if user.reset_password_expiry < timezone.now():
                return Response({'error': 'Token expirado.'}, status=status.HTTP_400_BAD_REQUEST)
            user.set_password(new_password)
            user.reset_password_token = None
            user.reset_password_expiry = None
            user.save()
            create_limited_notification(
                user=user,
                type='success',
                title='Senha alterada',
                message='Sua senha foi alterada com sucesso.',
                is_read=False,
            )
            return Response({'message': 'Senha redefinida com sucesso.'})
        except User.DoesNotExist:
            return Response({'error': 'Token inválido.'}, status=status.HTTP_400_BAD_REQUEST)


class ConfirmEmailAPI(APIView):
    def get(self, request):
        token = request.GET.get('token')
        User = get_user_model()
        try:
            user = User.objects.get(email_confirmation_token=token)
            if user.email_confirmation_expiry < timezone.now():
                return Response({'error': 'Token expirado.'}, status=400)
            user.is_email_confirmed = True
            user.is_active = True
            user.email_confirmation_token = None
            user.email_confirmation_expiry = None
            user.save()
            return Response({'message': 'Email confirmado com sucesso.'})
        except User.DoesNotExist:
            return Response({'error': 'Token inválido.'}, status=400)


class ResendConfirmationEmailAPI(APIView):
    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'error': 'Email é obrigatório.'}, status=status.HTTP_400_BAD_REQUEST)
        User = get_user_model()
        try:
            user = User.objects.get(email=email)
            if user.is_email_confirmed:
                return Response({'message': 'Email já confirmado.'}, status=status.HTTP_200_OK)
            send_mail_confirmation_email(user)
            return Response({'message': 'E-mail de confirmação reenviado.'}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({'error': 'Usuário não encontrado.'}, status=status.HTTP_404_NOT_FOUND)


class SignUpAPI(generics.GenericAPIView):
    """
    Register API endpoint.
    """
    serializer_class = RegisterSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        send_mail_confirmation_email(user)
        token = AuthToken.objects.create(user)
        audit_log('auth.register', user=user, message='Novo cadastro concluído', email=user.email)
        return Response({
            "user": UserSerializer(user, context=self.get_serializer_context()).data,
            "token": token[1]
        }, status=CREATED)


class PreLoginAPI(APIView):
    """
    Endpoint para autenticação inicial e verificação de 2FA.
    """

    def post(self, request):
        serializer = PreLoginSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except serializers.ValidationError as exc:
            audit_log(
                'auth.login',
                status='failed',
                message='Falha na validação inicial de login',
                email=request.data.get('email'),
                details=exc.detail,
            )
            if exc.detail.get('require_2fa'):
                return Response(exc.detail, status=status.HTTP_200_OK)
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.validated_data
        response = initialize_user_chat(user)
        audit_log('auth.login', user=user, message='Login concluído', email=user.email)
        return response


class SignInAPI(generics.GenericAPIView):
    """
    Login API endpoint.
    """
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except serializers.ValidationError as exc:
            audit_log(
                'auth.login',
                status='failed',
                message='Falha no login',
                email=request.data.get('email'),
                details=exc.detail,
            )
            raise
        user = serializer.validated_data
        if user.is_2fa_enabled:
            otp_code = request.data.get('otp_code')
            if not otp_code:
                audit_log('auth.login', status='failed', user=user, message='2FA requerido', email=user.email)
                return Response({'require_2fa': True, 'message': '2FA requerido.'}, status=200)
            totp = pyotp.TOTP(user.otp_secret)
            if not totp.verify(otp_code):
                audit_log('auth.login', status='failed', user=user, message='Código 2FA inválido', email=user.email)
                return Response({'error': 'Código 2FA inválido.'}, status=400)
        # Verificar se o usuário possui alguma sessão
        response = initialize_user_chat(user)
        audit_log('auth.login', user=user, message='Login concluído', email=user.email)
        return response


class LogoutAPI(KnoxLogoutView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, format=None):
        audit_log('auth.logout', user=request.user, message='Logout concluído')
        return super().post(request, format=format)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def generate_2fa_qr(request):
    user = request.user
    if not user.otp_secret:
        user.otp_secret = pyotp.random_base32()
        user.save()
    otp_uri = pyotp.totp.TOTP(user.otp_secret).provisioning_uri(
        name=user.email, issuer_name="Marriplan"
    )
    qr = qrcode.make(otp_uri)
    buf = io.BytesIO()
    qr.save(buf, format='PNG')
    image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    return Response({
        "otp_secret": user.otp_secret,
        "otp_uri": otp_uri,
        "qr_code_base64": image_base64
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def enable_2fa(request):
    user = request.user
    otp_code = request.data.get('otp_code')
    if not user.otp_secret:
        return Response({"error": "2FA não iniciado."}, status=400)
    totp = pyotp.TOTP(user.otp_secret)
    if totp.verify(otp_code):
        user.is_2fa_enabled = True
        user.save()
        if user.settings:
            user.settings.enable_2fa = True
            user.settings.save()
        create_limited_notification(
            user=user,
            type='success',
            title='2FA ativado',
            message='A autenticação em duas etapas foi ativada com sucesso.',
            is_read=False,
        )
        return Response({"message": "2FA ativado com sucesso."})
    return Response({"error": "Código OTP inválido."}, status=400)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def disable_2fa(request):
    user = request.user
    user.is_2fa_enabled = False
    user.otp_secret = None
    user.save()
    if user.settings:
        user.settings.enable_2fa = False
        user.settings.save()
    create_limited_notification(
        user=user,
        type='warning',
        title='2FA desativado',
        message='A autenticação em duas etapas foi desativada.',
        is_read=False,
    )
    return Response({"message": "2FA desativado."})
