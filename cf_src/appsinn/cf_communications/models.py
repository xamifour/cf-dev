# cf-dev/cf_src/appsinn/cf_communications/models.py

"""Concrete communications domain models."""

from django.utils.translation import gettext_lazy as _

from cf_users.managers import TenantManager

from django.db import models

from .base.models import (
    AbstractBirthdayGreetingLog,
    AbstractBroadcastMessage,
    AbstractNotification,
    AbstractNotificationTemplate,
)


class Notification(AbstractNotification):
    objects = TenantManager()

    class Meta(AbstractNotification.Meta):
        abstract = False
        verbose_name = _("notification")
        verbose_name_plural = _("notifications")
        # Preserve table created under cf_operations during app extraction.
        db_table = "cf_operations_notification"


class BroadcastMessage(AbstractBroadcastMessage):
    objects = TenantManager()

    class Meta(AbstractBroadcastMessage.Meta):
        abstract = False
        verbose_name = _("broadcast message")
        verbose_name_plural = _("broadcast messages")
        db_table = "cf_operations_broadcastmessage"


class NotificationTemplate(AbstractNotificationTemplate):
    objects = TenantManager()

    class Meta(AbstractNotificationTemplate.Meta):
        abstract = False
        verbose_name = _("notification template")
        verbose_name_plural = _("notification templates")
        db_table = "cf_operations_notificationtemplate"


class BirthdayGreetingLog(AbstractBirthdayGreetingLog):
    """Tracks automatic birthday messages (one per user per year)."""

    objects = models.Manager()

    class Meta(AbstractBirthdayGreetingLog.Meta):
        abstract = False
