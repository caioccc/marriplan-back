from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from app.models import ChecklistTask, ChecklistTaskNotification, Notification
from app.constants import CHECKLIST_TASK_REMINDER_EMAIL_TEMPLATE
from django.conf import settings
import logging

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
            logging.error(f'Erro ao criar lembrete/checklist/email para o usuário {user.id} e tarefa {task.id}: {e}', exc_info=True)
