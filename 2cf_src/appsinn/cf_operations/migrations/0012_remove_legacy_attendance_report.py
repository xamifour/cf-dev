# Remove legacy AttendanceReport model, report FK, and report-linked rows.

from django.db import migrations


def purge_legacy_report_rows(apps, schema_editor):
    """Drop stored report headers and any attendance rows that belonged to them."""
    AttendanceRecord = apps.get_model("cf_operations", "AttendanceRecord")
    AttendanceReport = apps.get_model("cf_operations", "AttendanceReport")
    # Week stats cascade from records.
    AttendanceRecord.objects.exclude(report_id=None).delete()
    AttendanceReport.objects.all().delete()


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("cf_operations", "0011_eventsession_weekday_schedule"),
    ]

    operations = [
        migrations.RunPython(purge_legacy_report_rows, noop_reverse),
        migrations.RemoveField(
            model_name="attendancerecord",
            name="report",
        ),
        migrations.DeleteModel(
            name="AttendanceReport",
        ),
    ]
