import logging
import secrets
import uuid
from datetime import timedelta
from decimal import Decimal, InvalidOperation
import re
from urllib.parse import quote_plus

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from knox.models import AuthToken
from rest_framework import (status)
from rest_framework.response import Response

from app.constants import CHECKLIST_TASK_REMINDER_EMAIL_TEMPLATE, EMAIL_CONFIRMATION_HTML_TEMPLATE, \
    EMAIL_WEDDING_SITE_CREATE_SUBJECT, EMAIL_WEDDING_SITE_CREATE_BODY, EMAIL_WEDDING_SITE_UPDATE_SUBJECT, \
    EMAIL_WEDDING_SITE_UPDATE_BODY, EMAIL_GIFT_PURCHASED_SUBJECT, EMAIL_GIFT_PURCHASED_BODY, \
    EMAIL_GIFT_UNMARKED_SUBJECT, EMAIL_GIFT_UNMARKED_BODY, EMAIL_GIFT_RESERVED_SUBJECT, EMAIL_GIFT_RESERVED_BODY
from app.models import ChecklistTask, ChecklistTaskNotification, Notification, UserWeddingProfile, UserSession, \
    ChatMessage, UserSettings
from app.serializers import UserSerializer

MAX_GUESTS_PER_WEDDING = 500
MAX_GIFTS_PER_WEDDING = 300
MAX_SUPPLIERS_PER_SCOPE = 50
MAX_TASKS_PER_USER = 100
MAX_NOTIFICATIONS_PER_USER = 100


def to_upper_camel_words(value):
    text = str(value or '').strip()
    if not text:
        return ''

    words = re.split(r'\s+', text)
    normalized_words = []
    for word in words:
        if not word:
            continue
        if word == word.upper() and re.search(r'[A-Z]', word):
            normalized_words.append(word)
        else:
            normalized_words.append(f'{word[:1].upper()}{word[1:].lower()}')
    return ' '.join(normalized_words)


def to_sentence_case(value):
    text = str(value or '').strip()
    if not text:
        return ''

    normalized = re.sub(r'\s+', ' ', text)
    words = []
    for word in normalized.split(' '):
        if word == word.upper() and re.search(r'[A-Z]', word):
            words.append(word)
        else:
            words.append(word.lower())

    combined = ' '.join(words)
    return f'{combined[:1].upper()}{combined[1:]}' if combined else ''


def is_valid_url(value):
    text = str(value or '').strip()
    return bool(text) and text.startswith(('http://', 'https://'))


def normalize_gift_value(value):
    if value is None:
        return Decimal('0.00')

    if isinstance(value, bool):
        return Decimal('0.00')

    if isinstance(value, (int, float, Decimal)):
        try:
            if isinstance(value, float) and (value != value):
                return Decimal('0.00')
            return Decimal(str(value)).quantize(Decimal('0.01'))
        except (InvalidOperation, ValueError, TypeError):
            return Decimal('0.00')

    text = str(value).strip()
    if not text or ',' in text:
        return Decimal('0.00')

    if not re.fullmatch(r'(0|[1-9]\d*)(\.\d{1,2})?', text):
        return Decimal('0.00')

    try:
        return Decimal(text).quantize(Decimal('0.01'))
    except (InvalidOperation, ValueError):
        return Decimal('0.00')


def remaining_quota(current_count, limit):
    return max(limit - current_count, 0)


def is_limit_reached(current_count, limit):
    return current_count >= limit


def create_limited_notification(*, user, type, title, message, is_read=False):
    notification = Notification.objects.create(
        user=user,
        type=type,
        title=title,
        message=message,
        is_read=is_read,
    )

    notification_ids = list(
        Notification.objects.filter(user=user)
        .order_by('-created_at')
        .values_list('id', flat=True)[MAX_NOTIFICATIONS_PER_USER:]
    )
    if notification_ids:
        Notification.objects.filter(id__in=notification_ids).delete()

    return notification


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
            create_limited_notification(
                user=user,
                type='info',
                title='⏰ Lembrete de tarefa',
                message=f'A tarefa "{task.description}" vence em 3 dias. Não se esqueça de concluir!',
                is_read=False,
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


def _clean_whatsapp_number(phone):
    digits = re.sub(r'\D', '', phone or '')
    if not digits:
        return ''
    if digits.startswith('55') and len(digits) > 11:
        return digits
    return f'55{digits}'


def build_whatsapp_link(phone, message):
    number = _clean_whatsapp_number(phone)
    if not number:
        return None
    return f'https://wa.me/{number}?text={quote_plus(message)}'


def notify_gift_status_change(gift, action, message=None, reserved_by=None):
    """
    Notifica os noivos por Notification e email ao marcar/desmarcar/reservar presente.
    action: 'purchased', 'unmarked' ou 'reserved'
    message: mensagem livre do comprador (opcional)
    """
    from app.models import Notification
    wedding_profile = getattr(gift, 'wedding_profile', None)
    if not wedding_profile:
        return {'whatsapp_links': []}
    # Suporte a wedding_profile.user (um noivo) ou wedding_profile.users (muitos)
    users = []
    if hasattr(wedding_profile, 'users') and wedding_profile.users:
        users = list(wedding_profile.users.all())
    elif hasattr(wedding_profile, 'user') and wedding_profile.user:
        users = [wedding_profile.user]

    whatsapp_links = []
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
        elif action == 'reserved':
            subject = EMAIL_GIFT_RESERVED_SUBJECT
            reserved_name = reserved_by or 'um convidado'
            custom_message = message.strip() if message else ''
            html_message = EMAIL_GIFT_RESERVED_BODY.format(
                gift_name=gift.name,
                reserved_by=reserved_name,
                message=custom_message or 'Sem mensagem adicional.'
            )
            notif_title = '🎁 Presente reservado!'
            notif_message = f'O presente "{gift.name}" foi reservado por {reserved_name}.'
            if custom_message:
                notif_message += f' Mensagem: {custom_message}'
        else:
            subject = EMAIL_GIFT_UNMARKED_SUBJECT
            html_message = EMAIL_GIFT_UNMARKED_BODY.format(
                gift_name=gift.name
            )
            notif_title = '🎁 Presente desmarcado'
            notif_message = f'O presente "{gift.name}" foi desmarcado como comprado.'
        create_limited_notification(
            user=user,
            type='info',
            title=notif_title,
            message=notif_message,
            is_read=False,
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

    if action == 'reserved':
        reserved_name = reserved_by or 'um convidado'
        custom_message = message.strip() if message else ''
        whatsapp_text = f'Oi! O presente "{gift.name}" foi reservado por {reserved_name}.'
        if custom_message:
            whatsapp_text += f' Mensagem: {custom_message}'
        if getattr(wedding_profile, 'telefone_noivo', ''):
            link = build_whatsapp_link(wedding_profile.telefone_noivo, whatsapp_text)
            if link:
                whatsapp_links.append({'label': 'Noivo', 'url': link})
        if getattr(wedding_profile, 'telefone_noiva', ''):
            link = build_whatsapp_link(wedding_profile.telefone_noiva, whatsapp_text)
            if link:
                whatsapp_links.append({'label': 'Noiva', 'url': link})

    return {'whatsapp_links': whatsapp_links}


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
