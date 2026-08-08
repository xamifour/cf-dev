# Session schedule: calendar dates → weekdays (Sun–Sat); check-in back to DateTime.

from django.db import migrations, models
from django.utils import timezone as dj_tz


# Python weekday: Monday=0 … Sunday=6
_PY_WEEKDAY_TO_CODE = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")


def _local_dt(dt):
    if dt is None:
        return None
    if dj_tz.is_aware(dt):
        return dj_tz.localtime(dt)
    return dt


def convert_schedule_to_weekdays(apps, schema_editor):
    EventSession = apps.get_model("cf_operations", "EventSession")
    for session in EventSession.objects.all().iterator():
        update_fields = []

        if session.start_day is not None:
            # start_day still a date during this step
            session.start_day_code = _PY_WEEKDAY_TO_CODE[session.start_day.weekday()]
            update_fields.append("start_day_code")
        if session.end_day is not None:
            session.end_day_code = _PY_WEEKDAY_TO_CODE[session.end_day.weekday()]
            update_fields.append("end_day_code")

        # Recombine split check-in day+time into datetimes when present.
        if session.check_in_start_day and session.check_in_start_time:
            from datetime import datetime

            dt = datetime.combine(session.check_in_start_day, session.check_in_start_time)
            if dj_tz.is_naive(dt):
                dt = dj_tz.make_aware(dt, dj_tz.get_current_timezone())
            session.check_in_start = dt
            update_fields.append("check_in_start")
        if session.check_in_end_day and session.check_in_end_time:
            from datetime import datetime

            dt = datetime.combine(session.check_in_end_day, session.check_in_end_time)
            if dj_tz.is_naive(dt):
                dt = dj_tz.make_aware(dt, dj_tz.get_current_timezone())
            session.check_in_end = dt
            update_fields.append("check_in_end")

        if update_fields:
            session.save(update_fields=update_fields)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("cf_operations", "0010_eventsession_day_and_time_fields"),
    ]

    operations = [
        # Temporary weekday code columns while old DateFields still exist.
        migrations.AddField(
            model_name="eventsession",
            name="start_day_code",
            field=models.CharField(
                blank=True,
                choices=[
                    ("SUN", "Sunday"),
                    ("MON", "Monday"),
                    ("TUE", "Tuesday"),
                    ("WED", "Wednesday"),
                    ("THU", "Thursday"),
                    ("FRI", "Friday"),
                    ("SAT", "Saturday"),
                ],
                db_index=True,
                help_text="Weekday when this session begins (Sunday–Saturday).",
                max_length=3,
                null=True,
                verbose_name="start day",
            ),
        ),
        migrations.AddField(
            model_name="eventsession",
            name="end_day_code",
            field=models.CharField(
                blank=True,
                choices=[
                    ("SUN", "Sunday"),
                    ("MON", "Monday"),
                    ("TUE", "Tuesday"),
                    ("WED", "Wednesday"),
                    ("THU", "Thursday"),
                    ("FRI", "Friday"),
                    ("SAT", "Saturday"),
                ],
                help_text="Weekday when this session ends (Sunday–Saturday).",
                max_length=3,
                null=True,
                verbose_name="end day",
            ),
        ),
        # Restore absolute check-in datetimes.
        migrations.AddField(
            model_name="eventsession",
            name="check_in_start",
            field=models.DateTimeField(
                blank=True,
                help_text="Optional. When check-in / attendance capture opens.",
                null=True,
                verbose_name="check-in start",
            ),
        ),
        migrations.AddField(
            model_name="eventsession",
            name="check_in_end",
            field=models.DateTimeField(
                blank=True,
                help_text="Optional. When check-in / attendance capture closes.",
                null=True,
                verbose_name="check-in end",
            ),
        ),
        migrations.RunPython(convert_schedule_to_weekdays, noop_reverse),
        migrations.RemoveField(model_name="eventsession", name="start_day"),
        migrations.RemoveField(model_name="eventsession", name="end_day"),
        migrations.RemoveField(model_name="eventsession", name="check_in_start_day"),
        migrations.RemoveField(model_name="eventsession", name="check_in_start_time"),
        migrations.RemoveField(model_name="eventsession", name="check_in_end_day"),
        migrations.RemoveField(model_name="eventsession", name="check_in_end_time"),
        migrations.RenameField(
            model_name="eventsession",
            old_name="start_day_code",
            new_name="start_day",
        ),
        migrations.RenameField(
            model_name="eventsession",
            old_name="end_day_code",
            new_name="end_day",
        ),
        migrations.AlterModelOptions(
            name="eventsession",
            options={
                "ordering": ("event", "sort_order", "start_day", "start_time", "name"),
                "verbose_name": "event session",
                "verbose_name_plural": "event sessions",
            },
        ),
    ]
