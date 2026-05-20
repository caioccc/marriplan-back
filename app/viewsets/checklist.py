from rest_framework import (permissions, viewsets)
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from app.models import (ChecklistTask, ChecklistTaskAttachment,
                        ChecklistTaskShare)
from app.serializers import (ChecklistTaskAttachmentSerializer,
                             ChecklistTaskSerializer,
                             ChecklistTaskShareSerializer)
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
        serializer.save(user=self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class ChecklistTaskAttachmentViewSet(viewsets.ModelViewSet):
    serializer_class = ChecklistTaskAttachmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ChecklistTaskAttachment.objects.filter(task__user=self.request.user)


class ChecklistTaskShareViewSet(viewsets.ModelViewSet):
    serializer_class = ChecklistTaskShareSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ChecklistTaskShare.objects.filter(task__user=self.request.user)
