import random
import string

from app.models import (ChatMessage, CustomUser, Notification, UserSession,
                        UserSettings, UserWeddingProfile, WeddingSite,
                        WeddingSiteHistory, WeddingImage, WeddingIdentity, WeddingIdentityInspiration, WeddingIdentityShareToken, ChecklistTask, ChecklistTaskAttachment, ChecklistTaskShare, Guest, GuestConfirmationToken, Gift, GiftListShareToken, SupplierCategory, Supplier, WeddingSupplier, STYLE_CHOICES)
from django.contrib.auth import authenticate, get_user_model
from django.utils.text import slugify
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed


class UserSerializer(serializers.ModelSerializer):
    wedding_profile = serializers.SerializerMethodField()

    class Meta:
        ref_name = "User"
        model = CustomUser
        fields = ('id', 'username', 'email', 'is_email_confirmed', 'is_2fa_enabled', 'settings', 'role', 'wedding_partner_role', 'wedding_profile', 'wedding_site',)

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


class WeddingIdentitySerializer(serializers.ModelSerializer):
    selected_style = serializers.ChoiceField(choices=STYLE_CHOICES, required=False, allow_blank=True)

    class Meta:
        model = WeddingIdentity
        fields = ['id', 'wedding_profile', 'selected_style', 'wedding_size', 'dress_code', 'palette', 'created_at', 'updated_at']
        read_only_fields = ['id', 'wedding_profile', 'created_at', 'updated_at']

    def validate_palette(self, value):
        if value in (None, ''):
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError('A paleta deve ser uma lista de cores.')
        return value


class WeddingIdentityInspirationSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeddingIdentityInspiration
        fields = [
            'id', 'wedding_profile', 'source_id', 'title', 'description', 'image_url', 'thumbnail_url',
            'source_url', 'query', 'selected_style', 'dress_code', 'is_favorite', 'is_liked', 'metadata',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'wedding_profile', 'created_at', 'updated_at']

    def validate_metadata(self, value):
        if value in (None, ''):
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError('Os metadados devem ser um objeto.')
        return value


class WeddingIdentityShareTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeddingIdentityShareToken
        fields = ['token', 'created_at']


class UserWeddingProfileSerializer(serializers.ModelSerializer):
    wedding_identity = WeddingIdentitySerializer(read_only=True)
    inspirations_count = serializers.SerializerMethodField()
    has_wedding_identity = serializers.SerializerMethodField()

    class Meta:
        model = UserWeddingProfile
        fields = '__all__'

    def get_has_wedding_identity(self, obj):
        return hasattr(obj, 'wedding_identity')

    def get_inspirations_count(self, obj):
        return obj.inspirations.count() if hasattr(obj, 'inspirations') else 0


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
            'priority', 'status', 'is_template', 'attachments', 'created_at', 'updated_at', 'days_before_event', 'notes'
        ]
        read_only_fields = ['user', 'created_at', 'updated_at', 'attachments', 'days_before_event']


class ChecklistTaskShareSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChecklistTaskShare
        fields = ['id', 'task', 'email', 'shared_at']


class GuestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Guest
        fields = ['id', 'name', 'phone', 'whatsapp', 'photo_url', 'photo_public_id', 'email', 'alergias', 'acompanhantes', 'observacoes', 'status_presenca', 'user', 'wedding_profile', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'wedding_profile', 'created_at', 'updated_at']


class GiftSerializer(serializers.ModelSerializer):
    product_code = serializers.CharField(required=False, allow_blank=True, allow_null=True, default='')

    class Meta:
        model = Gift
        fields = [
            'id', 'wedding_profile', 'name', 'value', 'link', 'description', 'category',
            'image', 'image_public_id', 'icon', 'status', 'purchased_by', 'purchase_date',
            'reserved_by', 'reserved_message', 'reserved_at',
            'product_code', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'purchase_date', 'reserved_at', 'created_at', 'updated_at']


class GiftListShareTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = GiftListShareToken
        fields = ['token', 'created_at']


class GuestConfirmationTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuestConfirmationToken
        fields = ['id', 'guest', 'token', 'created_at', 'expires_at', 'used_at', 'confirmation_status']
        read_only_fields = ['id', 'token', 'created_at', 'expires_at', 'used_at']


class SupplierCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplierCategory
        fields = ['id', 'name', 'slug']


class SupplierSerializer(serializers.ModelSerializer):
    category_detail = SupplierCategorySerializer(source='category', read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(source='category', queryset=SupplierCategory.objects.all(), write_only=True)

    class Meta:
        model = Supplier
        fields = [
            'id', 'category_detail', 'category_id', 'name', 'company_name', 'description', 'phone', 'cnpj',
            'whatsapp', 'email', 'instagram', 'website', 'city', 'state', 'cover_image_url',
            'cover_image_public_id', 'status', 'visibility', 'is_featured', 'created_by_user', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_by_user', 'created_at', 'updated_at']


class WeddingSupplierSerializer(serializers.ModelSerializer):
    supplier_detail = SupplierSerializer(source='supplier', read_only=True)
    supplier_id = serializers.PrimaryKeyRelatedField(source='supplier', queryset=Supplier.objects.all(), write_only=True)

    class Meta:
        model = WeddingSupplier
        fields = [
            'id', 'wedding', 'supplier_detail', 'supplier_id', 'is_hired', 'is_favorite',
            'estimated_price', 'negotiated_price', 'paid_amount', 'contract_date', 'wedding_delivery_date',
            'contract_file_url', 'contract_file_public_id', 'notes', 'status', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'wedding', 'created_at', 'updated_at']
