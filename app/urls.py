from django.urls import path, include
from knox import views as knox_views
from rest_framework.routers import DefaultRouter

from app.viewsets.auth import SignUpAPI, SignInAPI, PreLoginAPI, ConfirmEmailAPI, ResendConfirmationEmailAPI, \
    ResetPasswordRequestAPI, ResetPasswordConfirmAPI, generate_2fa_qr, enable_2fa, disable_2fa, GoogleLoginView
from app.viewsets.checklist import ChecklistTaskViewSet, ChecklistTaskAttachmentViewSet, ChecklistTaskShareViewSet
from app.viewsets.gift import GiftViewSet, GiftListShareTokenView, PublicGiftListView
from app.viewsets.guest import GuestViewSet
from app.viewsets.user import NotificationViewSet, UserViewSet, UserWeddingProfileViewSet, MainUser, UserSettingsAPI
from app.viewsets.utility import upload_cloudinary, delete_cloudinary_image
from app.viewsets.wedding import WeddingSiteViewSet, WeddingSiteHistoryViewSet, public_wedding_site

router = DefaultRouter()
router.register(r'wedding-profile', UserWeddingProfileViewSet, basename='wedding-profile')
router.register(r'wedding-site', WeddingSiteViewSet, basename='wedding-site')
router.register(r'wedding-site-history', WeddingSiteHistoryViewSet, basename='wedding-site-history')
router.register(r'checklist-tasks', ChecklistTaskViewSet, basename='checklisttask')
router.register(r'checklist-attachments', ChecklistTaskAttachmentViewSet, basename='checklisttaskattachment')
router.register(r'checklist-shares', ChecklistTaskShareViewSet, basename='checklisttaskshare')
router.register(r'guests', GuestViewSet, basename='guest')
router.register(r'gifts', GiftViewSet, basename='gift')

urlpatterns = []


notification_list = NotificationViewSet.as_view({'get': 'list', 'post': 'create'})
notification_detail = NotificationViewSet.as_view({'get': 'retrieve', 'delete': 'destroy'})

urlpatterns += [
    path('auth/register/', SignUpAPI.as_view(), name="knox_register"),
    path('auth/login/', SignInAPI.as_view(), name="knox_login"),
    path('auth/user/', MainUser.as_view(), name="knox_user"),
    path('auth/logout/', knox_views.LogoutView.as_view(), name="knox_logout"),
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
    path('delete-cloudinary-image/', delete_cloudinary_image, name='delete-cloudinary-image'),

    path('gifts/share-token/', GiftListShareTokenView.as_view(), name='gift-share-token'),
    path('gifts/public/<str:token>/', PublicGiftListView.as_view(), name='public-gift-list'),

    path('', include(router.urls)),
]
