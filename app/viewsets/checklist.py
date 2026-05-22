from rest_framework import (permissions, viewsets)
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from app.models import (ChecklistTask, ChecklistTaskAttachment,
                        ChecklistTaskShare)
from app.serializers import (ChecklistTaskAttachmentSerializer,
                             ChecklistTaskSerializer,
                             ChecklistTaskShareSerializer)
from app.logging_utils import audit_log
from app.utils import MAX_TASKS_PER_USER, is_limit_reached


class ChecklistTaskViewSet(viewsets.ModelViewSet):
    serializer_class = ChecklistTaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ChecklistTask.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        current_count = ChecklistTask.objects.filter(user=self.request.user).count()
        if is_limit_reached(current_count, MAX_TASKS_PER_USER):
            raise ValidationError({'detail': 'Limite de 100 tarefas atingido.'})
        instance = serializer.save(user=self.request.user)
        audit_log('checklist_task.create', user=self.request.user, obj=instance, message='Tarefa criada')

    def perform_update(self, serializer):
        instance = serializer.save()
        audit_log('checklist_task.update', user=self.request.user, obj=instance, message='Tarefa atualizada')

    def perform_destroy(self, instance):
        audit_log('checklist_task.delete', user=self.request.user, obj=instance, message='Tarefa removida')
        instance.delete()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class ChecklistTaskAttachmentViewSet(viewsets.ModelViewSet):
    serializer_class = ChecklistTaskAttachmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ChecklistTaskAttachment.objects.filter(task__user=self.request.user)

    def perform_create(self, serializer):
        instance = serializer.save()
        audit_log('checklist_task_attachment.create', user=self.request.user, obj=instance, message='Anexo de tarefa criado')

    def perform_destroy(self, instance):
        audit_log('checklist_task_attachment.delete', user=self.request.user, obj=instance, message='Anexo de tarefa removido')
        instance.delete()


class ChecklistTaskShareViewSet(viewsets.ModelViewSet):
    serializer_class = ChecklistTaskShareSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ChecklistTaskShare.objects.filter(task__user=self.request.user)

    def perform_create(self, serializer):
        instance = serializer.save()
        audit_log('checklist_task_share.create', user=self.request.user, obj=instance, message='Compartilhamento de tarefa criado')

    def perform_destroy(self, instance):
        audit_log('checklist_task_share.delete', user=self.request.user, obj=instance, message='Compartilhamento de tarefa removido')
        instance.delete()
