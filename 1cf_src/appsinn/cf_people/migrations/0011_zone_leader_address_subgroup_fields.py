# Zone coordinator→leader + address; Sub group code/address/location_provider

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cf_people", "0010_member_org_scoped_number"),
    ]

    operations = [
        migrations.AddField(
            model_name="zone",
            name="address",
            field=models.CharField(
                blank=True,
                help_text="Optional street / area address for this zone.",
                max_length=512,
                verbose_name="address",
            ),
        ),
        migrations.RenameField(
            model_name="zone",
            old_name="coordinator",
            new_name="leader",
        ),
        migrations.AlterField(
            model_name="zone",
            name="leader",
            field=models.ForeignKey(
                blank=True,
                help_text="Optional. Zone leader (member).",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="led_zones",
                to="cf_people.member",
                verbose_name="leader",
            ),
        ),
        migrations.AddField(
            model_name="subbranch",
            name="code",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text=(
                    "Optional short code for this sub group "
                    "(unique within the zone)."
                ),
                max_length=32,
                null=True,
                verbose_name="code",
            ),
        ),
        migrations.AddField(
            model_name="subbranch",
            name="address",
            field=models.CharField(
                blank=True,
                help_text="Optional street / meeting address for this sub group.",
                max_length=512,
                verbose_name="address",
            ),
        ),
        migrations.AddField(
            model_name="subbranch",
            name="location_provider",
            field=models.CharField(
                blank=True,
                help_text=(
                    "Optional. Who provides or hosts this sub group's location."
                ),
                max_length=255,
                verbose_name="location provider",
            ),
        ),
        migrations.AddConstraint(
            model_name="subbranch",
            constraint=models.UniqueConstraint(
                condition=models.Q(
                    ("code__isnull", False), models.Q(("code", ""), _negated=True)
                ),
                fields=("zone", "code"),
                name="cf_people_subbranch_unique_zone_code",
            ),
        ),
    ]
