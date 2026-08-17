# Generated manually: month, attendance_at, location_provider, leader FK

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cf_operations", "0014_attendance_seat_and_record_week"),
        ("cf_people", "0010_member_org_scoped_number"),
    ]

    operations = [
        migrations.AddField(
            model_name="attendancerecord",
            name="month",
            field=models.PositiveSmallIntegerField(
                blank=True,
                choices=[
                    (1, "January"),
                    (2, "February"),
                    (3, "March"),
                    (4, "April"),
                    (5, "May"),
                    (6, "June"),
                    (7, "July"),
                    (8, "August"),
                    (9, "September"),
                    (10, "October"),
                    (11, "November"),
                    (12, "December"),
                ],
                db_index=True,
                help_text=(
                    "Optional. Calendar month this attendance relates to "
                    "(January–December)."
                ),
                null=True,
                verbose_name="month",
            ),
        ),
        migrations.AddField(
            model_name="attendancerecord",
            name="attendance_at",
            field=models.DateTimeField(
                blank=True,
                db_index=True,
                help_text="Optional. When this attendance was taken.",
                null=True,
                verbose_name="attendance date/time",
            ),
        ),
        migrations.AddField(
            model_name="attendancerecord",
            name="location_provider",
            field=models.CharField(
                blank=True,
                help_text="Optional. Who provided or hosts this location.",
                max_length=255,
                verbose_name="location provider",
            ),
        ),
        migrations.AddField(
            model_name="attendancerecord",
            name="leader",
            field=models.ForeignKey(
                blank=True,
                help_text="Optional. Cell / centre leader (member).",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="led_attendance_records",
                to="cf_people.member",
                verbose_name="leader",
            ),
        ),
        migrations.RemoveField(
            model_name="attendancerecord",
            name="leader_name",
        ),
    ]
