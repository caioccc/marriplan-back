import base64
import io
import secrets
import uuid
from http.client import CREATED

import pyotp
import qrcode
from app.constants import (EMAIL_CONFIRMATION_HTML_TEMPLATE,
                           RESET_PASSWORD_EMAIL_TEMPLATE)
from app.core.models.llm.chat import (ChatRequest, generate_streaming_response,
                                      prepare_chat_messages)
from app.core.renderers import EventStreamRenderer
from app.core.services import QuestionService, SearchService
from app.core.services.search import SearchFilters
from app.models import (ChatMessage, Notification, UserSession, UserSettings,
                        UserWeddingProfile, WeddingSite, WeddingSiteHistory,
                        WeddingImage)
from app.serializers import (ChatMessageSerializer, LoginSerializer,
                             NotificationSerializer, PreLoginSerializer,
                             RegisterSerializer, UserSerializer,
                             UserSessionSerializer, UserSettingsSerializer,
                             UserWeddingProfileSerializer,
                             WeddingSiteHistorySerializer,
                             WeddingSiteSerializer, WeddingImageSerializer)
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from google.auth.transport import requests
from google.oauth2 import id_token
from knox.auth import TokenAuthentication
from knox.models import AuthToken
from rest_framework import generics, permissions, serializers, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes, parser_classes
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView
import cloudinary
import cloudinary.uploader
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated


# Configure Cloudinary (pode ser feito no settings.py)
cloudinary.config(
    cloud_name='freelancerinc',
    api_key='977733565746842',
    api_secret='q552mjrVeEmgPs1kUxfKzp4wz2o',
)


@api_view(['delete'])
@permission_classes([permissions.IsAuthenticated])
def delete_all_sessions(request):
    UserSession.objects.filter(user=request.user).delete()
    return Response({'message': 'Todas as sessões foram excluídas.'}, status=200)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_all_messages(request):
    ChatMessage.objects.filter(session__user=request.user).delete()
    Notification.objects.create(
        user=request.user,
        type='warning',
        title='Mensagens removidas',
        message='Todas as suas mensagens foram removidas.',
        is_read=False
    )
    return Response({'message': 'Todas as mensagens foram excluídas.'}, status=200)


