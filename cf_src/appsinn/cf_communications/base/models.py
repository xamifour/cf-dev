# cf-dev/cf_src/appsinn/cf_communications/base/models.py

"""
Abstract communications models: notifications, broadcasts, templates.
Concrete implementations live in cf_communications.models.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from cf_users.mixins import AuditMixin

from ..utils import send_email, send_inapp, send_sms, send_whatsapp

logger = logging.getLogger(__name__)


class AbstractNotification(models.Model):
    """A single notification delivered to one recipient."""

    TYPE_CHOICES = [
        ("info", _("Information")),
        ("warning", _("Warning")),
        ("alert", _("Urgent / Alert")),
    ]
    organization = models.ForeignKey(
        "cf_users.Organization",
        on_delete=models.CASCADE,
        related_name="%(class)s_notifications",
        verbose_name=_("organisation"),
    )
    branch = models.ForeignKey(
        "cf_users.Branch",
        on_delete=models.CASCADE,
        related_name="%(class)s_branch_notifications",
        verbose_name=_("branch"),
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name=_("recipient"),
    )
    notification_type = models.CharField(
        _("type"), max_length=20, choices=TYPE_CHOICES, default="info"
    )
    title = models.CharField(_("title"), max_length=150, blank=True)
    message = models.TextField(_("message"))
    seen = models.BooleanField(_("seen"), default=False, db_index=True)
    broadcast = models.ForeignKey(
        "cf_communications.BroadcastMessage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_notifications",
        verbose_name=_("related broadcast"),
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        abstract = True
        # No AuditMixin; use updated_at as “last modified”.
        ordering = ("-updated_at", "-created_at")

    def __str__(self) -> str:
        return (
            f"[{self.get_notification_type_display()}] "
            f"{self.recipient} – {self.message[:40]}"
        )

    @classmethod
    def create_and_notify(
        cls,
        *,
        recipient,
        branch,
        title: str,
        message: str,
        sms_text: str | None = None,
        wa_template: str | None = None,
        wa_params: list | None = None,
        notif_type: str = "info",
        broadcast=None,
    ):
        """Persist notification and dispatch via enabled channels."""
        organization = branch.organization
        email = getattr(recipient, "email", None)
        phone = getattr(recipient, "phone_number", None)
        org_muted = not getattr(organization, "notifications_enabled", True)
        branch_muted = not getattr(branch, "notifications_enabled", True)

        with transaction.atomic():
            notification = cls.objects.create(
                organization=organization,
                branch=branch,
                recipient=recipient,
                notification_type=notif_type,
                title=title,
                message=message,
                broadcast=broadcast,
            )

        if org_muted or branch_muted:
            logger.info(
                "Notification muted by org/branch policy (org=%s, branch=%s).",
                organization.pk,
                branch.pk,
            )
            return notification

        if getattr(recipient, "notify_via_inapp", True):
            try:
                send_inapp(
                    title=title,
                    message=message,
                    recipients=[recipient],
                    notification_type=notif_type,
                    extra={
                        "notification_id": str(notification.pk),
                        "branch_id": str(branch.pk),
                        "unread_count": cls.objects.filter(
                            recipient=recipient, seen=False
                        ).count(),
                    },
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("In-app dispatch failed for %s: %s", recipient.pk, exc)

        if getattr(recipient, "notify_via_email", True) and email:
            try:
                send_email(subject=title, body_text=message, recipients=[email])
            except Exception as exc:  # noqa: BLE001
                logger.warning("Email dispatch failed for %s: %s", email, exc)

        if getattr(recipient, "notify_via_sms", False) and phone:
            try:
                send_sms(message=sms_text or message, recipients=[str(phone)])
            except Exception as exc:  # noqa: BLE001
                logger.warning("SMS dispatch failed for %s: %s", phone, exc)

        if getattr(recipient, "notify_via_whatsapp", False) and phone:
            try:
                send_whatsapp(
                    phone_number=str(phone),
                    template_name=wa_template,
                    parameters=wa_params or [],
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("WhatsApp dispatch failed for %s: %s", phone, exc)

        return notification

    @classmethod
    def already_sent(cls, recipient, keyword: str, hours: int = 12) -> bool:
        """Return True if a matching notification was sent within the last N hours."""
        cutoff = timezone.now() - timedelta(hours=hours)
        return cls.objects.filter(
            recipient=recipient,
            message__icontains=keyword,
            created_at__gte=cutoff,
        ).exists()


class AbstractBirthdayGreetingLog(models.Model):
    """
    Idempotency log for automatic birthday greetings.

    One row per user per calendar year prevents duplicate sends when the
    daily Celery beat task re-runs.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="birthday_greeting_logs",
        verbose_name=_("user"),
    )
    year = models.PositiveIntegerField(_("year"), db_index=True)
    for_date = models.DateField(
        _("birthday date"),
        help_text=_("The calendar date (this year) the greeting was for."),
    )
    channel_summary = models.CharField(
        _("channels used"),
        max_length=120,
        blank=True,
        help_text=_("e.g. email,inapp"),
    )
    sent_at = models.DateTimeField(_("sent at"), auto_now_add=True, db_index=True)

    class Meta:
        abstract = True
        ordering = ("-sent_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["user", "year"],
                name="%(app_label)s_%(class)s_unique_user_year",
            ),
        ]
        verbose_name = _("birthday greeting log")
        verbose_name_plural = _("birthday greeting logs")

    def __str__(self) -> str:
        return f"{self.user} · {self.year}"


