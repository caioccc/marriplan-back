from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from app.models import CustomUser, UserSession, ChatMessage, UserSettings, Notification, UserWeddingProfile, WeddingSite, WeddingSiteHistory, WeddingImage


class UserSettingsAdmin(admin.ModelAdmin):
    list_display = ('language', 'theme', 'created_at', 'updated_at')
    list_filter = ('language', 'theme')
    ordering = ('updated_at',)


class UserSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'session_id', 'title', 'created_at', 'updated_at')
    search_fields = ('user__username', 'session_id')
    list_filter = ('created_at',)
    ordering = ('-created_at',)


class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('session', 'is_user', 'content', 'created_at', 'updated_at')
    search_fields = ('session__user__username', 'content')
    list_filter = ('is_user', 'created_at')
    ordering = ('-created_at',)


class UserWeddingProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'nome_noivo', 'nome_noiva', 'data_casamento', 'local', 'cidade', 'estado', 'created_at', 'updated_at',)
    search_fields = ('user__username', 'nome_noivo', 'nome_noiva', 'local',)
    list_filter = ('cidade', 'estado',)
    ordering = ('-created_at',)


class WeddingSiteAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'template', 'cover_photo', 'get_gallery_count')
    search_fields = ('user__username', 'template')
    filter_horizontal = ('gallery',)
    def get_gallery_count(self, obj):
        return obj.gallery.count()
    get_gallery_count.short_description = 'Qtd. Imagens Galeria'



class WeddingSiteHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'site', 'action', 'performed_by', 'created_at', 'description')
    list_filter = ('action', 'created_at', 'performed_by')
    search_fields = ('site__id', 'description', 'performed_by__username')
    date_hierarchy = 'created_at'


class UserWeddingProfileInline(admin.StackedInline):
    model = UserWeddingProfile
    can_delete = False
    verbose_name_plural = "Perfil de Casamento"
    fk_name = 'user'

class WeddingSiteInline(admin.StackedInline):
    model = WeddingSite
    can_delete = False
    verbose_name_plural = "Site de Casamento"
    fk_name = 'user'

class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Confirmação de Email', {
            'fields': ('is_email_confirmed', 'email_confirmation_token', 'email_confirmation_expiry')
        }),
        ('Configurações de 2FA', {
            'fields': ('is_2fa_enabled', 'otp_secret')
        }),
        ('Configurações do Usuário', {
            'fields': ('settings',)
        }),
    )
    list_display = UserAdmin.list_display + ('is_email_confirmed', 'is_2fa_enabled')
    inlines = [UserWeddingProfileInline, WeddingSiteInline]


class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'type', 'title', 'message', 'is_read', 'created_at',)
    search_fields = ('user__username', 'message')
    list_filter = ('type', 'is_read')
    ordering = ('-created_at',)


class WeddingImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'url', 'id_cloudinary', 'folder', 'in_use', 'uploaded_at')
    list_filter = ('in_use', 'folder', 'uploaded_at')
    search_fields = ('url', 'id_cloudinary', 'folder')


# Registre os outros modelos normalmente
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(UserSession, UserSessionAdmin)
admin.site.register(ChatMessage, ChatMessageAdmin)
admin.site.register(UserSettings, UserSettingsAdmin)
admin.site.register(Notification, NotificationAdmin)
admin.site.register(UserWeddingProfile, UserWeddingProfileAdmin)
admin.site.register(WeddingSite, WeddingSiteAdmin)
admin.site.register(WeddingSiteHistory, WeddingSiteHistoryAdmin)
admin.site.register(WeddingImage, WeddingImageAdmin)
