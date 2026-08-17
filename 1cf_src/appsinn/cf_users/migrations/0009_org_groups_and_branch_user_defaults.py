# Organisation groups, memberships; OrganisationUser defaults; seed groups.

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


def seed_groups_for_existing_orgs(apps, schema_editor):
    Organization = apps.get_model("cf_users", "Organization")
    OrganizationGroup = apps.get_model("cf_users", "OrganizationGroup")
    for org in Organization.objects.all().iterator():
        for name, is_default, desc in (
            ("Members", True, "Default group for organisation members (viewer)."),
            (
                "Branch Managers",
                False,
                "Manage branch-level records (people, events, attendance).",
            ),
            (
                "Organisation Admins",
                False,
                "Full organisation administration privileges.",
            ),
        ):
            OrganizationGroup.objects.get_or_create(
                organization=org,
                name=name,
                defaults={
                    "description": desc,
                    "is_default": is_default,
                    "is_active": True,
                },
            )


def backfill_org_users_from_branch_users(apps, schema_editor):
    BranchUser = apps.get_model("cf_users", "BranchUser")
    OrganizationUser = apps.get_model("cf_users", "OrganizationUser")
    OrganizationGroup = apps.get_model("cf_users", "OrganizationGroup")
    OrganizationGroupMembership = apps.get_model(
        "cf_users", "OrganizationGroupMembership"
    )
    for bu in BranchUser.objects.select_related("branch").iterator():
        org_id = bu.branch.organization_id
        if not org_id:
            continue
        if not OrganizationUser.objects.filter(
            user_id=bu.user_id, organization_id=org_id
        ).exists():
            OrganizationUser.objects.create(
                user_id=bu.user_id,
                organization_id=org_id,
                role="VIEWER",
                is_org_manager=False,
                is_admin=False,
            )
        for group in OrganizationGroup.objects.filter(
            organization_id=org_id, is_default=True, is_active=True
        ):
            OrganizationGroupMembership.objects.get_or_create(
                group=group, user_id=bu.user_id
            )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("cf_users", "0008_alter_branch_options_alter_organization_options_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="organizationuser",
            name="is_org_manager",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Grants administrative access across this organisation's branches."
                ),
                verbose_name="is manager",
            ),
        ),
        migrations.AlterField(
            model_name="organizationuser",
            name="role",
            field=models.CharField(
                choices=[
                    ("VIEWER", "Viewer / Member"),
                    ("AUDITOR", "Denomination Auditor"),
                    ("OVERSEER", "Regional Overseer / Bishop"),
                    ("ADMIN", "HQ Administrator"),
                ],
                default="VIEWER",
                max_length=20,
                verbose_name="role",
            ),
        ),
        migrations.CreateModel(
            name="OrganizationGroup",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, db_index=True, verbose_name="created at"
                    ),
                ),
                (
                    "modified_at",
                    models.DateTimeField(auto_now=True, verbose_name="modified at"),
                ),
                ("name", models.CharField(max_length=150, verbose_name="name")),
                (
                    "description",
                    models.TextField(blank=True, verbose_name="description"),
                ),
                (
                    "is_default",
                    models.BooleanField(
                        default=False,
                        help_text=(
                            "When enabled, users who join a branch of this "
                            "organisation are added to this group automatically."
                        ),
                        verbose_name="default for new members",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        db_index=True, default=True, verbose_name="is active"
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(app_label)s_%(class)s_created",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="created by",
                    ),
                ),
                (
                    "modified_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(app_label)s_%(class)s_modified",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="modified by",
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="permission_groups",
                        to="cf_users.organization",
                        verbose_name="organisation",
                    ),
                ),
                (
                    "permissions",
                    models.ManyToManyField(
                        blank=True,
                        help_text=(
                            "Privileges granted to members of this group within "
                            "the organisation."
                        ),
                        related_name="organization_groups",
                        to="auth.permission",
                        verbose_name="permissions",
                    ),
                ),
            ],
            options={
                "verbose_name": "organisation group",
                "verbose_name_plural": "organisation groups",
                "ordering": ("-modified_at", "name"),
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="OrganizationGroupMembership",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, db_index=True, verbose_name="created at"
                    ),
                ),
                (
                    "modified_at",
                    models.DateTimeField(auto_now=True, verbose_name="modified at"),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(app_label)s_%(class)s_created",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="created by",
                    ),
                ),
                (
                    "group",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="memberships",
                        to="cf_users.organizationgroup",
                        verbose_name="group",
                    ),
                ),
                (
                    "modified_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(app_label)s_%(class)s_modified",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="modified by",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="organization_group_memberships",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="user",
                    ),
                ),
            ],
            options={
                "verbose_name": "organisation group membership",
                "verbose_name_plural": "organisation group memberships",
                "ordering": ("-modified_at",),
                "abstract": False,
            },
        ),
        migrations.AddIndex(
            model_name="organizationgroup",
            index=models.Index(
                fields=["organization", "is_default", "is_active"],
                name="cf_users_or_organiz_def_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="organizationgroup",
            constraint=models.UniqueConstraint(
                fields=("organization", "name"),
                name="cf_users_organizationgroup_unique_org_group_name",
            ),
        ),
        migrations.AddConstraint(
            model_name="organizationgroupmembership",
            constraint=models.UniqueConstraint(
                fields=("group", "user"),
                name="cf_users_organizationgroupmembership_unique_group_user",
            ),
        ),
        migrations.RunPython(seed_groups_for_existing_orgs, noop),
        migrations.RunPython(backfill_org_users_from_branch_users, noop),
    ]
