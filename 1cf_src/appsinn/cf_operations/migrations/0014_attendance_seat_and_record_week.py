# Generated manually for AttendanceWeekStat → AttendanceSeat + record.week

import django.db.models.deletion
from django.db import migrations, models


def _stat_has_counts(stat) -> bool:
    return any(
        int(getattr(stat, f) or 0)
        for f in (
            "male_adults",
            "female_adults",
            "male_children",
            "female_children",
            "new_converts",
            "first_timers",
            "testimonies",
        )
    )


def migrate_week_stats_to_seats(apps, schema_editor):
    """
    Convert AttendanceWeekStat rows into AttendanceSeat + optional record.week.

    - Empty week slots are dropped (no pre-population of week 1–5).
    - First non-empty week stays on the original record.
    - Further non-empty weeks become additional AttendanceRecord + seat rows.
    """
    AttendanceRecord = apps.get_model("cf_operations", "AttendanceRecord")
    AttendanceWeekStat = apps.get_model("cf_operations", "AttendanceWeekStat")
    AttendanceSeat = apps.get_model("cf_operations", "AttendanceSeat")

    for record in AttendanceRecord.objects.all().iterator():
        stats = list(
            AttendanceWeekStat.objects.filter(record_id=record.pk).order_by(
                "week_number"
            )
        )
        filled = [s for s in stats if _stat_has_counts(s)]
        if not filled:
            continue

        first, *rest = filled
        record.week = first.week_number
        record.save(update_fields=["week"])
        AttendanceSeat.objects.create(
            record_id=record.pk,
            male_adults=first.male_adults or 0,
            female_adults=first.female_adults or 0,
            male_children=first.male_children or 0,
            female_children=first.female_children or 0,
            total=first.total or 0,
            new_converts=first.new_converts or 0,
            first_timers=first.first_timers or 0,
            testimonies=first.testimonies or 0,
        )

        for stat in rest:
            new_rec = AttendanceRecord.objects.create(
                event_id=record.event_id,
                session_id=record.session_id,
                branch_id=record.branch_id,
                zone_id=record.zone_id,
                subgroup_id=record.subgroup_id,
                week=stat.week_number,
                serial_number=record.serial_number,
                centre_name=record.centre_name,
                leader_name=getattr(record, "leader_name", "") or "",
                location=record.location,
                contact=record.contact,
                created_by_id=getattr(record, "created_by_id", None),
                modified_by_id=getattr(record, "modified_by_id", None),
            )
            AttendanceSeat.objects.create(
                record_id=new_rec.pk,
                male_adults=stat.male_adults or 0,
                female_adults=stat.female_adults or 0,
                male_children=stat.male_children or 0,
                female_children=stat.female_children or 0,
                total=stat.total or 0,
                new_converts=stat.new_converts or 0,
                first_timers=stat.first_timers or 0,
                testimonies=stat.testimonies or 0,
            )


class Migration(migrations.Migration):

    dependencies = [
        ("cf_operations", "0013_alter_attendancerecord_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="attendancerecord",
            name="week",
            field=models.PositiveSmallIntegerField(
                blank=True,
                choices=[
                    (1, "1"),
                    (2, "2"),
                    (3, "3"),
                    (4, "4"),
                    (5, "5"),
                ],
                db_index=True,
                help_text=(
                    "Optional. Which week column (1–5) this record maps to on the "
                    "Excel-style preview sheet."
                ),
                null=True,
                verbose_name="week",
            ),
        ),
        migrations.CreateModel(
            name="AttendanceSeat",
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
                        help_text="Usually MA+FA+MC+FC; recomputed on save.",
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
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="seat",
                        to="cf_operations.attendancerecord",
                        verbose_name="attendance record",
                    ),
                ),
            ],
            options={
                "verbose_name": "attendance seat",
                "verbose_name_plural": "attendance seats",
                "ordering": ("record",),
                "abstract": False,
            },
        ),
        migrations.RunPython(
            migrate_week_stats_to_seats,
            migrations.RunPython.noop,
        ),
        migrations.DeleteModel(
            name="AttendanceWeekStat",
        ),
    ]
