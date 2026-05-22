import secrets

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from app.models import UserWeddingProfile, WeddingIdentity, WeddingIdentityShareToken
from app.serializers import WeddingIdentitySerializer, WeddingIdentityShareTokenSerializer
from app.logging_utils import audit_log
from app.services.wedding_identity import delete_wedding_identity, get_wedding_identity, upsert_wedding_identity


class WeddingIdentityViewSet(viewsets.ModelViewSet):
    serializer_class = WeddingIdentitySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_profile(self, create=False):
        profile = getattr(self.request.user, 'wedding_profile', None)
        if profile or not create:
            return profile
        profile, _ = UserWeddingProfile.objects.get_or_create(user=self.request.user)
        return profile

    def get_queryset(self):
        return WeddingIdentity.objects.filter(wedding_profile__user=self.request.user)

    def get_object(self):
        profile = self.get_profile()
        if not profile:
            raise NotFound('Nenhuma identidade de casamento encontrada para este usuário.')

        identity = get_wedding_identity(profile)
        if not identity:
            raise NotFound('Nenhuma identidade de casamento encontrada para este usuário.')
        return identity

    def list(self, request, *args, **kwargs):
        profile = self.get_profile()
        if not profile:
            return Response({'detail': 'Nenhuma identidade de casamento encontrada para este usuário.'}, status=status.HTTP_404_NOT_FOUND)

        identity = get_wedding_identity(profile)
        if not identity:
            return Response({'detail': 'Nenhuma identidade de casamento encontrada para este usuário.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(identity)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        identity, created = upsert_wedding_identity(self.get_profile(create=True), serializer.validated_data)
        response_serializer = self.get_serializer(identity)
        audit_log('wedding_identity.create', user=request.user, obj=identity, message='Identidade criada ou atualizada no create', created=created)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        identity = self.get_object()
        serializer = self.get_serializer(identity, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated_identity, _ = upsert_wedding_identity(self.get_profile(create=True), serializer.validated_data)
        response_serializer = self.get_serializer(updated_identity)
        audit_log('wedding_identity.update', user=request.user, obj=updated_identity, message='Identidade atualizada')
        return Response(response_serializer.data)

    def destroy(self, request, *args, **kwargs):
        deleted = delete_wedding_identity(self.get_profile())
        if not deleted:
            raise NotFound('Nenhuma identidade de casamento encontrada para este usuário.')
        audit_log('wedding_identity.delete', user=request.user, message='Identidade removida')
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get', 'patch', 'delete'], url_path='me')
    def me(self, request):
        if request.method == 'GET':
            return self.list(request)

        if request.method == 'PATCH':
            identity = get_wedding_identity(self.get_profile())
            serializer = self.get_serializer(identity, data=request.data, partial=True) if identity else self.get_serializer(data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            updated_identity, created = upsert_wedding_identity(self.get_profile(create=True), serializer.validated_data)
            response_serializer = self.get_serializer(updated_identity)
            audit_log('wedding_identity.update', user=request.user, obj=updated_identity, message='Identidade atualizada via me', created=created)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

        deleted = delete_wedding_identity(self.get_profile())
        if not deleted:
            raise NotFound('Nenhuma identidade de casamento encontrada para este usuário.')
        audit_log('wedding_identity.delete', user=request.user, message='Identidade removida via me')
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['post'], url_path='share-token')
    def share_token(self, request):
        profile = self.get_profile(create=True)
        share_token, created = WeddingIdentityShareToken.objects.get_or_create(
            wedding_profile=profile,
            defaults={'token': secrets.token_urlsafe(32)},
        )

        if not share_token.token:
            share_token.token = secrets.token_urlsafe(32)
            share_token.save(update_fields=['token', 'updated_at'])

        serializer = WeddingIdentityShareTokenSerializer(share_token)
        audit_log('wedding_identity.share_token', user=request.user, obj=share_token, message='Token de compartilhamento gerado', created=created)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
