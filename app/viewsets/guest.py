import io

import pandas as pd
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from rest_framework import (permissions, status, viewsets, filters)
from rest_framework.decorators import (action)
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

import re
from urllib.parse import quote_plus
from django.utils import timezone
from django.conf import settings

from app.models import (Guest, GuestConfirmationToken)
from app.serializers import (GuestSerializer)
from django.core.mail import send_mail
from app.utils import (
    MAX_GUESTS_PER_WEDDING,
    create_limited_notification,
    is_limit_reached,
    to_sentence_case,
    to_upper_camel_words,
)
from app.logging_utils import audit_log


class GuestViewSet(viewsets.ModelViewSet):
    serializer_class = GuestSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'email', 'phone']
    ordering_fields = ['name', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        # Se for noivo(a) ou convidado, vê todos os convidados do casamento vinculado ao wedding_profile
        if hasattr(user, 'wedding_profile'):
            return Guest.objects.filter(wedding_profile=user.wedding_profile).order_by('-created_at')
        # Se for convidado (sem wedding_profile), mas está cadastrado como Guest, buscar o wedding_profile pelo Guest
        guest = Guest.objects.filter(user=user).first()
        if guest and guest.wedding_profile:
            return Guest.objects.filter(wedding_profile=guest.wedding_profile).order_by('-created_at')
        # Caso não tenha vínculo, retorna apenas o próprio cadastro
        return Guest.objects.filter(user=user).order_by('-created_at')

    def perform_create(self, serializer):
        user = self.request.user
        wedding_profile = getattr(user, 'wedding_profile', None)
        if wedding_profile and is_limit_reached(Guest.objects.filter(wedding_profile=wedding_profile).count(), MAX_GUESTS_PER_WEDDING):
            raise ValidationError({'detail': 'Limite de 500 convidados atingido.'})
        if hasattr(user, 'wedding_profile'):
            instance = serializer.save(user=user, wedding_profile=user.wedding_profile)
        else:
            instance = serializer.save(user=user)
        audit_log('guest.create', user=user, obj=instance, message='Convidado criado')

    def perform_update(self, serializer):
        instance = serializer.save()
        audit_log('guest.update', user=self.request.user, obj=instance, message='Convidado atualizado')

    def perform_destroy(self, instance):
        audit_log('guest.delete', user=self.request.user, obj=instance, message='Convidado removido')
        instance.delete()

    @action(detail=False, methods=['get'], url_path='all', permission_classes=[permissions.IsAuthenticated])
    def all_guests(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = GuestSerializer(queryset, many=True)
        return Response({
            'results': serializer.data,
            'count': queryset.count(),
        })

    @action(detail=False, methods=['get'], url_path='download-model')
    def download_model(self, request):
        # Modelo padrão CSV
        columns = ['nome', 'telefone', 'whatsapp', 'email', 'alergias', 'acompanhantes', 'observacoes']
        df = pd.DataFrame(columns=columns)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="modelo_convidados.csv"'
        df.to_csv(response, index=False)
        return response

    @action(detail=False, methods=['post'], url_path='import', parser_classes=[MultiPartParser, FormParser])
    def import_guests(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({'detail': 'Arquivo não enviado.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            if file.name.endswith('.csv'):
                df = pd.read_csv(file)
            elif file.name.endswith('.xlsx'):
                df = pd.read_excel(file)
            else:
                return Response({'detail': 'Formato não suportado. Envie CSV ou Excel.'},
                                status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'detail': f'Erro ao ler arquivo: {e}'}, status=status.HTTP_400_BAD_REQUEST)
        errors = []
        created = 0
        wedding_profile = getattr(request.user, 'wedding_profile', None)
        current_count = Guest.objects.filter(wedding_profile=wedding_profile).count() if wedding_profile else 0
        for idx, row in df.iterrows():
            if wedding_profile and is_limit_reached(current_count, MAX_GUESTS_PER_WEDDING):
                errors.append({'row': idx + 2, 'error': 'Limite de 500 convidados atingido. Os registros restantes foram ignorados.'})
                break
            data = row.to_dict()
            data = {k: (v if pd.notnull(v) else None) for k, v in data.items()}
            # Normaliza nomes de colunas para os campos esperados pelo serializer
            data['name'] = to_upper_camel_words(data.get('name') or data.get('nome'))
            data['phone'] = data.get('phone') or data.get('telefone')
            # Normaliza campos opcionais: se vierem None, NaN ou vazio, vira string vazia
            for field in ['whatsapp', 'acompanhantes']:
                if field in data and (data[field] is None or str(data[field]).strip() == '' or pd.isna(data[field])):
                    data[field] = ''
            for field in ['alergias', 'observacoes']:
                if field in data and (data[field] is None or str(data[field]).strip() == '' or pd.isna(data[field])):
                    data[field] = ''
                else:
                    data[field] = to_sentence_case(data.get(field))
            serializer = GuestSerializer(data=data)
            if serializer.is_valid():
                # Verifica duplicidade de e-mail
                wedding_profile = getattr(request.user, 'wedding_profile', None)
                if data.get('email') and Guest.objects.filter(email=data['email'],
                                                              wedding_profile=wedding_profile).exists():
                    errors.append({'row': idx + 2, 'error': 'E-mail duplicado'})
                    continue
                # Salva explicitamente user e wedding_profile
                if wedding_profile:
                    serializer.save(user=request.user, wedding_profile=wedding_profile)
                else:
                    serializer.save(user=request.user)
                created += 1
                current_count += 1
            else:
                errors.append({'row': idx + 2, 'error': serializer.errors})
        if errors:
            return Response(
                {'detail': f'{created} convidados importados. Alguns registros possuem erro.', 'errors': errors},
                status=status.HTTP_207_MULTI_STATUS)
        return Response({'detail': f'{created} convidados importados com sucesso.'})

    @action(detail=False, methods=['get'], url_path='export')
    def export_guests(self, request):
        format = request.query_params.get('format', 'pdf')
        queryset = self.filter_queryset(self.get_queryset())
        data = GuestSerializer(queryset, many=True).data
        df = pd.DataFrame(data)
        df['status_rsvp'] = ''
        df['grupo'] = ''
        if format == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="convidados.csv"'
            df.to_csv(response, index=False)
            return response
        elif format == 'xlsx':
            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename="convidados.xlsx"'
            with pd.ExcelWriter(response, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            return response
        elif format == 'pdf':
            try:
                response = HttpResponse(content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename="convidados.pdf"'
                buffer = io.BytesIO()
                p = canvas.Canvas(buffer, pagesize=letter)
                width, height = letter
                y = height - 40
                p.setFont('Helvetica-Bold', 14)
                p.drawString(40, y, 'Lista de Convidados')
                y -= 30
                p.setFont('Helvetica', 10)
                # Cabeçalho
                columns = ['Nome', 'Telefone', 'Acompanhantes', 'Observações', 'Alergias']
                col_widths = [140, 80, 90, 120, 90]
                x = 40
                for i, col in enumerate(columns):
                    p.drawString(x, y, col)
                    x += col_widths[i]
                y -= 18
                # Linhas
                for _, row in df.iterrows():
                    x = 40
                    values = [
                        str(row.get('name', '')),
                        str(row.get('phone', '')),
                        str(row.get('acompanhantes', '')),
                        str(row.get('observacoes', '')),
                        str(row.get('alergias', '')),
                    ]
                    for i, value in enumerate(values):
                        p.drawString(x, y,
                                     value[:40] if i == 0 else value[:25])  # Permite nomes maiores na primeira coluna
                        x += col_widths[i]
                    y -= 15
                    if y < 60:
                        p.showPage()
                        y = height - 40
                        p.setFont('Helvetica', 10)
                p.save()
                pdf = buffer.getvalue()
                buffer.close()
                response.write(pdf)
                return response
            except Exception as e:
                return Response({'detail': f'Erro ao exportar PDF: {str(e)}'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response({'detail': 'Formato não suportado.'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='generate-confirmation-link')
    def generate_confirmation_link(self, request, pk=None):
        """Gera (ou reutiliza) um token de confirmação para o convidado e retorna a URL de confirmação."""
        guest = self.get_object()
        user = request.user
        wedding_profile = getattr(user, 'wedding_profile', None)
        if not ((wedding_profile and guest.wedding_profile == wedding_profile) or guest.user == user):
            return Response({'detail': 'Não autorizado.'}, status=status.HTTP_403_FORBIDDEN)

        token_obj = GuestConfirmationToken.objects.filter(guest=guest, used_at__isnull=True, expires_at__gt=timezone.now()).order_by('-created_at').first()
        if not token_obj:
            token_obj = GuestConfirmationToken.objects.create(guest=guest)

        token_str = str(token_obj.token)
        # Preferir Origin (frontend) se presente — útil em dev com front em :3000
        origin = None
        try:
            origin = request.headers.get('Origin') or request.META.get('HTTP_ORIGIN')
        except Exception:
            origin = None

        frontend_base = origin or getattr(settings, 'FRONTEND_URL', None)
        if frontend_base:
            confirmation_url = f"{str(frontend_base).rstrip('/')}/guests/confirm/{token_str}"
        else:
            confirmation_url = request.build_absolute_uri(f"/guests/confirm/{token_str}")

        whatsapp_link = None
        if guest.whatsapp:
            text = f"Olá {guest.name}! Por gentileza, confirme sua presença no nosso casamento respondendo este formulário: {confirmation_url} \n\n O convite formal será enviado via papelaria. Obrigado!"
            wa_clean = re.sub(r'\D', '', guest.whatsapp)
            whatsapp_link = f"https://wa.me/55{wa_clean}?text={quote_plus(text)}"

        return Response({
            'token': token_str,
            'confirmation_url': confirmation_url,
            'expires_at': token_obj.expires_at,
            'whatsapp_link': whatsapp_link,
        })

    @action(detail=False, methods=['get'], url_path='confirm/(?P<token>[^/.]+)/verify', permission_classes=[permissions.AllowAny])
    def confirm_verify(self, request, token=None):
        """Verifica se um token é válido (usado para a página frontend)."""
        try:
            token_obj = GuestConfirmationToken.objects.get(token=token)
        except GuestConfirmationToken.DoesNotExist:
            return Response({'valid': False}, status=status.HTTP_404_NOT_FOUND)

        if not token_obj.is_valid():
            return Response({'valid': False}, status=status.HTTP_400_BAD_REQUEST)

        guest = token_obj.guest
        return Response({'valid': True, 'guest_name': guest.name, 'guest_id': guest.id})

    @action(detail=False, methods=['post'], url_path='confirm/(?P<token>[^/.]+)', parser_classes=[JSONParser], permission_classes=[permissions.AllowAny])
    def confirm(self, request, token=None):
        """Recebe confirmações do frontend e atualiza o Guest e o token."""
        status_choice = request.data.get('status')
        if status_choice not in dict(Guest.STATUS_PRESENCA_CHOICES).keys():
            return Response({'detail': 'Status inválido.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token_obj = GuestConfirmationToken.objects.get(token=token)
        except GuestConfirmationToken.DoesNotExist:
            return Response({'detail': 'Token inválido.'}, status=status.HTTP_404_NOT_FOUND)

        if not token_obj.is_valid():
            return Response({'detail': 'Token inválido ou expirado.'}, status=status.HTTP_400_BAD_REQUEST)

        guest = token_obj.guest
        guest.status_presenca = status_choice
        guest.save()
        token_obj.mark_used(status_choice)

        # Criar notificação para os noivos (usuários vinculados ao wedding_profile)
        wedding_profile = getattr(guest, 'wedding_profile', None)
        if wedding_profile:
            users = []
            if hasattr(wedding_profile, 'users') and wedding_profile.users:
                users = list(wedding_profile.users.all())
            elif hasattr(wedding_profile, 'user') and wedding_profile.user:
                users = [wedding_profile.user]

            notif_title = '🎉 Confirmação de presença'
            notif_message = f'O convidado "{guest.name}" confirmou presença: {status_choice}.'
            for user in users:
                try:
                    create_limited_notification(
                        user=user,
                        type='info',
                        title=notif_title,
                        message=notif_message,
                        is_read=False,
                    )
                    # Enviar e-mail de aviso se e-mail estiver configurado
                    if user.email:
                        send_mail(
                            subject='Confirmação de presença - Marriplan',
                            message=notif_message,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[user.email],
                            fail_silently=True,
                        )
                except Exception:
                    # Não falhar a requisição principal por erro na notificação
                    pass

        return Response({'success': True, 'message': 'Presença atualizada com sucesso.', 'guest_id': guest.id, 'status': status_choice})
