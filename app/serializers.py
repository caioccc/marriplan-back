import random
import string

from app.models import (ChatMessage, CustomUser, Notification, UserSession,
                        UserSettings, UserWeddingProfile, WeddingSite,
                        WeddingSiteHistory, WeddingImage, ChecklistTask, ChecklistTaskAttachment, ChecklistTaskShare, Guest, GuestConfirmationToken, Gift, GiftListShareToken)
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


class WeddingImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeddingImage
        fields = ['id', 'url', 'id_cloudinary', 'folder', 'in_use', 'uploaded_at']


class WeddingSiteSerializer(serializers.ModelSerializer):
    cover_photo = WeddingImageSerializer(read_only=True)
    gallery = WeddingImageSerializer(many=True, read_only=True)

    class Meta:
        model = WeddingSite
        fields = '__all__'
        extra_kwargs = {
            'user': {'required': False},
            'url_slug': {'required': False},
        }


class WeddingSiteHistorySerializer(serializers.ModelSerializer):
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    performed_by_username = serializers.CharField(source='performed_by.username', read_only=True)
    class Meta:
        model = WeddingSiteHistory
        fields = ['id', 'site', 'action', 'action_display', 'performed_by', 'performed_by_username', 'description', 'snapshot', 'created_at']


class ChecklistTaskAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChecklistTaskAttachment
        fields = ['id', 'file', 'uploaded_at']


class ChecklistTaskSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    days_before_event = serializers.IntegerField(read_only=True)

    class Meta:
        model = ChecklistTask
        fields = [
            'id', 'user', 'month', 'description', 'start_date', 'due_date',
            'priority', 'status', 'is_template', 'attachments', 'created_at', 'updated_at', 'days_before_event'
        ]
        read_only_fields = ['user', 'created_at', 'updated_at', 'attachments', 'days_before_event']


class ChecklistTaskShareSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChecklistTaskShare
        fields = ['id', 'task', 'email', 'shared_at']


class GuestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Guest
        fields = ['id', 'name', 'phone', 'whatsapp', 'email', 'alergias', 'acompanhantes', 'observacoes', 'status_presenca', 'user', 'wedding_profile', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'wedding_profile', 'created_at', 'updated_at']


class GiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = Gift
        fields = [
            'id', 'wedding_profile', 'name', 'value', 'link', 'description', 'category',
            'image', 'icon', 'status', 'purchased_by',
            'purchase_date', 'product_code', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'purchase_date', 'created_at', 'updated_at']


class GiftListShareTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = GiftListShareToken
        fields = ['token', 'created_at']


class GuestConfirmationTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuestConfirmationToken
        fields = ['id', 'guest', 'token', 'created_at', 'expires_at', 'used_at', 'confirmation_status']
        read_only_fields = ['id', 'token', 'created_at', 'expires_at', 'used_at']
