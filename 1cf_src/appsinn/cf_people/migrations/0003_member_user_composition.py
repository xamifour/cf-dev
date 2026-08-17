# cf-dev/cf_src/appsinn/cf_people/migrations/0003_member_user_composition.py

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def forwards_link_users(apps, schema_editor):
    """Ensure every Member has a User; copy identity fields onto User."""
    Member = apps.get_model("cf_people", "Member")
    User = apps.get_model("cf_users", "User")

    for member in Member.objects.all().iterator():
        if member.user_id:
            user = member.user
            # Prefer member names if user names empty.
            updated = []
            if not user.first_name and getattr(member, "first_name", None):
                user.first_name = member.first_name
                updated.append("first_name")
            if not user.last_name and getattr(member, "last_name", None):
                user.last_name = member.last_name
                updated.append("last_name")
            if (
                not user.middle_name
                and getattr(member, "middle_name", None)
            ):
                user.middle_name = member.middle_name
                updated.append("middle_name")
            if updated:
                user.save(update_fields=updated)
            continue

        first = getattr(member, "first_name", None) or "Member"
        last = getattr(member, "last_name", None) or "Unknown"
        middle = getattr(member, "middle_name", None) or ""
        base = f"{first}{last}".lower().replace(" ", "")[:40] or "member"
        username = f"{base}{uuid.uuid4().hex[:8]}"
        email = f"{username}@members.local"
        phone = f"+23320{uuid.uuid4().int % 10_000_000:07d}"
        while User.objects.filter(phone_number=phone).exists():
            phone = f"+23320{uuid.uuid4().int % 10_000_000:07d}"

        user = User.objects.create(
            username=username[:64],
            email=email,
            first_name=first[:64],
            last_name=last[:64],
            middle_name=(middle[:64] if middle else None),
            phone_number=phone,
            address="—",
            city="—",
            country="—",
            is_active=True,
            password="!",  # unusable marker; auth backend rejects
        )
        # Ensure unusable password semantics for historical model
        user.password = f"!{uuid.uuid4().hex}"
        user.save(update_fields=["password"])
        member.user = user
        member.save(update_fields=["user"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("cf_people", "0002_initial"),
    ]

    operations = [
        migrations.RunPython(forwards_link_users, noop_reverse),
        migrations.AlterField(
            model_name="member",
            name="user",
            field=models.OneToOneField(
                help_text=(
                    "Login / person identity. Required. Use an unusable password for "
                    "directory-only members until they are invited to the portal."
                ),
                on_delete=django.db.models.deletion.PROTECT,
                related_name="member_profile",
                to=settings.AUTH_USER_MODEL,
                verbose_name="user account",
            ),
        ),
        migrations.RemoveField(model_name="member", name="first_name"),
        migrations.RemoveField(model_name="member", name="last_name"),
        migrations.RemoveField(model_name="member", name="middle_name"),
        migrations.AlterModelOptions(
            name="member",
            options={
                "ordering": ("user__last_name", "user__first_name"),
                "verbose_name": "member",
                "verbose_name_plural": "members",
            },
        ),
    ]
