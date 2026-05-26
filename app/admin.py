from django.utils.html import format_html
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import path, reverse

from app.models import CustomUser, UserSession, ChatMessage, UserSettings, Notification, UserWeddingProfile, WeddingIdentity, WeddingIdentityInspiration, WeddingIdentityShareToken, WeddingSite, WeddingSiteHistory, WeddingImage, SupplierCategory, Supplier, WeddingSupplier
from .models import ChecklistTask, ChecklistTaskAttachment, ChecklistTaskShare, ChecklistTaskNotification, Guest, Gift, GiftListShareToken, ProductCatalog
from app.services.scrapers.amazon import AmazonScraper


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
    change_form_template = 'admin/app/userweddingprofile/change_form.html'
    list_display = ('user','get_wedding_partner_role', 'nome_noivo', 'nome_noiva', 'data_casamento', 
                    'local', 'cidade', 'estado', 'created_at', 'updated_at',)
    search_fields = ('user__username', 'nome_noivo', 'nome_noiva', 'local',)
    list_filter = ('cidade', 'estado',)
    ordering = ('-created_at',)

    def get_wedding_partner_role(self, obj):
        if obj.user.wedding_partner_role:
            return obj.user.wedding_partner_role.capitalize()
        return '-'

    def _related_querysets(self, obj):
        if not obj:
            return {
                'guests_related': Guest.objects.none(),
                'gifts_related': Gift.objects.none(),
                'wedding_suppliers_related': WeddingSupplier.objects.none(),
                'checklist_tasks_related': ChecklistTask.objects.none(),
            }

        return {
            'guests_related': Guest.objects.filter(wedding_profile=obj).order_by('-created_at'),
            'gifts_related': Gift.objects.filter(wedding_profile=obj).order_by('-created_at'),
            'wedding_suppliers_related': WeddingSupplier.objects.select_related('supplier', 'supplier__category').filter(wedding=obj).order_by('-updated_at'),
            'checklist_tasks_related': ChecklistTask.objects.filter(user=obj.user).order_by('-created_at'),
        }

    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        context.update(self._related_querysets(obj))
        return super().render_change_form(request, context, add, change, form_url, obj)

    def response_change(self, request, obj):
        bulk_entity = request.POST.get('_bulk_delete_related')
        if not bulk_entity:
            return super().response_change(request, obj)

        selected_ids = request.POST.getlist(f'{bulk_entity}_selected_ids')
        if not selected_ids:
            self.message_user(request, 'Selecione ao menos um item para remover.', level=messages.WARNING)
            return redirect(reverse('admin:app_userweddingprofile_change', args=[obj.pk]))

        queryset = None
        entity_label = None

        if bulk_entity == 'guests':
            queryset = Guest.objects.filter(wedding_profile=obj, pk__in=selected_ids)
            entity_label = 'convidado(s)'
        elif bulk_entity == 'gifts':
            queryset = Gift.objects.filter(wedding_profile=obj, pk__in=selected_ids)
            entity_label = 'presente(s)'
        elif bulk_entity == 'wedding_suppliers':
            queryset = WeddingSupplier.objects.filter(wedding=obj, pk__in=selected_ids)
            entity_label = 'fornecedor(es)'
        elif bulk_entity == 'checklist_tasks':
            queryset = ChecklistTask.objects.filter(user=obj.user, pk__in=selected_ids)
            entity_label = 'tarefa(s)'

        if queryset is None:
            self.message_user(request, 'Entidade inválida para remoção em lote.', level=messages.ERROR)
            return redirect(reverse('admin:app_userweddingprofile_change', args=[obj.pk]))

        deleted_count = queryset.count()
        queryset.delete()
        self.message_user(request, f'{deleted_count} {entity_label} removido(s) com sucesso.', level=messages.SUCCESS)
        return redirect(reverse('admin:app_userweddingprofile_change', args=[obj.pk]))


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


class WeddingIdentityInline(admin.StackedInline):
    model = WeddingIdentity
    can_delete = False
    verbose_name_plural = "Identidade do Casamento"
    fk_name = 'wedding_profile'


