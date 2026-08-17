# Attendance: serial_number→code, leader CharField, location→address, drop contact

from django.db import migrations, models


def copy_serial_and_leader(apps, schema_editor):
    AttendanceRecord = apps.get_model("cf_operations", "AttendanceRecord")
    Member = apps.get_model("cf_people", "Member")
    members = {
        m.pk: m
        for m in Member.objects.select_related("user").all().iterator()
    }
    for rec in AttendanceRecord.objects.all().iterator():
        updates = []
        # serial_number → code text
        sn = getattr(rec, "serial_number", None)
        if sn is not None and not (rec.code or "").strip():
            rec.code = str(sn)
            updates.append("code")
        # leader FK → text name (field still named leader_id until removed)
        leader_id = getattr(rec, "leader_id", None)
        if leader_id and not (getattr(rec, "leader_text", "") or "").strip():
            m = members.get(leader_id)
            if m is not None:
                user = getattr(m, "user", None)
                if user is not None:
                    name = (
                        f"{getattr(user, 'first_name', '')} "
                        f"{getattr(user, 'last_name', '')}"
                    ).strip()
                else:
                    name = str(getattr(m, "member_number", "") or m.pk)
                rec.leader_text = name
                updates.append("leader_text")
        if updates:
            rec.save(update_fields=updates)


class Migration(migrations.Migration):

    dependencies = [
        ("cf_operations", "0015_attendance_month_leader_datetime"),
        ("cf_people", "0010_member_org_scoped_number"),
    ]

    operations = [
        migrations.AddField(
            model_name="attendancerecord",
            name="code",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Optional row / centre code (formerly S/N on the sheet).",
                max_length=64,
                verbose_name="code",
            ),
        ),
        migrations.AddField(
            model_name="attendancerecord",
            name="leader_text",
            field=models.CharField(
                blank=True,
                default="",
                max_length=255,
                verbose_name="leader",
            ),
        ),
        migrations.RunPython(copy_serial_and_leader, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="attendancerecord",
            name="serial_number",
        ),
        migrations.RemoveField(
            model_name="attendancerecord",
            name="leader",
        ),
        migrations.RenameField(
            model_name="attendancerecord",
            old_name="leader_text",
            new_name="leader",
        ),
        migrations.AlterField(
            model_name="attendancerecord",
            name="leader",
            field=models.CharField(
                blank=True,
                help_text="Optional. Cell / centre leader name (as on the sheet).",
                max_length=255,
                verbose_name="leader",
            ),
        ),
        migrations.RenameField(
            model_name="attendancerecord",
            old_name="location",
            new_name="address",
        ),
        migrations.AlterField(
            model_name="attendancerecord",
            name="address",
            field=models.CharField(
                blank=True, max_length=512, verbose_name="address"
            ),
        ),
        migrations.RemoveField(
            model_name="attendancerecord",
            name="contact",
        ),
        migrations.AlterModelOptions(
            name="attendancerecord",
            options={
                "ordering": ("-modified_at", "code", "centre_name"),
                "verbose_name": "attendance record",
                "verbose_name_plural": "attendance records",
            },
        ),
    ]
