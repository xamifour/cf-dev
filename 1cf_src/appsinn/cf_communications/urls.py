# cf-dev/cf_src/appsinn/gmtisp_communications/urls.py

from django.urls import path
from . import views

urlpatterns = [

    # ── Notifications (bell) ──────────────────────────────────────────────────
    path("notifications/",
         views.notifications_list,
         name="notifications_list"),

    path("notifications/api/",
         views.notifications_api,
         name="notifications_api"),

    path("notifications/mark-all-read/",
         views.mark_all_notifications_read,
         name="mark_all_notifications_read"),

    path("notifications/<uuid:notification_id>/read/",
         views.mark_notification_read,
         name="mark_notification_read"),

    path("notifications/<uuid:notification_id>/",
         views.NotificationDetailView.as_view(),
         name="notification_detail"),

    # ── Broadcast messages (envelope) ─────────────────────────────────────────
    path("messages/",
         views.broadcast_messages_list,
         name="broadcast_messages_list"),

    path("messages/api/",
         views.broadcast_messages_api,
         name="broadcast_messages_api"),

    path("messages/api/count/",
         views.broadcast_messages_count_api,
         name="broadcast_messages_count_api"),

    path("messages/<uuid:broadcast_id>/",
         views.BroadcastMessageDetailView.as_view(),
         name="broadcast_message_detail"),

    # ── Terms and Conditions ──────────────────────────────────────────────────
    path("terms-and-conditions/",
         views.TermsAndConditionsView.as_view(),
         name="terms_and_conditions"),

]