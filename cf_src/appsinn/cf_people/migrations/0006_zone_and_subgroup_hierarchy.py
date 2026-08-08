# Organisation → Branch → Zone → Sub group hierarchy

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def forwards_zones_and_subgroups(apps, schema_editor):
    Zone = apps.get_model("cf_people", "Zone")
    SubBranch = apps.get_model("cf_people", "SubBranch")
    Branch = apps.get_model("cf_users", "Branch")

    default_zones = {}
    for branch in Branch.objects.all():
        zone, _ = Zone.objects.get_or_create(
            branch_id=branch.pk,
            name="General Zone",
            defaults={
                "code": "GEN",
                "description": "Default zone created during hierarchy migration.",
                "is_active": True,
            },
        )
        default_zones[str(branch.pk)] = zone

    for sg in SubBranch.objects.all():
        gtype = getattr(sg, "group_type", None) or "CELL"

        if gtype == "ZONE":
            zone, _ = Zone.objects.get_or_create(
                branch_id=sg.branch_id,
                name=sg.name,
                defaults={
                    "description": sg.description or "",
                    "is_active": sg.is_active,
                    "coordinator_id": sg.leader_id,
                },
            )
            sg.zone_id = zone.pk
            sg.group_type = "CELL"
            if (
                SubBranch.objects.filter(zone_id=zone.pk, name=sg.name)
                .exclude(pk=sg.pk)
                .exists()
            ):
                sg.name = f"{sg.name} Cell"
        else:
            zone = default_zones.get(str(sg.branch_id))
            if zone is None:
                zone, _ = Zone.objects.get_or_create(
                    branch_id=sg.branch_id,
                    name="General Zone",
                    defaults={"code": "GEN", "is_active": True},
                )
                default_zones[str(sg.branch_id)] = zone
            sg.zone_id = zone.pk
            if gtype == "SETTLITE":
                sg.group_type = "SATELLITE"
            elif gtype not in ("CELL", "SATELLITE", "SETTLITE"):
                sg.group_type = "CELL"
        sg.save()


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("cf_people", "0005_alter_subbranch_options_remove_subbranch_group_and_more"),
        ("cf_users", "0005_user_gender"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Zone",
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
                    "name",
                    models.CharField(
                        help_text="e.g. ZONE 13, Kasoa West",
                        max_length=255,
                        verbose_name="name",
                    ),
                ),
                (
                    "code",
                    models.CharField(
                        blank=True,
                        help_text="Optional short code, e.g. Z13",
                        max_length=32,
                        verbose_name="code",
                    ),
                ),
                (
                    "description",
                    models.TextField(blank=True, verbose_name="description"),
                ),
                (
                    "is_active",
                    models.BooleanField(default=True, verbose_name="is active"),
                ),
                (
                    "branch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="zones",
                        to="cf_users.branch",
                        verbose_name="branch",
                    ),
                ),
                (
                    "coordinator",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="coordinated_zones",
                        to="cf_people.member",
                        verbose_name="zonal coordinator",
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
            ],
            options={
                "verbose_name": "zone",
                "verbose_name_plural": "zones",
                "ordering": ("branch", "name"),
                "abstract": False,
                "unique_together": {("branch", "name")},
            },
        ),
        migrations.AddField(
            model_name="subbranch",
            name="zone",
            field=models.ForeignKey(
                blank=True,
                help_text=(
                    "Sub groups (cells / satellites) belong to a zone under the branch."
                ),
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="sub_groups",
                to="cf_people.zone",
                verbose_name="zone",
            ),
        ),
        migrations.AlterField(
            model_name="subbranch",
            name="group_type",
            field=models.CharField(
                choices=[
                    ("CELL", "Cell Group"),
                    ("SATELLITE", "Satellite Fellowship"),
                    ("SETTLITE", "Satellite Fellowship (legacy)"),
                ],
                db_index=True,
                default="CELL",
                max_length=20,
                verbose_name="group type",
            ),
        ),
        migrations.RunPython(forwards_zones_and_subgroups, noop_reverse),
        migrations.AlterField(
            model_name="subbranch",
            name="zone",
            field=models.ForeignKey(
                help_text=(
                    "Sub groups (cells / satellites) belong to a zone under the branch."
                ),
                on_delete=django.db.models.deletion.PROTECT,
                related_name="sub_groups",
                to="cf_people.zone",
                verbose_name="zone",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="subbranch",
            unique_together={("zone", "name")},
        ),
        migrations.AlterModelOptions(
            name="subbranch",
            options={
                "ordering": ("zone", "name"),
                "verbose_name": "sub group",
                "verbose_name_plural": "sub groups",
            },
        ),
    ]
