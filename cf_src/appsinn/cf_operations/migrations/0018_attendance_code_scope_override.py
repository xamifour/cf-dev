# code field help text + fill_from_scope includes code

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cf_operations", "0017_attendance_phone_fill_from_scope"),
    ]

    operations = [
        migrations.AlterField(
            model_name="attendancerecord",
            name="code",
            field=models.CharField(
                blank=True,
                default="",
                help_text=(
                    "Override. Leave blank to use code from sub group / zone / "
                    "branch / organisation (most specific linked scope). "
                    "Tick “fill from scope” to store that code here."
                ),
                max_length=64,
                verbose_name="code",
            ),
        ),
        migrations.AlterField(
            model_name="attendancerecord",
            name="fill_from_scope",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "When ticked, code, centre name, leader, address, phone "
                    "number and location provider are filled from the linked "
                    "scope on save: sub group if set, else zone, else branch, "
                    "else organisation."
                ),
                verbose_name="fill from scope",
            ),
        ),
    ]
