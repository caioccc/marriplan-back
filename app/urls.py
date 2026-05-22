from django.urls import path, include
from rest_framework.routers import DefaultRouter

from app.viewsets.auth import SignUpAPI, SignInAPI, PreLoginAPI, ConfirmEmailAPI, ResendConfirmationEmailAPI, \
     ResetPasswordRequestAPI, ResetPasswordConfirmAPI, generate_2fa_qr, enable_2fa, disable_2fa, GoogleLoginView, LogoutAPI
from app.viewsets.checklist import ChecklistTaskViewSet, ChecklistTaskAttachmentViewSet, ChecklistTaskShareViewSet
from app.viewsets.gift import GiftViewSet, GiftListShareTokenView, PublicGiftListView
from app.viewsets.guest import GuestViewSet
from app.viewsets.supplier import SupplierCategoryViewSet, SupplierViewSet, WeddingSupplierViewSet
from app.viewsets.user import NotificationViewSet, UserViewSet, UserWeddingProfileViewSet, MainUser, UserSettingsAPI
from app.viewsets.utility import upload_cloudinary, upload_cloudinary_file, delete_cloudinary_image
from app.viewsets.wedding_identity import WeddingIdentityViewSet
from app.viewsets.wedding_identity_inspiration import WeddingIdentityInspirationViewSet, PublicWeddingIdentityView
from app.viewsets.wedding import WeddingSiteViewSet, WeddingSiteHistoryViewSet, public_wedding_site

router = DefaultRouter()
router.register(r'wedding-identity', WeddingIdentityViewSet, basename='wedding-identity')
router.register(r'wedding-profile', UserWeddingProfileViewSet, basename='wedding-profile')
router.register(r'wedding-site', WeddingSiteViewSet, basename='wedding-site')
router.register(r'wedding-site-history', WeddingSiteHistoryViewSet, basename='wedding-site-history')
router.register(r'checklist-tasks', ChecklistTaskViewSet, basename='checklisttask')
router.register(r'checklist-attachments', ChecklistTaskAttachmentViewSet, basename='checklisttaskattachment')
router.register(r'checklist-shares', ChecklistTaskShareViewSet, basename='checklisttaskshare')
router.register(r'guests', GuestViewSet, basename='guest')
router.register(r'gifts', GiftViewSet, basename='gift')
router.register(r'supplier-categories', SupplierCategoryViewSet, basename='supplier-category')
router.register(r'suppliers', SupplierViewSet, basename='supplier')
router.register(r'wedding-suppliers', WeddingSupplierViewSet, basename='wedding-supplier')

urlpatterns = []

notification_list = NotificationViewSet.as_view({'get': 'list', 'post': 'create'})
notification_detail = NotificationViewSet.as_view({'get': 'retrieve', 'delete': 'destroy'})
wedding_identity_singleton = WeddingIdentityViewSet.as_view({
    'get': 'list',
    'post': 'create',
    'patch': 'me',
    'delete': 'me',
})
wedding_identity_share_token = WeddingIdentityViewSet.as_view({'post': 'share_token'})
wedding_identity_inspirations_list = WeddingIdentityInspirationViewSet.as_view({'get': 'list', 'post': 'create'})
wedding_identity_inspirations_detail = WeddingIdentityInspirationViewSet.as_view(
    {'patch': 'partial_update', 'delete': 'destroy'})
wedding_identity_inspirations_search = WeddingIdentityInspirationViewSet.as_view({'get': 'search'})

urlpatterns += [
    path('auth/register/', SignUpAPI.as_view(), name="knox_register"),
    path('auth/login/', SignInAPI.as_view(), name="knox_login"),
    path('auth/user/', MainUser.as_view(), name="knox_user"),
     path('auth/logout/', LogoutAPI.as_view(), name="knox_logout"),
    path('auth/confirm-email/', ConfirmEmailAPI.as_view(), name='confirm-email'),
    path('auth/resend-confirmation/', ResendConfirmationEmailAPI.as_view(), name='resend-confirmation'),
    path('auth/reset-password/', ResetPasswordRequestAPI.as_view(), name='reset-password'),
    path('auth/reset-password/confirm/', ResetPasswordConfirmAPI.as_view(), name='reset-password-confirm'),
    path('auth/2fa/generate/', generate_2fa_qr, name='generate-2fa-qr'),
    path('auth/2fa/enable/', enable_2fa, name='enable-2fa'),
    path('auth/2fa/disable/', disable_2fa, name='disable-2fa'),
    path('auth/pre-login/', PreLoginAPI.as_view(), name='pre-login'),
    path('auth/google/', GoogleLoginView.as_view(), name='google_login'),

    path('user/', UserViewSet.as_view({'get': 'list'}), name="user"),
    path('user/update-profile/', UserViewSet.as_view({'patch': 'update_profile'}), name='update-profile'),

    path('user/<int:pk>/', UserViewSet.as_view({'get': 'retrieve'}), name="user"),

    path('settings/', UserSettingsAPI.as_view(), name='user-settings'),

    path('notifications/', notification_list, name='notification-list'),
    path('notifications/<int:pk>/', notification_detail, name='notification-detail'),
    path('notifications/unread/', NotificationViewSet.as_view({'get': 'unread'}), name='notification-unread'),
    path('notifications/mark-all-read/', NotificationViewSet.as_view({'post': 'mark_all_read'}),
         name='notification-mark-all-read'),
    path('notifications/mark-all-unread/', NotificationViewSet.as_view({'post': 'mark_all_unread'}),
         name='notification-mark-all-unread'),
    path('notifications/<int:pk>/mark-read/', NotificationViewSet.as_view({'post': 'mark_read'}),
         name='notification-mark-read'),
    path('notifications/<int:pk>/mark-unread/', NotificationViewSet.as_view({'post': 'mark_unread'}),
         name='notification-mark-unread'),
    path('notifications/delete-all/', NotificationViewSet.as_view({'delete': 'delete_all'}),
         name='notification-delete-all'),

    path('site/<slug:slug>/', public_wedding_site, name='public-wedding-site'),

    path('upload-cloudinary/', upload_cloudinary, name='upload-cloudinary'),
    path('upload-cloudinary-file/', upload_cloudinary_file, name='upload-cloudinary-file'),
    path('delete-cloudinary-image/', delete_cloudinary_image, name='delete-cloudinary-image'),

    path('gifts/share-token/', GiftListShareTokenView.as_view(), name='gift-share-token'),
    path('gifts/public/<str:token>/', PublicGiftListView.as_view(), name='public-gift-list'),

    path('wedding-identity/', wedding_identity_singleton, name='wedding-identity-singleton'),
     path('wedding-identity/share-token/', wedding_identity_share_token, name='wedding-identity-share-token'),
    path('wedding-identity/inspirations/', wedding_identity_inspirations_list,
         name='wedding-identity-inspirations-list'),
    path('wedding-identity/inspirations/search/', wedding_identity_inspirations_search,
         name='wedding-identity-inspirations-search'),
    path('wedding-identity/inspirations/<int:pk>/', wedding_identity_inspirations_detail,
         name='wedding-identity-inspirations-detail'),

     path('public/wedding-identity/<str:token>/', PublicWeddingIdentityView.as_view(), name='public-wedding-identity'),

    path('', include(router.urls)),
]