UserWeddingProfileAdmin.inlines = [WeddingIdentityInline]

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
    list_display = UserAdmin.list_display + ('is_email_confirmed', 'is_2fa_enabled', 'wedding_partner_role',)
    inlines = [UserWeddingProfileInline, WeddingSiteInline]


class WeddingIdentityAdmin(admin.ModelAdmin):
    list_display = ('id', 'wedding_profile', 'selected_style', 'wedding_size', 'dress_code', 'updated_at')
    list_filter = ('selected_style', 'wedding_size', 'dress_code', 'created_at')
    search_fields = ('wedding_profile__user__username', 'wedding_profile__user__email')
    ordering = ('-updated_at',)


class WeddingIdentityInspirationAdmin(admin.ModelAdmin):
    list_display = ('id', 'wedding_profile', 'title', 'selected_style', 'dress_code', 'is_favorite', 'is_liked', 'created_at')
    list_filter = ('selected_style', 'dress_code', 'is_favorite', 'is_liked', 'created_at')
    search_fields = ('title', 'description', 'wedding_profile__user__username', 'source_url')
    ordering = ('-created_at',)


class WeddingIdentityShareTokenAdmin(admin.ModelAdmin):
    list_display = ('wedding_profile', 'token', 'created_at')
    search_fields = ('wedding_profile__user__username', 'token')
    readonly_fields = ('token', 'created_at')


class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'type', 'title', 'message', 'is_read', 'created_at',)
    search_fields = ('user__username', 'message')
    list_filter = ('type', 'is_read')
    ordering = ('-created_at',)


class WeddingImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'url', 'id_cloudinary', 'folder', 'in_use', 'uploaded_at')
    list_filter = ('in_use', 'folder', 'uploaded_at')
    search_fields = ('url', 'id_cloudinary', 'folder')


@admin.register(SupplierCategory)
class SupplierCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug')
    search_fields = ('name', 'slug')


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('id', 'cover_preview', 'name', 'category', 'city', 'state', 'status', 'visibility', 'is_featured', 'created_by_user')
    list_filter = ('status', 'visibility', 'is_featured', 'category', 'state')
    search_fields = ('name', 'company_name', 'description', 'city', 'state', 'email', 'whatsapp')

    def cover_preview(self, obj):
        if not obj.cover_image_url:
          return '-'
        return format_html('<img src="{}" style="width:50px;height:50px;object-fit:cover;border-radius:8px;" />', obj.cover_image_url)
    cover_preview.short_description = 'Capa'


@admin.register(WeddingSupplier)
class WeddingSupplierAdmin(admin.ModelAdmin):
    list_display = ('id', 'wedding', 'supplier', 'status', 'is_hired', 'is_favorite', 'estimated_price', 'negotiated_price', 'paid_amount')
    list_filter = ('status', 'is_hired', 'is_favorite')
    search_fields = ('supplier__name', 'supplier__company_name', 'notes', 'wedding__user__username')


@admin.register(ChecklistTask)
class ChecklistTaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'month', 'description', 'priority', 'status', 'due_date', 'is_template')
    list_filter = ('month', 'priority', 'status', 'is_template')
    search_fields = ('description', 'user__username')

@admin.register(ChecklistTaskAttachment)
class ChecklistTaskAttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'task', 'file', 'uploaded_at')

@admin.register(ChecklistTaskShare)
class ChecklistTaskShareAdmin(admin.ModelAdmin):
    list_display = ('id', 'task', 'email', 'shared_at')

@admin.register(ChecklistTaskNotification)
class ChecklistTaskNotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'task', 'user', 'scheduled_for', 'sent', 'sent_at')


