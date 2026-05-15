from django.contrib.auth import get_user_model
from knox.auth import TokenAuthentication
from rest_framework import (generics, permissions, status, viewsets)
from rest_framework.decorators import (action)
from rest_framework.response import Response
from rest_framework.views import APIView

from app.models import (Notification, UserSettings,
                        UserWeddingProfile)
from app.serializers import (NotificationSerializer, UserSerializer,
                             UserSettingsSerializer,
                             UserWeddingProfileSerializer)


class MainUser(generics.RetrieveAPIView):
    """
    Get user API endpoint.
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = [
        permissions.IsAuthenticated
    ]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class UserSettingsAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        settings_obj = request.user.settings
        user = request.user
        if not settings_obj:
            settings_obj = UserSettings.objects.create()
            user.settings = settings_obj
            user.save()
        serializer = UserSettingsSerializer(settings_obj)
        return Response(serializer.data)

    def patch(self, request):
        settings = self.request.user.settings
        user = request.user
        if not settings:
            settings = UserSettings.objects.create()
            user.settings = settings
            user.save()
        serializer = UserSettingsSerializer(settings, data={
            'language': request.data.get('language', settings.language),
            'theme': request.data.get('theme', settings.theme),
            'enable_2fa': request.data.get('enable_2fa', False)
        }, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class UserViewSet(viewsets.ModelViewSet):
    """
    User viewset
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = [
        permissions.IsAuthenticated
    ]
    serializer_class = UserSerializer

    def get_queryset(self):
        User = get_user_model()
        queryset = User.objects.all()
        name = self.request.query_params.get('name', None)
        if name is not None:
            queryset = queryset.filter(name__icontains=name)
        return queryset

    @action(detail=False, methods=['patch'], url_path='update-profile',
            permission_classes=[permissions.IsAuthenticated])
    def update_profile(self, request):
        User = get_user_model()
        user = request.user
        username = request.data.get('username')
        name = request.data.get('name')

        if username:
            if User.objects.exclude(pk=user.pk).filter(username=username).exists():
                return Response({'error': 'Username já está em uso.'}, status=status.HTTP_400_BAD_REQUEST)
            user.username = username

        if name:
            user.first_name = name

        user.save()
        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('is_read', '-created_at')

    @action(detail=False, methods=['get'])
    def unread(self, request):
        queryset = self.get_queryset().filter(is_read=False).order_by('-created_at')
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({'status': 'Todas marcadas como lidas'})

    @action(detail=False, methods=['post'])
    def mark_all_unread(self, request):
        self.get_queryset().filter(is_read=True).update(is_read=False)
        return Response({'status': 'Todas marcadas como não lidas'})

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'Marcada como lida'})

    @action(detail=True, methods=['post'])
    def mark_unread(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = False
        notification.save()
        return Response({'status': 'Marcada como não lida'})

    @action(detail=False, methods=['delete'], url_path='delete-all')
    def delete_all(self, request):
        self.get_queryset().delete()
        return Response({'status': 'Todas notificações removidas'})


class UserWeddingProfileViewSet(viewsets.ModelViewSet):
    serializer_class = UserWeddingProfileSerializer

    def get_queryset(self):
        return UserWeddingProfile.objects.filter(user=self.request.user)

    def get_object(self):
        # Garante que cada usuário só acessa o próprio perfil
        obj, _ = UserWeddingProfile.objects.get_or_create(user=self.request.user)
        return obj

    def list(self, request, *args, **kwargs):
        # Retorna sempre o perfil único do usuário
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
