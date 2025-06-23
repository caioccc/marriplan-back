from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from app.models import ChecklistTask, ChecklistTaskNotification

# Exemplo de função para rodar via Celery ou cron

def send_checklist_task_reminders():
    now = timezone.now()
    days_before = 3
    target_date = now + timedelta(days=days_before)
    tasks = ChecklistTask.objects.filter(
        due_date=target_date.date(),
        status__in=['pending', 'in_progress']
    )
    for task in tasks:
        # Evita duplicidade
        if ChecklistTaskNotification.objects.filter(task=task, user=task.user, scheduled_for=target_date.date()).exists():
            continue
        # Cria notificação in-app
        ChecklistTaskNotification.objects.create(
            task=task,
            user=task.user,
            scheduled_for=target_date,
            sent=True,
            sent_at=now
        )
        # Cria notificação no sistema (Notification)
        from app.models import Notification
        Notification.objects.create(
            user=task.user,
            type='info',
            title='⏰ Lembrete de tarefa',
            message=f'A tarefa "{task.description}" vence em 3 dias. Não se esqueça de concluir!',
            is_read=False
        )
        # Envia e-mail
        send_mail(
            subject='⏰ Lembrete: Tarefa do checklist vence em 3 dias',
            message=f'A tarefa "{task.description}" vence em 3 dias. Não se esqueça de concluir!',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[task.user.email],
            fail_silently=True,
        )
