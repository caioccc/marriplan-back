from rest_framework import (permissions, viewsets)
from rest_framework.response import Response

from app.models import (ChecklistTask, ChecklistTaskAttachment,
                        ChecklistTaskShare)
from app.serializers import (ChecklistTaskAttachmentSerializer,
                             ChecklistTaskSerializer,
                             ChecklistTaskShareSerializer)


class ChecklistTaskViewSet(viewsets.ModelViewSet):
    serializer_class = ChecklistTaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ChecklistTask.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
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
