# Member number unique per organisation; denormalised organization FK.

import django.db.models.deletion
from django.db import migrations, models


def backfill_member_organization(apps, schema_editor):
    Member = apps.get_model("cf_people", "Member")
    for member in Member.objects.select_related("branch").iterator():
        if member.branch_id and member.branch.organization_id:
            Member.objects.filter(pk=member.pk).update(
                organization_id=member.branch.organization_id
            )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("cf_people", "0009_alter_department_options_alter_family_options_and_more"),
        ("cf_users", "0008_alter_branch_options_alter_organization_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="member",
            name="organization",
            field=models.ForeignKey(
                help_text="Denormalised from branch for org-scoped member numbers.",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="members",
                to="cf_users.organization",
                verbose_name="organisation",
            ),
        ),
        migrations.RunPython(backfill_member_organization, noop),
        migrations.AlterField(
            model_name="member",
            name="organization",
            field=models.ForeignKey(
                help_text="Denormalised from branch for org-scoped member numbers.",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="members",
                to="cf_users.organization",
                verbose_name="organisation",
            ),
        ),
        migrations.AlterField(
            model_name="member",
            name="member_number",
            field=models.CharField(
                blank=True,
                help_text="Unique within the organisation (auto-generated if blank).",
                max_length=50,
                verbose_name="member number",
            ),
        ),
        migrations.AddConstraint(
            model_name="member",
            constraint=models.UniqueConstraint(
                fields=("organization", "member_number"),
                name="cf_people_member_unique_org_member_number",
            ),
        ),
        migrations.AddIndex(
            model_name="member",
            index=models.Index(
                fields=["organization", "member_number"],
                name="cf_people_m_organiz_member_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="member",
            index=models.Index(
                fields=["branch", "membership_status"],
                name="cf_people_m_branch_status_idx",
            ),
        ),
    ]