class AbstractBroadcastMessage(models.Model):
    """A mass-communication campaign targeting one or more branches."""

    STATUS_CHOICES = [
        ("DRAFT", _("Draft")),
        ("SENDING", _("Sending")),
        ("SENT", _("Sent")),
        ("FAILED", _("Failed")),
    ]
    organization = models.ForeignKey(
        "cf_users.Organization",
        on_delete=models.CASCADE,
        related_name="broadcasts",
        verbose_name=_("organisation"),
    )
    title = models.CharField(_("campaign title"), max_length=150)
    body = models.TextField(
        _("body"),
        help_text=_("Full message text used for email and in-app channels."),
    )
    sms_text = models.TextField(
        _("SMS copy"),
        blank=True,
        null=True,
        help_text=_(
            "Condensed copy for SMS dispatch. Falls back to a truncated body if blank."
        ),
    )
    channels = models.JSONField(
        _("channels"),
        default=list,
        help_text=_('e.g. ["email", "sms", "whatsapp"]'),
    )
    branches = models.ManyToManyField(
        "cf_users.Branch",
        blank=True,
        related_name="broadcasts",
        verbose_name=_("target branches"),
        help_text=_("Leave empty to target all branches of the organisation."),
    )
    target_all = models.BooleanField(_("target all active members"), default=True)
    only_active_members = models.BooleanField(_("active members only"), default=True)
    target_absent_members = models.BooleanField(
        _("target absent members"),
        default=False,
        help_text=_(
            "If True, limits recipients to members absent for at least 'absence_days'."
        ),
    )
    absence_days = models.PositiveIntegerField(
        _("absence threshold (days)"),
        null=True,
        blank=True,
        help_text=_(
            "Minimum days since last attendance. Required when targeting absent members."
        ),
    )
    status = models.CharField(
        _("status"),
        max_length=16,
        choices=STATUS_CHOICES,
        default="DRAFT",
        db_index=True,
    )
    recipients_targeted = models.PositiveIntegerField(
        _("recipients targeted"), default=0, editable=False
    )
    recipients_sent = models.PositiveIntegerField(
        _("recipients sent"), default=0, editable=False
    )
    recipients_failed = models.PositiveIntegerField(
        _("recipients failed"), default=0, editable=False
    )
    sent_at = models.DateTimeField(_("sent at"), null=True, blank=True, editable=False)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        abstract = True
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return self.title

    def clean(self) -> None:
        errors: dict = {}
        if self.target_absent_members:
            if not self.absence_days or self.absence_days < 1:
                errors["absence_days"] = _(
                    "Specify an absence threshold of at least 1 day when targeting "
                    "absent members."
                )
            if self.target_all:
                errors["target_all"] = _(
                    "Cannot target all members and absent members simultaneously."
                )
        if errors:
            raise ValidationError(errors)

    def get_sms_body(self) -> str:
        if self.sms_text:
            return self.sms_text
        return (self.body[:157] + "…") if len(self.body) > 160 else self.body

    def get_recipient_queryset(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        qs = User.objects.filter(is_active=True)
        if self.branches.exists():
            qs = qs.filter(branch_roles__branch__in=self.branches.all())
        else:
            qs = qs.filter(org_roles__organization=self.organization)
        if self.target_all:
            return qs.distinct()
        if self.target_absent_members and self.absence_days:
            cutoff = timezone.now() - timedelta(days=self.absence_days)
            qs = qs.annotate(
                last_attendance=models.Max(
                    "member_profile__attendance_records__check_in_time"
                )
            ).filter(
                models.Q(last_attendance__lt=cutoff)
                | models.Q(last_attendance__isnull=True)
            )
        elif self.only_active_members:
            qs = qs.filter(member_profile__membership_status="ACTIVE")
        return qs.distinct()


class AbstractNotificationTemplate(AuditMixin):
    """Reusable message template for automated notifications."""

    CHANNEL_CHOICES = [
        ("EMAIL", _("Email")),
        ("SMS", _("SMS")),
        ("IN_APP", _("In-App")),
        ("WHATSAPP", _("WhatsApp")),
    ]
    branch = models.ForeignKey(
        "cf_users.Branch",
        on_delete=models.PROTECT,
        related_name="notification_templates",
        verbose_name=_("branch"),
    )
    name = models.CharField(_("name"), max_length=255)
    channel = models.CharField(_("channel"), max_length=20, choices=CHANNEL_CHOICES)
    subject = models.CharField(_("subject / title"), max_length=255, blank=True)
    body_content = models.TextField(
        _("body content"),
        help_text=_(
            "Supports Django template tag variables, e.g. {{ member.first_name }}."
        ),
    )

    class Meta:
        abstract = True
        unique_together = ("branch", "name", "channel")

    def __str__(self) -> str:
        return f"{self.name} ({self.get_channel_display()})"
