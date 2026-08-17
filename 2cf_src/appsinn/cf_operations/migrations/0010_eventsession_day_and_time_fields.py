# Generated manually: split EventSession DateTime schedule into day + time.

from django.db import migrations, models
from django.utils import timezone as dj_tz


def _local_parts(dt):
    """Return (date, time) in the active timezone for a stored datetime."""
    if dt is None:
        return None, None
    if dj_tz.is_aware(dt):
        dt = dj_tz.localtime(dt)
    return dt.date(), dt.time().replace(microsecond=0)


def split_session_datetimes(apps, schema_editor):
    EventSession = apps.get_model("cf_operations", "EventSession")
    for session in EventSession.objects.all().iterator():
        changed = False

        if session.start_time_old is not None:
            day, time = _local_parts(session.start_time_old)
            session.start_day = day
            session.start_time = time
            changed = True
        if session.end_time_old is not None:
            day, time = _local_parts(session.end_time_old)
            session.end_day = day
            session.end_time = time
            changed = True
        if session.check_in_start_old is not None:
            day, time = _local_parts(session.check_in_start_old)
            session.check_in_start_day = day
            session.check_in_start_time = time
            changed = True
        if session.check_in_end_old is not None:
            day, time = _local_parts(session.check_in_end_old)
            session.check_in_end_day = day
            session.check_in_end_time = time
            changed = True

        if changed:
            session.save(
                update_fields=[
                    "start_day",
                    "start_time",
                    "end_day",
                    "end_time",
                    "check_in_start_day",
                    "check_in_start_time",
                    "check_in_end_day",
                    "check_in_end_time",
                ]
            )


def noop_reverse(apps, schema_editor):
    # Old DateTime columns are dropped; reverse is a no-op (data already migrated).
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("cf_operations", "0009_event_session_model"),
    ]

    operations = [
        # Rename old DateTime fields so we can re-use start_time / end_time names.
        migrations.RenameField(
            model_name="eventsession",
            old_name="start_time",
            new_name="start_time_old",
        ),
        migrations.RenameField(
            model_name="eventsession",
            old_name="end_time",
            new_name="end_time_old",
        ),
        migrations.RenameField(
            model_name="eventsession",
            old_name="check_in_start",
            new_name="check_in_start_old",
        ),
        migrations.RenameField(
            model_name="eventsession",
            old_name="check_in_end",
            new_name="check_in_end_old",
        ),
        # New day + time fields.
        migrations.AddField(
            model_name="eventsession",
            name="start_day",
            field=models.DateField(
                blank=True,
                db_index=True,
                help_text="Calendar day when this session begins.",
                null=True,
                verbose_name="start day",
            ),
        ),
        migrations.AddField(
            model_name="eventsession",
            name="start_time",
            field=models.TimeField(
                blank=True,
                help_text="Clock time when this session begins.",
                null=True,
                verbose_name="start time",
            ),
        ),
        migrations.AddField(
            model_name="eventsession",
            name="end_day",
            field=models.DateField(
                blank=True,
                help_text="Calendar day when this session ends.",
                null=True,
                verbose_name="end day",
            ),
        ),
        migrations.AddField(
            model_name="eventsession",
            name="end_time",
            field=models.TimeField(
                blank=True,
                help_text="Clock time when this session ends.",
                null=True,
                verbose_name="end time",
            ),
        ),
        migrations.AddField(
            model_name="eventsession",
            name="check_in_start_day",
            field=models.DateField(
                blank=True,
                help_text="Optional. Day when check-in / attendance capture opens.",
                null=True,
                verbose_name="check-in start day",
            ),
        ),
        migrations.AddField(
            model_name="eventsession",
            name="check_in_start_time",
            field=models.TimeField(
                blank=True,
                help_text="Optional. Clock time when check-in opens.",
                null=True,
                verbose_name="check-in start time",
            ),
        ),
        migrations.AddField(
            model_name="eventsession",
            name="check_in_end_day",
            field=models.DateField(
                blank=True,
                help_text="Optional. Day when check-in / attendance capture closes.",
                null=True,
                verbose_name="check-in end day",
            ),
        ),
        migrations.AddField(
            model_name="eventsession",
            name="check_in_end_time",
            field=models.TimeField(
                blank=True,
                help_text="Optional. Clock time when check-in closes.",
                null=True,
                verbose_name="check-in end time",
            ),
        ),
        migrations.RunPython(split_session_datetimes, noop_reverse),
        migrations.RemoveField(
            model_name="eventsession",
            name="start_time_old",
        ),
        migrations.RemoveField(
            model_name="eventsession",
            name="end_time_old",
        ),
        migrations.RemoveField(
            model_name="eventsession",
            name="check_in_start_old",
        ),
        migrations.RemoveField(
            model_name="eventsession",
            name="check_in_end_old",
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
