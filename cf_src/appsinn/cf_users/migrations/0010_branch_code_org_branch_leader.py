# Branch.code; Organization.leader + Branch.leader → Member

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cf_people", "0010_member_org_scoped_number"),
        ("cf_users", "0009_org_groups_and_branch_user_defaults"),
    ]

    operations = [
        migrations.AddField(
            model_name="branch",
            name="code",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text=(
                    "Optional short code for this branch "
                    "(unique within the organisation)."
                ),
                max_length=32,
                null=True,
                verbose_name="code",
            ),
        ),
        migrations.AddField(
            model_name="organization",
            name="leader",
            field=models.ForeignKey(
                blank=True,
                help_text="Optional. Organisation-level leader (member).",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="led_organizations",
                to="cf_people.member",
                verbose_name="leader",
            ),
        ),
        migrations.AddField(
            model_name="branch",
            name="leader",
            field=models.ForeignKey(
                blank=True,
                help_text="Optional. Branch leader (member).",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="led_branches",
                to="cf_people.member",
                verbose_name="leader",
            ),
        ),
        migrations.AddConstraint(
            model_name="branch",
            constraint=models.UniqueConstraint(
                condition=models.Q(
                    ("code__isnull", False), models.Q(("code", ""), _negated=True)
                ),
                fields=("organization", "code"),
                name="cf_users_branch_unique_org_code",
            ),
        ),
    ]
