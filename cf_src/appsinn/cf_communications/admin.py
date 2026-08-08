# cf-dev/cf_src/appsinn/cf_communications/admin.py

"""Admin registrations for communications domain models."""

from django.contrib import admin

from cf_users.multitenancy import (
    MultitenantAdminMixin,
    MultitenantBranchFilter,
    MultitenantOrgFilter,
)
from cf_users.utils import BaseAdmin

from .models import (
    BirthdayGreetingLog,
    BroadcastMessage,
    Notification,
    NotificationTemplate,
)


@admin.register(Notification)
class NotificationAdmin(MultitenantAdminMixin, BaseAdmin):
    list_display = (
        "title",
        "recipient",
        "branch",
        "notification_type",
        "seen",
        "created_at",
    )
    list_filter = (
        MultitenantBranchFilter,
        MultitenantOrgFilter,
        "notification_type",
        "seen",
    )
    search_fields = ("title", "message", "recipient__username")
    autocomplete_fields = ("organization", "branch", "recipient", "broadcast")


@admin.register(BroadcastMessage)
class BroadcastMessageAdmin(MultitenantAdminMixin, BaseAdmin):
    list_display = (
        "title",
        "organization",
        "status",
        "recipients_targeted",
        "recipients_sent",
        "created_at",
    )
    list_filter = (MultitenantOrgFilter, "status")
    search_fields = ("title",)
    filter_horizontal = ("branches",)
    autocomplete_fields = ("organization",)


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(MultitenantAdminMixin, BaseAdmin):
    list_display = ("name", "branch", "channel")
    list_filter = (MultitenantBranchFilter, "channel")
    search_fields = ("name",)
    autocomplete_fields = ("branch",)


@admin.register(BirthdayGreetingLog)
class BirthdayGreetingLogAdmin(BaseAdmin):
    list_display = ("user", "year", "for_date", "channel_summary", "sent_at")
    list_filter = ("year",)
    search_fields = (
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
    )
    autocomplete_fields = ("user",)
    readonly_fields = ("user", "year", "for_date", "channel_summary", "sent_at")

    def has_add_permission(self, request):
        return False
