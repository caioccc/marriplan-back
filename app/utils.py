import logging
import secrets
import uuid
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from knox.models import AuthToken
from rest_framework import (status)
from rest_framework.response import Response

from app.constants import CHECKLIST_TASK_REMINDER_EMAIL_TEMPLATE, EMAIL_CONFIRMATION_HTML_TEMPLATE, \
    EMAIL_WEDDING_SITE_CREATE_SUBJECT, EMAIL_WEDDING_SITE_CREATE_BODY, EMAIL_WEDDING_SITE_UPDATE_SUBJECT, \
    EMAIL_WEDDING_SITE_UPDATE_BODY
from app.models import ChecklistTask, ChecklistTaskNotification, Notification, UserWeddingProfile, UserSession, \
    ChatMessage, UserSettings
from app.serializers import UserSerializer


def check_and_send_checklist_reminders(user):
    now = timezone.now()
    days_before = 3
    target_date = now + timedelta(days=days_before)
    tasks = ChecklistTask.objects.filter(
        user=user,
        due_date=target_date.date(),
        status__in=['pending', 'in_progress']
    )
    for task in tasks:
        if Notification.objects.filter(
                user=user,
                title='⏰ Lembrete de tarefa',
                message__contains=task.description,
                is_read=False
        ).exists():
            continue
        if ChecklistTaskNotification.objects.filter(task=task, user=user, scheduled_for=target_date.date()).exists():
            continue
        try:
            ChecklistTaskNotification.objects.create(
                task=task,
                user=user,
                scheduled_for=target_date,
                sent=True,
                sent_at=now
            )
            Notification.objects.create(
                user=user,
                type='info',
                title='⏰ Lembrete de tarefa',
                message=f'A tarefa "{task.description}" vence em 3 dias. Não se esqueça de concluir!',
                is_read=False
            )
            if user.email:
                html_message = CHECKLIST_TASK_REMINDER_EMAIL_TEMPLATE.format(
                    email=user.email,
                    description=task.description,
                    due_date=task.due_date.strftime('%d/%m/%Y')
                )
                send_mail(
                    subject='⏰ Lembrete: Tarefa do checklist vence em 3 dias',
                    message=f'A tarefa "{task.description}" vence em 3 dias. Não se esqueça de concluir!',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    html_message=html_message,
                    fail_silently=True,
                )
        except Exception as e:
            logging.error(f'Erro ao criar lembrete/checklist/email para o usuário {user.id} e tarefa {task.id}: {e}',
                          exc_info=True)


def notify_gift_status_change(gift, action, message=None):
    """
    Notifica os noivos por Notification e email ao marcar/desmarcar presente.
    action: 'purchased' ou 'unmarked'
    message: mensagem livre do comprador (opcional)
    """
    from app.constants import EMAIL_GIFT_PURCHASED_SUBJECT, EMAIL_GIFT_PURCHASED_BODY, EMAIL_GIFT_UNMARKED_SUBJECT, \
        EMAIL_GIFT_UNMARKED_BODY
    from app.models import Notification
    wedding_profile = getattr(gift, 'wedding_profile', None)
    if not wedding_profile:
        return
    # Suporte a wedding_profile.user (um noivo) ou wedding_profile.users (muitos)
    users = []
    if hasattr(wedding_profile, 'users') and wedding_profile.users:
        users = list(wedding_profile.users.all())
    elif hasattr(wedding_profile, 'user') and wedding_profile.user:
        users = [wedding_profile.user]
    for user in users:
        if action == 'purchased':
            subject = EMAIL_GIFT_PURCHASED_SUBJECT
            html_message = EMAIL_GIFT_PURCHASED_BODY.format(
                gift_name=gift.name,
                purchased_by=gift.purchased_by or 'Desconhecido',
                message=message or ''
            )
            notif_title = '🎁 Presente comprado!'
            notif_message = f'O presente "{gift.name}" foi marcado como comprado. Comprado por: {gift.purchased_by or "Desconhecido"}.'
        else:
            subject = EMAIL_GIFT_UNMARKED_SUBJECT
            html_message = EMAIL_GIFT_UNMARKED_BODY.format(
                gift_name=gift.name
            )
            notif_title = '🎁 Presente desmarcado'
            notif_message = f'O presente "{gift.name}" foi desmarcado como comprado.'
        Notification.objects.create(
            user=user,
            type='info',
            title=notif_title,
            message=notif_message,
            is_read=False
        )
        if user and user.email:
            send_mail(
                subject=subject,
                message=notif_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=True,
            )
            logging.info(f'Email enviado para {user.email} sobre o presente "{gift.name}" ({action})')
        logging.info(f'Notificação enviada para {user.username} sobre o presente "{gift.name}" ({action})')


def send_mail_confirmation_email(user):
    token = secrets.token_urlsafe(32)
    user.email_confirmation_token = token
    user.is_active = False  # Desativar o usuário até que o email seja confirmado
    user.is_email_confirmed = False  # Garantir que o usuário não está confirmado
    user.email_confirmation_expiry = timezone.now() + timezone.timedelta(hours=24)
    user.save()
    confirmation_link = f"{settings.FRONTEND_URL}/register/confirm-email/?token={token}"
    subject = "📧 Bem-vindo! Confirme seu e-mail para ativar sua conta"
    plain_message = f"Clique no link para confirmar: {confirmation_link}"
    html_message = EMAIL_CONFIRMATION_HTML_TEMPLATE.format(
        email=user.email,
        confirmation_link=confirmation_link
    )
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=html_message,
    )


def initialize_user_chat(user):
    UserWeddingProfile.objects.get_or_create(user=user)
    check_and_send_checklist_reminders(user)
    if not user.settings:
        user.settings = UserSettings.objects.create()
        user.save()
    return Response({
        "user": UserSerializer(user).data,
        "token": AuthToken.objects.create(user)[1],
    }, status=status.HTTP_200_OK)


def notify_user_wedding_site(user, action):
    if action == 'create':
        subject = EMAIL_WEDDING_SITE_CREATE_SUBJECT
        message = EMAIL_WEDDING_SITE_CREATE_BODY
    else:
        subject = EMAIL_WEDDING_SITE_UPDATE_SUBJECT
        message = EMAIL_WEDDING_SITE_UPDATE_BODY
    send_mail(
        subject,
        'Olá {user.email},\n\n',
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=message,
        fail_silently=True,
    )


def notify_user_wedding_site(user, action):
    if action == 'create':
        subject = EMAIL_WEDDING_SITE_CREATE_SUBJECT
        message = EMAIL_WEDDING_SITE_CREATE_BODY
    else:
        subject = EMAIL_WEDDING_SITE_UPDATE_SUBJECT
        message = EMAIL_WEDDING_SITE_UPDATE_BODY
    send_mail(
        subject,
        'Olá {user.email},\n\n',
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=message,
        fail_silently=True,
    )