@admin.register(Guest)
class GuestAdmin(admin.ModelAdmin):
    list_display = ('id', 'photo_preview', 'name', 'phone', 'whatsapp', 'email', 'alergias', 'acompanhantes', 'observacoes', 'user', 'wedding_profile', 'created_at', 'updated_at')
    search_fields = ('name', 'phone', 'whatsapp', 'email', 'alergias', 'observacoes', 'user__username', 'wedding_profile__user__username')
    list_filter = ()
    ordering = ('-created_at',)

    def photo_preview(self, obj):
        if not obj.photo_url:
            return '-'
        return format_html('<img src="{}" style="width:50px;height:50px;object-fit:cover;border-radius:8px;" />', obj.photo_url)

    photo_preview.short_description = 'Foto'


@admin.register(Gift)
class GiftAdmin(admin.ModelAdmin):
    list_display = ('id', 'image_preview', 'name', 'value', 'category', 'status', 'wedding_profile', 'purchased_by', 'purchase_date', 'created_at')
    list_filter = ('status', 'category', 'wedding_profile')
    search_fields = ('name', 'description', 'product_code', 'wedding_profile__user__username')
    readonly_fields = ('created_at', 'updated_at')

    def image_preview(self, obj):
        if not obj.image:
            return '-'
        return format_html('<img src="{}" style="width:50px;height:50px;object-fit:cover;border-radius:8px;" />', obj.image)
    image_preview.short_description = 'Imagem'


@admin.register(GiftListShareToken)
class GiftListShareTokenAdmin(admin.ModelAdmin):
    list_display = ('wedding_profile', 'token', 'created_at')
    search_fields = ('wedding_profile__user__username', 'token')
    readonly_fields = ('token', 'created_at')


@admin.register(ProductCatalog)
class ProductCatalogAdmin(admin.ModelAdmin):
    list_display = ('title', 'store', 'category', 'is_essential_template', 'search_term', 'price', 'created_at')
    list_filter = ('store', 'category', 'is_essential_template', 'created_at')
    search_fields = ('title', 'description', 'product_url', 'search_term', 'store')
    readonly_fields = ('created_at', 'updated_at')


# Registre os outros modelos normalmente
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(UserSession, UserSessionAdmin)
admin.site.register(ChatMessage, ChatMessageAdmin)
admin.site.register(UserSettings, UserSettingsAdmin)
admin.site.register(Notification, NotificationAdmin)
admin.site.register(UserWeddingProfile, UserWeddingProfileAdmin)
admin.site.register(WeddingIdentity, WeddingIdentityAdmin)
admin.site.register(WeddingIdentityInspiration, WeddingIdentityInspirationAdmin)
admin.site.register(WeddingIdentityShareToken, WeddingIdentityShareTokenAdmin)
admin.site.register(WeddingSite, WeddingSiteAdmin)
admin.site.register(WeddingSiteHistory, WeddingSiteHistoryAdmin)
admin.site.register(WeddingImage, WeddingImageAdmin)


def amazon_scraper_admin_view(request):
    query = request.GET.get('q', '').strip()
    max_results_raw = request.GET.get('limit', '6').strip()

    try:
        max_results = max(1, min(int(max_results_raw), 12))
    except ValueError:
        max_results = 6

    results = []
    error_message = ''
    service = AmazonScraper(max_results=max_results)

    if query:
        try:
            results = service.search_products(query)
            if not results:
                messages.info(request, 'Nenhum produto foi encontrado na Amazon para esse termo.')
        except Exception as exc:
            error_message = f'Não foi possível consultar {service.marketplace_label} no momento: {exc}'
            messages.error(request, error_message)

    context = admin.site.each_context(request)
    context.update({
        'title': 'Amazon Scraper',
        'page_title': 'Amazon Scraper',
        'provider_label': service.marketplace_label,
        'query': query,
        'max_results': max_results,
        'results': results,
        'results_count': len(results),
        'error_message': error_message,
        'search_url': reverse('admin:amazon_scraper'),
    })
    return render(request, 'admin/amazon_scraper.html', context)


_admin_get_urls = admin.site.get_urls


def _get_admin_urls():
    urls = _admin_get_urls()
    custom_urls = [
        path('amazon-scraper/', admin.site.admin_view(amazon_scraper_admin_view), name='amazon_scraper'),
    ]
    return custom_urls + urls


admin.site.get_urls = _get_admin_urls