class GoogleLoginView(APIView):

    def post(self, request):
        User = get_user_model()
        token = request.data.get('token')
        if not token:
            return Response({'error': 'Token é obrigatório.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            idinfo = id_token.verify_oauth2_token(token, requests.Request())
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

            return initialize_user_chat(user)
        except Exception as e:
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
            subject = "Redefinição de senha - Marriplan"
            plain_message = f"Redefina sua senha: {reset_link}"
            html_message = RESET_PASSWORD_EMAIL_TEMPLATE.format(
                username=user.username,
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
            Notification.objects.create(
                user=user,
                type='success',
                title='Senha alterada',
                message='Sua senha foi alterada com sucesso.',
                is_read=False
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


def send_mail_confirmation_email(user):
    token = secrets.token_urlsafe(32)
    user.email_confirmation_token = token
    user.is_active = False  # Desativar o usuário até que o email seja confirmado
    user.is_email_confirmed = False  # Garantir que o usuário não está confirmado
    user.email_confirmation_expiry = timezone.now() + timezone.timedelta(hours=24)
    user.save()
    confirmation_link = f"{settings.FRONTEND_URL}/register/confirm-email/?token={token}"
    subject = "Bem-vindo! Confirme seu e-mail para ativar sua conta"
    plain_message = f"Clique no link para confirmar: {confirmation_link}"
    html_message = EMAIL_CONFIRMATION_HTML_TEMPLATE.format(
        username=user.username,
        confirmation_link=confirmation_link
    )
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=html_message,
    )


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
        return Response({
            "user": UserSerializer(user, context=self.get_serializer_context()).data,
            "token": token[1]
        }, status=CREATED)


def initialize_user_chat(user):
    # Garante que o perfil de casamento existe
    UserWeddingProfile.objects.get_or_create(user=user)
    if not UserSession.objects.filter(user=user).exists():
        session = UserSession.objects.create(
            user=user,
            session_id=str(uuid.uuid4()),
            title="Sessão Inicial"
        )
        ChatMessage.objects.create(
            session=session,
            is_user=False,
            content=(
                "Olá! 👋 Eu sou o seu assistente virtual do **Marriplan**, aqui para ajudar você a organizar cada detalhe do seu casamento perfeito!\n\n"
                "Você pode me perguntar sobre:\n"
                "- ✅ Checklist pré-casamento (12 meses)\n"
                "- ✅ Configuração de RSVP e confirmação de presença\n"
                "- ✅ Lista de presentes e organização de convidados\n"
                "- ✅ Agenda do dia do casamento\n"
                "- ✅ Dicas de fornecedores, decoração e muito mais!\n\n"
                "**Como posso ajudar você hoje?**  \n"
                "Exemplos:\n\n"
                "- \"Como montar um checklist de 12 meses?\"\n"
                "- \"Preciso de ideias para uma lista de presentes criativa.\"\n"
                "- \"Como criar um formulário de RSVP eficaz?\""
            )
        )
    if not user.settings:
        user.settings = UserSettings.objects.create()
        user.save()
    return Response({
        "user": UserSerializer(user).data,
        "token": AuthToken.objects.create(user)[1],
    }, status=status.HTTP_200_OK)


class PreLoginAPI(APIView):
    """
    Endpoint para autenticação inicial e verificação de 2FA.
    """

    def post(self, request):
        serializer = PreLoginSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except serializers.ValidationError as exc:
            if exc.detail.get('require_2fa'):
                return Response(exc.detail, status=status.HTTP_200_OK)
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.validated_data
        return initialize_user_chat(user)


class SignInAPI(generics.GenericAPIView):
    """
    Login API endpoint.
    """
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data
        if user.is_2fa_enabled:
            otp_code = request.data.get('otp_code')
            if not otp_code:
                return Response({'require_2fa': True, 'message': '2FA requerido.'}, status=200)
            totp = pyotp.TOTP(user.otp_secret)
            if not totp.verify(otp_code):
                return Response({'error': 'Código 2FA inválido.'}, status=400)
        # Verificar se o usuário possui alguma sessão
        return initialize_user_chat(user)


class MainUser(generics.RetrieveAPIView):
    """
    Get user API endpoint.
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = [
        permissions.IsAuthenticated
    ]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class UserSettingsAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        settings_obj = request.user.settings
        user = request.user
        if not settings_obj:
            settings_obj = UserSettings.objects.create()
            user.settings = settings_obj
            user.save()
        serializer = UserSettingsSerializer(settings_obj)
        return Response(serializer.data)

    def patch(self, request):
        settings = self.request.user.settings
        user = request.user
        if not settings:
            settings = UserSettings.objects.create()
            user.settings = settings
            user.save()
        serializer = UserSettingsSerializer(settings, data={
            'language': request.data.get('language', settings.language),
            'theme': request.data.get('theme', settings.theme),
            'enable_2fa': request.data.get('enable_2fa', False)
        }, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class UserSessionViewSet(viewsets.ModelViewSet):
    serializer_class = UserSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return UserSession.objects.filter(user=self.request.user)
        return UserSession.objects.none()

    def perform_create(self, serializer):
        existing_session = UserSession.objects.filter(
            user=self.request.user,
            messages__isnull=True
        ).first()

        if existing_session:
            existing_session.session_id = str(uuid.uuid4())
            existing_session.updated_at = timezone.now()
            existing_session.save()
            self.existing_session = existing_session
        else:
            session_id = str(uuid.uuid4())
            serializer.validated_data['session_id'] = session_id
            serializer.validated_data['title'] = f"Sessão Inicial - {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
            self.existing_session = serializer.save(user=self.request.user)
            # criar mensagem default da IA
            ChatMessage.objects.create(
                session=self.existing_session,
                is_user=False,
                content=(
                    "Olá! 👋 Eu sou o seu assistente virtual do **Marriplan**, aqui para ajudar você a organizar cada detalhe do seu casamento perfeito!\n\n"
                    "Você pode me perguntar sobre:\n"
                    "- ✅ Checklist pré-casamento (12 meses)\n"
                    "- ✅ Configuração de RSVP e confirmação de presença\n"
                    "- ✅ Lista de presentes e organização de convidados\n"
                    "- ✅ Agenda do dia do casamento\n"
                    "- ✅ Dicas de fornecedores, decoração e muito mais!\n\n"
                    "**Como posso ajudar você hoje?**  \n"
                    "Exemplos:\n\n"
                    "- \"Como montar um checklist de 12 meses?\"\n"
                    "- \"Preciso de ideias para uma lista de presentes criativa.\"\n"
                    "- \"Como criar um formulário de RSVP eficaz?\""
                )
            )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)  # Valida os dados antes de acessar validated_data
        self.perform_create(serializer)
        return Response(
            UserSessionSerializer(self.existing_session).data,
            status=status.HTTP_200_OK if hasattr(self, 'existing_session') else status.HTTP_201_CREATED
        )

    @action(detail=False, methods=['delete'], url_path='delete-by-session-id/(?P<session_id>[^/]+)',
            permission_classes=[permissions.IsAuthenticated])
    def delete_by_session_id(self, request, session_id=None):
        if not session_id:
            return Response({"error": "session_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            session = UserSession.objects.get(session_id=session_id, user=request.user)
            session.delete()
            return Response({"message": "Session deleted successfully."}, status=status.HTTP_200_OK)
        except UserSession.DoesNotExist:
            return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)


class ChatMessageViewSet(viewsets.ModelViewSet):
    serializer_class = ChatMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return ChatMessage.objects.filter(session__user=self.request.user)
        return ChatMessage.objects.none()

    def partial_update(self, request, pk=None):
        user = request.user
        try:
            message = ChatMessage.objects.get(pk=pk, session__user=user)
        except ChatMessage.DoesNotExist:
            return Response({"error": "Mensagem não encontrada."}, status=status.HTTP_404_NOT_FOUND)

        new_content = request.data.get("content")
        if not new_content:
            return Response({"error": "Conteúdo é obrigatório."}, status=status.HTTP_400_BAD_REQUEST)

        # remove a mensagem
        ChatMessage.objects.filter(pk=pk).delete()

        # Remove mensagens posteriores na mesma sessão
        ChatMessage.objects.filter(
            session=message.session,
            created_at__gt=message.created_at
        ).delete()

        return Response(ChatMessageSerializer(message).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch'], url_path='update-title', permission_classes=[permissions.IsAuthenticated])
    def update_title(self, request, session_id=None):
        try:
            session = UserSession.objects.get(session_id=session_id, user=request.user)
        except UserSession.DoesNotExist:
            return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

        new_title = request.data.get('title')
        if not new_title:
            return Response({"error": "Title is required."}, status=status.HTTP_400_BAD_REQUEST)

        session.title = new_title
        session.save()

        return Response({"message": "Title updated successfully.", "session": UserSessionSerializer(session).data},
                        status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='stream-message', permission_classes=[permissions.IsAuthenticated],
            parser_classes=[JSONParser],
            renderer_classes=[EventStreamRenderer, JSONRenderer])
    def stream_message(self, request):
        session_id = request.data.get('session_id')
        user_message = request.data.get('content')

        if not session_id or not user_message:
            return Response({"error": "session_id and content are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            session = UserSession.objects.get(session_id=session_id, user=request.user)
        except UserSession.DoesNotExist:
            return Response({"error": "Invalid session_id."}, status=status.HTTP_404_NOT_FOUND)

        # Fetch the chat history for the session
        chat_history = ChatMessage.objects.filter(session=session).order_by('created_at')
        history = [
            {"role": "user" if msg.is_user else "assistant", "content": msg.content}
            for msg in chat_history
        ]

        # Preservar mensagem original
        original_message = user_message

        # Detectar intenção do usuário
        intent = self._detect_intent(user_message, session)

        # Se for pedido de questão, processar antes
        if intent['type'] == 'request_question':
            context = self._handle_question_request(intent['filters'], session, request.user)
            if context:
                # Adicionar contexto à mensagem para a LLM
                user_message = f"{context}\n\nMensagem original do usuário: {user_message}"

        # Se for resposta a questão, verificar
        elif intent['type'] == 'answer_question':
            context = self._handle_answer(intent['answer'], session, request.user)
            if context:
                user_message = f"{context}\n\nResposta do usuário: {intent['answer']}"

        # Se for referência a questão anterior
        elif intent['type'] == 'reference_previous_question':
            context = self._handle_question_reference(intent, session, request.user)
            if context:
                user_message = f"{context}\n\nMensagem original: {user_message}"

        # Prepare chat messages
        chat_request = ChatRequest(current_message=user_message, history=history)
        chat_messages = prepare_chat_messages(chat_request)

        # Stream response
        response = StreamingHttpResponse(
            generate_streaming_response(chat_messages, session, original_message),
            content_type="text/event-stream"
        )
        response['Cache-Control'] = 'no-cache'
        return response

    @action(detail=False, methods=['post'], url_path='send-message', permission_classes=[permissions.IsAuthenticated])
    def send_message(self, request):
        session_id = request.data.get('session_id')
        user_message = request.data.get('content')

        if not session_id or not user_message:
            return Response({"error": "session_id and content are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            session = UserSession.objects.get(session_id=session_id, user=request.user)
        except UserSession.DoesNotExist:
            return Response({"error": "Invalid session_id."}, status=status.HTTP_404_NOT_FOUND)

        # Save the user's message
        user_chat_message = ChatMessage.objects.create(
            session=session,
            is_user=True,
            content=user_message
        )

        # Simulate an AI response
        ai_response = f"Response to: {user_message}"

        # Save the AI's response
        ai_chat_message = ChatMessage.objects.create(
            session=session,
            is_user=False,
            content=ai_response
        )

        return Response({
            "user_message": ChatMessageSerializer(user_chat_message).data,
            "ai_response": ChatMessageSerializer(ai_chat_message).data
        }, status=status.HTTP_201_CREATED)

    def _detect_intent(self, message: str, session: UserSession) -> dict:
        """
        Detecta a intenção do usuário na mensagem para contexto de planejamento de casamentos.
        """
        message_lower = message.lower()

        # Palavras-chave de cada área do planejamento de casamento
        checklist_keywords = ["checklist", "pré-casamento", "preparativos", "12 meses", "organizar casamento"]
        rsvp_keywords = ["rsvp", "confirmação de presença", "confirmar presença", "lista de convidados"]
        presentes_keywords = ["lista de presentes", "presentes", "sugestão de presentes", "gift list"]
        agenda_keywords = ["agenda", "cronograma", "horário", "programação", "roteiro do dia"]
        fornecedores_keywords = ["fornecedor", "buffet", "decoração", "fotógrafo", "dj", "cerimonial", "local", "orçamento", "contratar", "serviço"]
        dicas_keywords = ["dica", "ideia", "inspiração", "cerimônia", "festa", "decoração", "tema", "tendência"]

        # Detectar intenção principal
        if any(word in message_lower for word in checklist_keywords):
            return {"type": "checklist"}
        if any(word in message_lower for word in rsvp_keywords):
            return {"type": "rsvp"}
        if any(word in message_lower for word in presentes_keywords):
            return {"type": "presentes"}
        if any(word in message_lower for word in agenda_keywords):
            return {"type": "agenda"}
        if any(word in message_lower for word in fornecedores_keywords):
            return {"type": "fornecedores"}
        if any(word in message_lower for word in dicas_keywords):
            return {"type": "dicas"}

        # Se não encontrou, retorna como chat genérico
        return {"type": "chat"}

    def _extract_filters(self, message: str) -> dict:
        """
        Extrai filtros da mensagem do usuário para contexto de casamento.
        """
        filters = {}
        # Exemplo: detectar mês, número de convidados, tipo de cerimônia, orçamento, etc.
        import re

        # Detectar número de convidados
        convidados_match = re.search(r'(\d+)\s*(convidados|pessoas)', message)
        if convidados_match:
            filters['convidados'] = int(convidados_match.group(1))
        # Detectar orçamento
        orcamento_match = re.search(r'\b(R\$|reais|mil)\s*(\d+[\.,]?\d*)', message)
        if orcamento_match:
            filters['orcamento'] = orcamento_match.group(0)
        # Detectar mês ou data
        meses = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
        for mes in meses:
            if mes in message:
                filters['mes'] = mes
                break
        return filters

    def _handle_question_request(self, filters: dict, session: UserSession, user) -> str:
        """
        Processa pedido de informação sobre planejamento de casamento e retorna contexto para a LLM.
        """
        # Exemplo de contexto para a LLM baseado nos filtros extraídos
        context_lines = []
        if 'convidados' in filters:
            context_lines.append(f"O usuário informou que terá cerca de {filters['convidados']} convidados.")
        if 'orcamento' in filters:
            context_lines.append(f"O orçamento estimado informado pelo usuário é {filters['orcamento']}.")
        if 'mes' in filters:
            context_lines.append(f"O casamento está previsto para o mês de {filters['mes']}.")

        # Adicionar instrução para a LLM
        context_lines.append(
            "Lembre-se: Responda de forma prática, objetiva e sempre focada em planejamento de casamentos. "
            "Seja detalhado e traga dicas úteis para o usuário organizar o evento, conforme o filtro informado. "
            "Se não houver filtro, responda de forma geral sobre o tema solicitado."
        )
        return "\n".join(context_lines) if context_lines else "Responda de forma detalhada e prática sobre o tema de planejamento de casamentos solicitado pelo usuário."

    def _handle_answer(self, answer: str, session: UserSession, user) -> str:
        """
        Não há mais verificação de resposta de questão. Apenas retorna mensagem padrão.
        """
        return "Atualmente não há verificação de respostas, pois o assistente Marriplan não trabalha mais com perguntas e respostas de provas. Se precisar de ajuda com planejamento de casamento, envie sua dúvida!"

    def _handle_question_reference(self, intent: dict, session: UserSession, user) -> str:
        """
        Não há mais referência a questões anteriores. Retorna mensagem padrão.
        """
        return "O assistente Marriplan não mantém histórico de questões. Por favor, envie sua dúvida sobre planejamento de casamento."

    def _format_questions_summary(self, questions_history: list) -> str:
        """
        Não há mais resumo de questões. Função mantida apenas para compatibilidade.
        """
        return "(Sem histórico de questões. O assistente Marriplan responde apenas dúvidas sobre planejamento de casamento.)"

    def _format_knowledge_refs(self, refs: list) -> str:
        """
        Não há mais referências de conhecimento. Função mantida apenas para compatibilidade.
        """
        return "(Sem referências específicas. Para dicas e fornecedores, envie sua dúvida!)"


class UserViewSet(viewsets.ModelViewSet):
    """
    User viewset
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = [
        permissions.IsAuthenticated
    ]
    serializer_class = UserSerializer

    def get_queryset(self):
        User = get_user_model()
        queryset = User.objects.all()
        name = self.request.query_params.get('name', None)
        if name is not None:
            queryset = queryset.filter(name__icontains=name)
        return queryset

    @action(detail=False, methods=['patch'], url_path='update-profile',
            permission_classes=[permissions.IsAuthenticated])
    def update_profile(self, request):
        User = get_user_model()
        user = request.user
        username = request.data.get('username')
        name = request.data.get('name')

        if username:
            if User.objects.exclude(pk=user.pk).filter(username=username).exists():
                return Response({'error': 'Username já está em uso.'}, status=status.HTTP_400_BAD_REQUEST)
            user.username = username

        if name:
            user.first_name = name

        user.save()
        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)


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
        Notification.objects.create(
            user=user,
            type='success',
            title='2FA ativado',
            message='A autenticação em duas etapas foi ativada com sucesso.',
            is_read=False
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
    Notification.objects.create(
        user=user,
        type='warning',
        title='2FA desativado',
        message='A autenticação em duas etapas foi desativada.',
        is_read=False
    )
    return Response({"message": "2FA desativado."})


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('is_read', '-created_at')

    @action(detail=False, methods=['get'])
    def unread(self, request):
        queryset = self.get_queryset().filter(is_read=False).order_by('-created_at')
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({'status': 'Todas marcadas como lidas'})

    @action(detail=False, methods=['post'])
    def mark_all_unread(self, request):
        self.get_queryset().filter(is_read=True).update(is_read=False)
        return Response({'status': 'Todas marcadas como não lidas'})

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'Marcada como lida'})

    @action(detail=True, methods=['post'])
    def mark_unread(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = False
        notification.save()
        return Response({'status': 'Marcada como não lida'})

    @action(detail=False, methods=['delete'], url_path='delete-all')
    def delete_all(self, request):
        self.get_queryset().delete()
        return Response({'status': 'Todas notificações removidas'})


class UserWeddingProfileViewSet(viewsets.ModelViewSet):
    serializer_class = UserWeddingProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserWeddingProfile.objects.filter(user=self.request.user)

    def get_object(self):
        # Garante que cada usuário só acessa o próprio perfil
        obj, _ = UserWeddingProfile.objects.get_or_create(user=self.request.user)
        return obj

    def list(self, request, *args, **kwargs):
        # Retorna sempre o perfil único do usuário
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

class WeddingSiteViewSet(viewsets.ModelViewSet):
    serializer_class = WeddingSiteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return WeddingSite.objects.filter(user=self.request.user)

    def get_object(self):
        try:
            return WeddingSite.objects.get(user=self.request.user)
        except WeddingSite.DoesNotExist:
            return None

    def list(self, request, *args, **kwargs):
        instance = self.get_object()
        if not instance:
            return Response({'detail': 'Nenhum site encontrado para este usuário.'}, status=404)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if not instance:
            return Response({'detail': 'Nenhum site encontrado para este usuário.'}, status=404)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        user = request.user
        profile = getattr(user, 'wedding_profile', None)
        req_data = request.data.copy()
        if profile and (profile.nome_noivo or profile.nome_noiva):
            from django.utils.text import slugify
            base = f"{profile.nome_noivo or ''}-{profile.nome_noiva or ''}".strip('-').replace(' ', '-').lower()
            slug = slugify(base)
            original_slug = slug
            i = 1
            while WeddingSite.objects.filter(url_slug=slug).exists():
                slug = f"{original_slug}-{i}"
                i += 1
            req_data['url_slug'] = slug
        else:
            req_data['url_slug'] = str(uuid.uuid4())[:8]
        req_data['user'] = user.id
        serializer = self.get_serializer(data=req_data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        # Histórico de criação
        site = WeddingSite.objects.get(pk=serializer.instance.pk)

        WeddingSiteHistory.objects.create(site=site, action='create', performed_by=user, snapshot=WeddingSiteSerializer(site).data)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def publish(self, request):
        site = self.get_object()
        if not site:
            return Response({'detail': 'Nenhum site encontrado para este usuário.'}, status=404)
        site.status = 'published'
        site.last_published_at = timezone.now()
        site.save()
        WeddingSiteHistory.objects.create(site=site, action='publish', performed_by=request.user, snapshot=WeddingSiteSerializer(site).data)
        return Response({'status': 'published'})

    @action(detail=False, methods=['post'])
    def unpublish(self, request):
        site = self.get_object()
        if not site:
            return Response({'detail': 'Nenhum site encontrado para este usuário.'}, status=404)
        site.status = 'draft'
        site.save()
        WeddingSiteHistory.objects.create(site=site, action='unpublish', performed_by=request.user, snapshot=WeddingSiteSerializer(site).data)
        return Response({'status': 'draft'})

    @action(detail=False, methods=['get'])
    def metrics(self, request):
        site = self.get_object()
        if not site:
            return Response({'detail': 'Nenhum site encontrado para este usuário.'}, status=404)
        return Response({
            'visits': site.visits,
            'rsvp_count': site.rsvp_count,
            'rsvp_conversion': site.rsvp_conversion,
            'last_visitor': site.last_visitor,
            'last_visitor_at': site.last_visitor_at,
        })

    @action(detail=False, methods=['get'])
    def preview(self, request):
        site = self.get_object()
        if not site:
            return Response({'detail': 'Nenhum site encontrado para este usuário.'}, status=404)
        # Retorna todos os campos relevantes do modelo
        return Response(WeddingSiteSerializer(site).data)

    def update(self, request, *args, **kwargs):
        # Atualiza o WeddingSite do usuário autenticado
        instance = self.get_object()
        if not instance:
            return Response({'detail': 'Nenhum site encontrado para este usuário.'}, status=404)
        data = request.data.copy()
        data['url_slug'] = instance.url_slug  # Mantém o slug existente
        data['user'] = instance.user.id
        # Atualiza galeria se vier IDs
        gallery_ids = data.pop('gallery', None)
        serializer = self.get_serializer(instance, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        if gallery_ids is not None:
            instance.gallery.set(gallery_ids)
        WeddingSiteHistory.objects.create(site=instance, action='edit', performed_by=request.user, snapshot=WeddingSiteSerializer(instance).data)
        return Response(serializer.data)

class WeddingSiteHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WeddingSiteHistorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return WeddingSiteHistory.objects.filter(site__user=self.request.user).order_by('-created_at')


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def public_wedding_site(request, slug):
    try:
        site = get_object_or_404(WeddingSite, url_slug=slug)
        if site.status != 'published':
            return Response({'detail': 'Site não publicado.'}, status=404)
        user = site.user
        # Incrementa visitas
        site.visits += 1
        site.save(update_fields=['visits'])
        data = WeddingSiteSerializer(site).data
        data['user'] = user.username
        data['wedding_profile'] = UserWeddingProfileSerializer(user.wedding_profile).data if hasattr(user, 'wedding_profile') else None
        return Response(data)
    except Exception as e:
        import logging
        logging.exception(f"Erro ao acessar site público: {slug}")
        return Response({'detail': 'Site não encontrado ou indisponível.'}, status=404)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_cloudinary(request):
    file = request.FILES.get('file')
    folder = request.data.get('folder', 'wedding-site')
    if not file:
        return Response({'error': 'Arquivo não enviado.'}, status=status.HTTP_400_BAD_REQUEST)
    if file.size > 10 * 1024 * 1024:
        return Response({'error': 'A imagem deve ter no máximo 10MB.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        result = cloudinary.uploader.upload(
            file,
            folder=folder,
            resource_type='image',
            overwrite=True,
            transformation=[{'width': 1200, 'height': 600, 'crop': 'limit'}] if folder == 'wedding-hero' else [{'width': 600, 'height': 400, 'crop': 'limit'}]
        )
        # Cria WeddingImage
        image = WeddingImage.objects.create(
            url=result['secure_url'],
            id_cloudinary=result['public_id'],
            folder=folder,
            in_use=True
        )
        return Response(WeddingImageSerializer(image).data)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def delete_cloudinary_image(request):
    public_id = request.data.get('public_id')
    if not public_id:
        return Response({'error': 'public_id é obrigatório.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        result = cloudinary.uploader.destroy(public_id)
        if result.get('result') == 'ok':
            WeddingImage.objects.filter(id_cloudinary=public_id).delete()
            return Response({'status': 'deleted'})
        return Response({'error': 'Erro ao deletar imagem no Cloudinary.'}, status=500)
    except Exception as e:
        return Response({'error': str(e)}, status=500)
