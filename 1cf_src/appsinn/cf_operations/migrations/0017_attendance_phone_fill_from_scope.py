# phone_number + fill_from_scope on AttendanceRecord

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cf_operations", "0016_attendance_code_leader_address"),
    ]

    operations = [
        migrations.AddField(
            model_name="attendancerecord",
            name="phone_number",
            field=models.CharField(
                blank=True,
                help_text=(
                    "Override. Leave blank to use the scope leader’s phone number. "
                    "Tick “fill from scope” to store it here."
                ),
                max_length=64,
                verbose_name="phone number",
            ),
        ),
        migrations.AddField(
            model_name="attendancerecord",
            name="fill_from_scope",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "When ticked, centre name, leader, address, phone number and "
                    "location provider are filled from the linked scope on save: "
                    "sub group if set, else zone, else branch, else organisation."
                ),
                verbose_name="fill from scope",
            ),
        ),
        migrations.AlterField(
            model_name="attendancerecord",
            name="centre_name",
            field=models.CharField(
                blank=True,
                help_text=(
                    "Override. Leave blank to use name from sub group / zone / "
                    "branch / organisation (most specific linked scope). "
                    "Tick “fill from scope” to store that name here."
                ),
                max_length=255,
                verbose_name="centre name",
            ),
        ),
        migrations.AlterField(
            model_name="attendancerecord",
            name="leader",
            field=models.CharField(
                blank=True,
                help_text=(
                    "Override. Leave blank to use leader from sub group / zone / "
                    "branch / organisation. Tick “fill from scope” to store that "
                    "name here."
                ),
                max_length=255,
                verbose_name="leader",
            ),
        ),
        migrations.AlterField(
            model_name="attendancerecord",
            name="address",
            field=models.CharField(
                blank=True,
                help_text=(
                    "Override. Leave blank to use address from sub group / zone / "
                    "branch / organisation. Tick “fill from scope” to store that "
                    "address here."
                ),
                max_length=512,
                verbose_name="address",
            ),
        ),
        migrations.AlterField(
            model_name="attendancerecord",
            name="location_provider",
            field=models.CharField(
                blank=True,
                help_text=(
                    "Override. Leave blank to use the sub group’s location "
                    "provider when a sub group is linked. Tick “fill from scope” "
                    "to store it here."
                ),
                max_length=255,
                verbose_name="location provider",
            ),
        ),
    ]
