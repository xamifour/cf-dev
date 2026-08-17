# cf-dev/cf_src/appsinn/cf_communications/migrations/0001_initial_from_operations.py

"""
Take ownership of communications models previously defined under cf_operations.

Database tables are reused (db_table keeps cf_operations_* names); only Django
state is updated here.
"""

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("cf_operations", "0003_initial"),
        ("cf_users", "0002_organization_code_autogen"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="BroadcastMessage",
                    fields=[
                        (
                            "id",
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name="ID",
                            ),
                        ),
                        (
                            "title",
                            models.CharField(
                                max_length=150, verbose_name="campaign title"
                            ),
                        ),
                        (
                            "body",
                            models.TextField(
                                help_text=(
                                    "Full message text used for email and in-app "
                                    "channels."
                                ),
                                verbose_name="body",
                            ),
                        ),
                        (
                            "sms_text",
                            models.TextField(
                                blank=True,
                                help_text=(
                                    "Condensed copy for SMS dispatch. Falls back to "
                                    "a truncated body if blank."
                                ),
                                null=True,
                                verbose_name="SMS copy",
                            ),
                        ),
                        (
                            "channels",
                            models.JSONField(
                                default=list,
                                help_text='e.g. ["email", "sms", "whatsapp"]',
                                verbose_name="channels",
                            ),
                        ),
                        (
                            "target_all",
                            models.BooleanField(
                                default=True, verbose_name="target all active members"
                            ),
                        ),
                        (
                            "only_active_members",
                            models.BooleanField(
                                default=True, verbose_name="active members only"
                            ),
                        ),
                        (
                            "target_absent_members",
                            models.BooleanField(
                                default=False,
                                help_text=(
                                    "If True, limits recipients to members absent "
                                    "for at least 'absence_days'."
                                ),
                                verbose_name="target absent members",
                            ),
                        ),
                        (
                            "absence_days",
                            models.PositiveIntegerField(
                                blank=True,
                                help_text=(
                                    "Minimum days since last attendance. Required "
                                    "when targeting absent members."
                                ),
                                null=True,
                                verbose_name="absence threshold (days)",
                            ),
                        ),
                        (
                            "status",
                            models.CharField(
                                choices=[
                                    ("DRAFT", "Draft"),
                                    ("SENDING", "Sending"),
                                    ("SENT", "Sent"),
                                    ("FAILED", "Failed"),
                                ],
                                db_index=True,
                                default="DRAFT",
                                max_length=16,
                                verbose_name="status",
                            ),
                        ),
                        (
                            "recipients_targeted",
                            models.PositiveIntegerField(
                                default=0,
                                editable=False,
                                verbose_name="recipients targeted",
                            ),
                        ),
                        (
                            "recipients_sent",
                            models.PositiveIntegerField(
                                default=0,
                                editable=False,
                                verbose_name="recipients sent",
                            ),
                        ),
                        (
                            "recipients_failed",
                            models.PositiveIntegerField(
                                default=0,
                                editable=False,
                                verbose_name="recipients failed",
                            ),
                        ),
                        (
                            "sent_at",
                            models.DateTimeField(
                                blank=True,
                                editable=False,
                                null=True,
                                verbose_name="sent at",
                            ),
                        ),
                        (
                            "created_at",
                            models.DateTimeField(
                                auto_now_add=True, verbose_name="created at"
                            ),
                        ),
                        (
                            "branches",
                            models.ManyToManyField(
                                blank=True,
                                help_text=(
                                    "Leave empty to target all branches of the "
                                    "organisation."
                                ),
                                related_name="broadcasts",
                                to="cf_users.branch",
                                verbose_name="target branches",
                            ),
                        ),
                        (
                            "organization",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="broadcasts",
                                to="cf_users.organization",
                                verbose_name="organisation",
                            ),
                        ),
                    ],
                    options={
                        "verbose_name": "broadcast message",
                        "verbose_name_plural": "broadcast messages",
                        "db_table": "cf_operations_broadcastmessage",
                        "ordering": ("-created_at",),
                        "abstract": False,
                    },
                ),
                migrations.CreateModel(
                    name="Notification",
                    fields=[
                        (
                            "id",
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name="ID",
                            ),
                        ),
                        (
                            "notification_type",
                            models.CharField(
                                choices=[
                                    ("info", "Information"),
                                    ("warning", "Warning"),
                                    ("alert", "Urgent / Alert"),
                                ],
                                default="info",
                                max_length=20,
                                verbose_name="type",
                            ),
                        ),
                        (
                            "title",
                            models.CharField(
                                blank=True, max_length=150, verbose_name="title"
                            ),
                        ),
                        ("message", models.TextField(verbose_name="message")),
                        (
                            "seen",
                            models.BooleanField(
                                db_index=True, default=False, verbose_name="seen"
                            ),
                        ),
                        (
                            "created_at",
                            models.DateTimeField(
                                auto_now_add=True,
                                db_index=True,
                                verbose_name="created at",
                            ),
                        ),
                        (
                            "updated_at",
                            models.DateTimeField(
                                auto_now=True, verbose_name="updated at"
                            ),
                        ),
                        (
                            "branch",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="%(class)s_branch_notifications",
                                to="cf_users.branch",
                                verbose_name="branch",
                            ),
                        ),
                        (
                            "broadcast",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.SET_NULL,
                                related_name="sent_notifications",
                                to="cf_communications.broadcastmessage",
                                verbose_name="related broadcast",
                            ),
                        ),
                        (
                            "organization",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="%(class)s_notifications",
                                to="cf_users.organization",
                                verbose_name="organisation",
                            ),
                        ),
                        (
                            "recipient",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="notifications",
                                to=settings.AUTH_USER_MODEL,
                                verbose_name="recipient",
                            ),
                        ),
                    ],
                    options={
                        "verbose_name": "notification",
                        "verbose_name_plural": "notifications",
                        "db_table": "cf_operations_notification",
                        "ordering": ("-created_at",),
                        "abstract": False,
                    },
                ),
                migrations.CreateModel(
                    name="NotificationTemplate",
                    fields=[
                        (
                            "id",
                            models.UUIDField(
                                default=uuid.uuid4,
                                editable=False,
                                primary_key=True,
                                serialize=False,
                            ),
                        ),
                        (
                            "created_at",
                            models.DateTimeField(
                                auto_now_add=True,
                                db_index=True,
                                verbose_name="created at",
                            ),
                        ),
                        (
                            "modified_at",
                            models.DateTimeField(
                                auto_now=True, verbose_name="modified at"
                            ),
                        ),
                        ("name", models.CharField(max_length=255, verbose_name="name")),
                        (
                            "channel",
                            models.CharField(
                                choices=[
                                    ("EMAIL", "Email"),
                                    ("SMS", "SMS"),
                                    ("IN_APP", "In-App"),
                                    ("WHATSAPP", "WhatsApp"),
                                ],
                                max_length=20,
                                verbose_name="channel",
                            ),
                        ),
                        (
                            "subject",
                            models.CharField(
                                blank=True,
                                max_length=255,
                                verbose_name="subject / title",
                            ),
                        ),
                        (
                            "body_content",
                            models.TextField(
                                help_text=(
                                    "Supports Django template tag variables, e.g. "
                                    "{{ member.first_name }}."
                                ),
                                verbose_name="body content",
                            ),
                        ),
                        (
                            "branch",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.PROTECT,
                                related_name="notification_templates",
                                to="cf_users.branch",
                                verbose_name="branch",
                            ),
                        ),
                        (
                            "created_by",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.SET_NULL,
                                related_name="%(app_label)s_%(class)s_created",
                                to=settings.AUTH_USER_MODEL,
                                verbose_name="created by",
                            ),
                        ),
                        (
                            "modified_by",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.SET_NULL,
                                related_name="%(app_label)s_%(class)s_modified",
                                to=settings.AUTH_USER_MODEL,
                                verbose_name="modified by",
                            ),
                        ),
                    ],
                    options={
                        "verbose_name": "notification template",
                        "verbose_name_plural": "notification templates",
                        "db_table": "cf_operations_notificationtemplate",
                        "abstract": False,
                        "unique_together": {("branch", "name", "channel")},
                    },
                ),
            ],
            database_operations=[],
        ),
    ]
