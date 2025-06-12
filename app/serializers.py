import random
import string

from app.models import (ChatMessage, CustomUser, Notification, UserSession,
                        UserSettings, UserWeddingProfile, WeddingSite,
                        WeddingSiteHistory)
from django.contrib.auth import authenticate, get_user_model
from django.utils.text import slugify
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed


class UserSerializer(serializers.ModelSerializer):
    wedding_profile = serializers.SerializerMethodField()

    class Meta:
        ref_name = "User"
        model = CustomUser
        fields = ('id', 'username', 'email', 'is_email_confirmed', 'is_2fa_enabled', 'settings', 'role', 'wedding_profile', 'wedding_site',)

    def get_wedding_site(self, obj):
        try:
            wedding_site = obj.wedding_site
        except WeddingSite.DoesNotExist:
            return None
        return WeddingSiteSerializer(wedding_site).data

    def get_wedding_profile(self, obj):
        try:
            profile = obj.wedding_profile
        except UserWeddingProfile.DoesNotExist:
            return None
        return UserWeddingProfileSerializer(profile).data


class UserSettingsSerializer(serializers.ModelSerializer):
    enable_2fa = serializers.BooleanField(required=False, default=False)

    class Meta:
        model = UserSettings
        fields = ['language', 'theme', 'enable_2fa', 'created_at', 'updated_at']


class RegisterSerializer(serializers.ModelSerializer):
    name = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=[('noivo', 'Noivo(a)'), ('convidado', 'Convidado')], default='noivo', required=False)

    class Meta:
        ref_name = "Register User"
        model = CustomUser
        fields = ('id', 'name', 'email', 'password', 'role')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        name = validated_data.get('name')
        email = validated_data.get('email')
        password = validated_data.get('password')
        role = validated_data.get('role', 'noivo')
        if not name or not email or not password:
            raise serializers.ValidationError('Todos os campos são obrigatórios.')
        base_username = slugify(name) or email.split('@')[0]
        username = base_username
        user_model = get_user_model()
        # Verifica se o email já está cadastrado
        if user_model.objects.filter(email=email).exists():
            raise serializers.ValidationError('Email já cadastrado.')
        # Garante unicidade do username
        while user_model.objects.filter(username=username).exists():
            username = f"{base_username}{''.join(random.choices(string.digits, k=3))}"

        user = user_model.objects.create_user(username=username, email=email, password=password, role=role)
        return user


class PreLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        User = get_user_model()
        email = data.get('email')
        password = data.get('password')
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({'error': 'Credenciais incorretas.'})

        if not user.is_email_confirmed:
            raise AuthenticationFailed('Confirme seu e-mail antes de fazer login.', code='email_not_confirmed')

        if user.is_2fa_enabled:
            # Não autentica ainda, só avisa que precisa do 2FA
            raise serializers.ValidationError({'require_2fa': True, 'message': '2FA requerido.'})

        user_auth = authenticate(username=user.username, password=password)
        if not user_auth or not user_auth.is_active:
            raise serializers.ValidationError({'error': 'Credenciais incorretas.'})

        return user


class LoginSerializer(serializers.Serializer):
    class Meta:
        ref_name = "Login User"

    """
    Login serializer
    """
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, data):
        User = get_user_model()
        email = data.get('email')
        password = data.get('password')
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError('Email não encontrado.')
        if not user.is_email_confirmed:
            raise AuthenticationFailed('Confirme seu e-mail antes de fazer login.', code='email_not_confirmed')
        user = authenticate(username=user.username, password=password)
        if user and user.is_active:
            return user
        raise serializers.ValidationError('Credenciais incorretas.')


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['id', 'session', 'is_user', 'content', 'thinking_content', 'created_at', 'updated_at']


class UserSessionSerializer(serializers.ModelSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)
    user = serializers.ReadOnlyField(source='user.username')
    session_id = serializers.CharField(required=False)

    class Meta:
        model = UserSession
        fields = ['id', 'user', 'session_id', 'created_at', 'updated_at', 'messages', 'title']


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'type', 'title', 'message', 'is_read', 'created_at']


class UserWeddingProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserWeddingProfile
        fields = '__all__'


class WeddingSiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeddingSite
        fields = '__all__'
        extra_kwargs = {
            'user': {'required': False},
            'url_slug': {'required': False},
        }

class WeddingSiteHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = WeddingSiteHistory
        fields = '__all__'
