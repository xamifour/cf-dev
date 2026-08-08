# Generated manually for Excel zonal attendance + public visibility + guest speakers

import uuid

import cf_users.mixins
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cf_operations", "0005_alter_event_end_time_alter_event_start_time"),
        ("cf_people", "0003_member_user_composition"),
        ("cf_users", "0004_alter_organizationuser_role"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # --- Drop old individual check-in attendance ---
        migrations.RemoveField(
            model_name="attendancerecord",
            name="member",
        ),
        migrations.RemoveField(
            model_name="attendancerecord",
            name="session",
        ),
        migrations.RemoveField(
            model_name="attendancerecord",
            name="visitor",
        ),
        migrations.RemoveField(
            model_name="attendancesession",
            name="branch",
        ),
        migrations.RemoveField(
            model_name="attendancesession",
            name="created_by",
        ),
        migrations.RemoveField(
            model_name="attendancesession",
            name="event",
        ),
        migrations.RemoveField(
            model_name="attendancesession",
            name="modified_by",
        ),
        migrations.DeleteModel(
            name="AttendanceRecord",
        ),
        migrations.DeleteModel(
            name="AttendanceSession",
        ),
        # --- Event: visibility + event_type ---
        migrations.AddField(
            model_name="event",
            name="event_type",
            field=models.CharField(
                choices=[
                    ("SERVICE", "Service"),
                    ("CONFERENCE", "Conference"),
                    ("OUTREACH", "Outreach"),
                    ("CAMP", "Camp"),
                    ("TRAINING", "Training"),
                    ("MEETING", "Meeting"),
                    ("OTHER", "Other"),
                ],
                db_index=True,
                default="SERVICE",
                max_length=20,
                verbose_name="event type",
            ),
        ),
        migrations.AddField(
            model_name="event",
            name="visibility",
            field=models.CharField(
                choices=[
                    ("PUBLIC", "Public (all platform users)"),
                    ("ORGANIZATION", "Organisation only"),
                ],
                db_index=True,
                default="PUBLIC",
                help_text=(
                    "Public content is visible to any user on the platform. "
                    "Organisation-only content is limited to that church's members and staff."
                ),
                max_length=20,
                verbose_name="visibility",
            ),
        ),
        # --- Sermon: guest speaker + visibility; speaker optional ---
        migrations.AddField(
            model_name="sermon",
            name="guest_speaker_church",
            field=models.CharField(
                blank=True,
                max_length=255,
                verbose_name="guest speaker church / organisation",
            ),
        ),
        migrations.AddField(
            model_name="sermon",
            name="guest_speaker_name",
            field=models.CharField(
                blank=True,
                help_text="Use for guest speakers who are not members of this church.",
                max_length=255,
                verbose_name="guest speaker name",
            ),
        ),
        migrations.AddField(
            model_name="sermon",
            name="guest_speaker_title",
            field=models.CharField(
                blank=True,
                help_text="e.g. Pastor, Evangelist, Bishop.",
                max_length=150,
                verbose_name="guest speaker title",
            ),
        ),
        migrations.AddField(
            model_name="sermon",
            name="visibility",
            field=models.CharField(
                choices=[
                    ("PUBLIC", "Public (all platform users)"),
                    ("ORGANIZATION", "Organisation only"),
                ],
                db_index=True,
                default="PUBLIC",
                help_text=(
                    "Public content is visible to any user on the platform. "
                    "Organisation-only content is limited to that church's members and staff."
                ),
                max_length=20,
                verbose_name="visibility",
            ),
        ),
        migrations.AlterField(
            model_name="sermon",
            name="speaker",
            field=models.ForeignKey(
                blank=True,
                help_text="Optional. Use when the preacher is a registered member.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="sermons",
                to="cf_people.member",
                verbose_name="member speaker",
            ),
        ),
        # --- New Excel-style zonal attendance ---
        migrations.CreateModel(
            name="AttendanceReport",
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
                        auto_now_add=True, db_index=True, verbose_name="created at"
                    ),
                ),
                (
                    "modified_at",
                    models.DateTimeField(auto_now=True, verbose_name="modified at"),
                ),
                (
                    "assembly_name",
                    models.CharField(
                        help_text="e.g. KASOA ASSEMBLY",
                        max_length=255,
                        verbose_name="assembly name",
                    ),
                ),
                (
                    "zone_name",
                    models.CharField(
                        help_text="e.g. ZONE 13",
                        max_length=100,
                        verbose_name="zone",
                    ),
                ),
                (
                    "report_title",
                    models.CharField(
                        help_text="e.g. ZONAL REPORT JUNE 2026",
                        max_length=255,
                        verbose_name="report title",
                    ),
                ),
                (
                    "coordinator_name",
                    models.CharField(
                        blank=True,
                        max_length=255,
                        verbose_name="zonal coordinator name",
                    ),
                ),
                (
                    "week_1_label",
                    models.CharField(
                        blank=True,
                        default="WEEK 1",
                        help_text="e.g. WEEK 1 - 01/08/2026",
                        max_length=100,
                        verbose_name="week 1 label",
                    ),
                ),
                (
                    "week_2_label",
                    models.CharField(
                        blank=True,
                        default="WEEK 2",
                        max_length=100,
                        verbose_name="week 2 label",
                    ),
                ),
                (
                    "week_3_label",
                    models.CharField(
                        blank=True,
                        default="WEEK 3",
                        max_length=100,
                        verbose_name="week 3 label",
                    ),
                ),
                (
                    "week_4_label",
                    models.CharField(
                        blank=True,
                        default="WEEK 4",
                        max_length=100,
                        verbose_name="week 4 label",
                    ),
                ),
                (
                    "week_5_label",
                    models.CharField(
                        blank=True,
                        default="WEEK 5",
                        max_length=100,
                        verbose_name="week 5 label",
                    ),
                ),
                ("notes", models.TextField(blank=True, verbose_name="notes")),
                (
                    "branch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="attendance_reports",
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
                "verbose_name": "attendance report",
                "verbose_name_plural": "attendance reports",
                "ordering": ("-created_at",),
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="AttendanceRecord",
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
                        auto_now_add=True, db_index=True, verbose_name="created at"
                    ),
                ),
                (
                    "modified_at",
                    models.DateTimeField(auto_now=True, verbose_name="modified at"),
                ),
                (
                    "serial_number",
                    models.PositiveIntegerField(default=1, verbose_name="S/N"),
                ),
                (
                    "centre_name",
                    models.CharField(
                        help_text="Cell / centre name as on the sheet.",
                        max_length=255,
                        verbose_name="centre name",
                    ),
                ),
                (
                    "leader_name",
                    models.CharField(
                        blank=True, max_length=255, verbose_name="leader's name"
                    ),
                ),
                (
                    "location",
                    models.CharField(blank=True, max_length=512, verbose_name="location"),
                ),
                (
                    "contact",
                    models.CharField(blank=True, max_length=64, verbose_name="contact"),
                ),
                (
                    "branch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="attendance_records",
                        to="cf_users.branch",
                        verbose_name="branch",
                    ),
                ),
                (
                    "cell_group",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="attendance_records",
                        to="cf_people.subbranch",
                        verbose_name="linked cell group",
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
                (
                    "report",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="records",
                        to="cf_operations.attendancereport",
                        verbose_name="attendance report",
                    ),
                ),
            ],
            options={
                "verbose_name": "attendance record",
                "verbose_name_plural": "attendance records",
                "ordering": ("report", "serial_number", "centre_name"),
                "abstract": False,
            },
            bases=(models.Model, cf_users.mixins.ValidateOrgBranchMixin),
        ),
        migrations.CreateModel(
            name="AttendanceWeekStat",
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
                    "week_number",
                    models.PositiveSmallIntegerField(
                        help_text="1 through 5", verbose_name="week number"
                    ),
                ),
                (
                    "male_adults",
                    models.PositiveIntegerField(
                        default=0, verbose_name="male adult (MA)"
                    ),
                ),
                (
                    "female_adults",
                    models.PositiveIntegerField(
                        default=0, verbose_name="female adult (FA)"
                    ),
                ),
                (
                    "male_children",
                    models.PositiveIntegerField(
                        default=0, verbose_name="male children (MC)"
                    ),
                ),
                (
                    "female_children",
                    models.PositiveIntegerField(
                        default=0, verbose_name="female children (FC)"
                    ),
                ),
                (
                    "total",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Usually MA+FA+MC+FC; stored for sheet fidelity.",
                        verbose_name="total (T)",
                    ),
                ),
                (
                    "new_converts",
                    models.PositiveIntegerField(
                        default=0, verbose_name="new converts (N/C)"
                    ),
                ),
                (
                    "first_timers",
                    models.PositiveIntegerField(
                        default=0, verbose_name="first timers (F/T)"
                    ),
                ),
                (
                    "testimonies",
                    models.PositiveIntegerField(
                        default=0, verbose_name="testimonies (TS)"
                    ),
                ),
                (
                    "record",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="week_stats",
                        to="cf_operations.attendancerecord",
                        verbose_name="attendance record",
                    ),
                ),
            ],
            options={
                "verbose_name": "attendance week stat",
                "verbose_name_plural": "attendance week stats",
                "ordering": ("record", "week_number"),
                "abstract": False,
                "constraints": [
                    models.UniqueConstraint(
                        fields=("record", "week_number"),
                        name="cf_operations_attendanceweekstat_unique_record_week",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(("week_number__gte", 1))
                        & models.Q(("week_number__lte", 5)),
                        name="cf_operations_attendanceweekstat_week_1_5",
                    ),
                ],
            },
        ),
    ]
