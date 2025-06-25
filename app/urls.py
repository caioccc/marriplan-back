from django.urls import path, include
from knox import views as knox_views
from rest_framework.routers import DefaultRouter

from app.viewsets import NotificationViewSet, GoogleLoginView
from app.viewsets import SignUpAPI, SignInAPI, MainUser, UserSessionViewSet, ChatMessageViewSet, UserViewSet, \
    ConfirmEmailAPI, ResendConfirmationEmailAPI, ResetPasswordRequestAPI, ResetPasswordConfirmAPI, delete_all_messages, \
    UserSettingsAPI, delete_all_sessions, generate_2fa_qr, enable_2fa, disable_2fa, PreLoginAPI
from .viewsets import ChecklistTaskViewSet, ChecklistTaskAttachmentViewSet, ChecklistTaskShareViewSet
from .viewsets import GuestViewSet
from .viewsets import UserWeddingProfileViewSet, WeddingSiteViewSet, WeddingSiteHistoryViewSet, public_wedding_site, \
    upload_cloudinary, delete_cloudinary_image
from .viewsets import GiftViewSet

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

user_session_list = UserSessionViewSet.as_view({
    'get': 'list',
    'post': 'create',
})

user_session_detail = UserSessionViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'delete': 'destroy'
})

chat_message_list = ChatMessageViewSet.as_view({
    'get': 'list',
    'post': 'create',
})

chat_message_detail = ChatMessageViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy',
})

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

    path('sessions/', user_session_list, name='user-session-list'),
    path('sessions/<int:pk>/', user_session_detail, name='user-session-detail'),
    path('sessions/delete-by-session-id/<str:session_id>/',
         UserSessionViewSet.as_view({'delete': 'delete_by_session_id'}),
         name='delete-by-session-id'),
    path('sessions/<str:session_id>/', ChatMessageViewSet.as_view({'patch': 'update_title'}),
         name='update-title'),

    path('clear-sessions/delete-all/', delete_all_sessions, name='delete-all-sessions'),

    path('messages/', chat_message_list, name='chat-message-list'),
    path('messages/<int:pk>/', chat_message_detail, name='chat-message-detail'),
    path('messages/send-message/', ChatMessageViewSet.as_view({'post': 'send_message'}), name='send-message'),
    path('messages/stream-message/', ChatMessageViewSet.as_view({'post': 'stream_message'}), name='stream-message'),
    path('messages/delete-all/', delete_all_messages, name='delete-all-messages'),

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

    path('', include(router.urls)),
]
