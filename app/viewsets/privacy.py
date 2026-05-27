from __future__ import annotations

from django.db import transaction
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from app.logging_utils import audit_exception, audit_log
from app.models import (
    ChatMessage,
    ChecklistTask,
    ChecklistTaskAttachment,
    ChecklistTaskNotification,
    ChecklistTaskShare,
    Gift,
    GiftListShareToken,
    Guest,
    GuestConfirmationToken,
    Notification,
    UserQuestionHistory,
    UserSession,
    WeddingIdentity,
    WeddingIdentityInspiration,
    WeddingIdentityShareToken,
    WeddingSite,
    WeddingSiteHistory,
    WeddingSupplier,
    LOGIN_METHOD_GOOGLE,
)
from app.serializers import (
    ChatMessageSerializer,
    ChecklistTaskSerializer,
    GiftSerializer,
    GuestSerializer,
    NotificationSerializer,
    UserSerializer,
    UserWeddingProfileSerializer,
    WeddingIdentityInspirationSerializer,
    WeddingIdentitySerializer,
    WeddingSiteSerializer,
    WeddingSupplierSerializer,
)


class AccountPrivacyExportDataAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        wedding_profile = getattr(user, "wedding_profile", None)

        guests_qs = Guest.objects.filter(user=user).order_by("id")
        tasks_qs = ChecklistTask.objects.filter(user=user).order_by("id")
        notifications_qs = Notification.objects.filter(user=user).order_by("id")
        sessions_qs = UserSession.objects.filter(user=user).order_by("id")
        messages_qs = ChatMessage.objects.filter(session__user=user).order_by("id")
        wedding_site = WeddingSite.objects.filter(user=user).first()

        gifts_qs = Gift.objects.none()
        vendors_qs = WeddingSupplier.objects.none()
        inspirations_qs = WeddingIdentityInspiration.objects.none()
        wedding_identity_obj = None

        if wedding_profile:
            gifts_qs = Gift.objects.filter(wedding_profile=wedding_profile).order_by("id")
            vendors_qs = WeddingSupplier.objects.filter(wedding=wedding_profile).order_by("id")
            inspirations_qs = WeddingIdentityInspiration.objects.filter(wedding_profile=wedding_profile).order_by("id")
            wedding_identity_obj = WeddingIdentity.objects.filter(wedding_profile=wedding_profile).first()

        payload = {
            "user": UserSerializer(user).data,
            "wedding_profile": UserWeddingProfileSerializer(wedding_profile).data if wedding_profile else None,
            "guests": GuestSerializer(guests_qs, many=True).data,
            "tasks": ChecklistTaskSerializer(tasks_qs, many=True).data,
            "gifts": GiftSerializer(gifts_qs, many=True).data,
            "vendors": WeddingSupplierSerializer(vendors_qs, many=True).data,
            "notifications": NotificationSerializer(notifications_qs, many=True).data,
            "messages": ChatMessageSerializer(messages_qs, many=True).data,
            "sessions": [
                {
                    "id": session.id,
                    "session_id": session.session_id,
                    "title": session.title,
                    "active_question_id": session.active_question_id,
                    "active_question_data": session.active_question_data,
                    "questions_history": session.questions_history,
                    "created_at": session.created_at,
                    "updated_at": session.updated_at,
                }
                for session in sessions_qs
            ],
            "wedding_identity": WeddingIdentitySerializer(wedding_identity_obj).data if wedding_identity_obj else None,
            "inspirations": WeddingIdentityInspirationSerializer(inspirations_qs, many=True).data,
            "wedding_site": WeddingSiteSerializer(wedding_site).data if wedding_site else None,
            "budget": [],
            "transactions": [],
            "timelines": [],
            "checklists": ChecklistTaskSerializer(tasks_qs, many=True).data,
            "cookie_preferences": {
                "managed_on_frontend": True,
                "note": "As preferências de cookies são armazenadas localmente no navegador.",
            },
        }

        audit_log(
            "account.privacy.export_data",
            user=user,
            message="Exportação de dados pessoais solicitada.",
            guests_count=guests_qs.count(),
            tasks_count=tasks_qs.count(),
            gifts_count=gifts_qs.count(),
            vendors_count=vendors_qs.count(),
            notifications_count=notifications_qs.count(),
            messages_count=messages_qs.count(),
        )
        return Response(payload, status=status.HTTP_200_OK)


class AccountPrivacyDeleteAccountAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request):
        user = request.user
        current_password = request.data.get("current_password")
        password_required = user.login_method != LOGIN_METHOD_GOOGLE and user.has_usable_password()

        if password_required:
            if not isinstance(current_password, str) or not current_password.strip():
                return Response(
                    {"detail": "A senha atual é obrigatória para excluir a conta."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if not user.check_password(current_password):
                return Response(
                    {"detail": "Senha atual inválida."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        wedding_profile = getattr(user, "wedding_profile", None)
        settings_obj = user.settings if getattr(user, "settings", None) else None

        try:
            with transaction.atomic():
                task_attachments = ChecklistTaskAttachment.objects.filter(task__user=user)
                for attachment in task_attachments:
                    if attachment.file:
                        attachment.file.delete(save=False)

                ChecklistTaskNotification.objects.filter(user=user).delete()
                ChecklistTaskShare.objects.filter(task__user=user).delete()
                task_attachments.delete()
                ChecklistTask.objects.filter(user=user).delete()

                GuestConfirmationToken.objects.filter(guest__user=user).delete()
                Guest.objects.filter(user=user).delete()

                if wedding_profile:
                    GiftListShareToken.objects.filter(wedding_profile=wedding_profile).delete()
                    Gift.objects.filter(wedding_profile=wedding_profile).delete()

                    WeddingSupplier.objects.filter(wedding=wedding_profile).delete()

                    WeddingIdentityShareToken.objects.filter(wedding_profile=wedding_profile).delete()
                    WeddingIdentityInspiration.objects.filter(wedding_profile=wedding_profile).delete()
                    WeddingIdentity.objects.filter(wedding_profile=wedding_profile).delete()

                WeddingSiteHistory.objects.filter(site__user=user).delete()
                WeddingSite.objects.filter(user=user).delete()

                Notification.objects.filter(user=user).delete()

                ChatMessage.objects.filter(session__user=user).delete()
                UserQuestionHistory.objects.filter(user_session__user=user).delete()
                UserSession.objects.filter(user=user).delete()

                if wedding_profile:
                    wedding_profile.delete()

                user.delete()

                if settings_obj:
                    settings_obj.delete()

            audit_log(
                "account.privacy.delete_account",
                user=user,
                message="Conta e dados pessoais excluídos com sucesso.",
            )
            return Response(
                {"detail": "Conta excluída com sucesso."},
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            audit_exception(
                "account.privacy.delete_account",
                user=user,
                message="Falha ao excluir conta.",
                exc=exc,
            )
            return Response(
                {"detail": "Não foi possível excluir a conta no momento."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )