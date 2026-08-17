# cf-dev/cf_src/appsinn/cf_users/permissions.py

"""Organisation-group permission helpers."""

from __future__ import annotations

from django.apps import apps
from django.contrib.auth.models import Permission
from django.db.models import Q


def seed_default_organization_groups(organization) -> list:
    """
    Create standard groups for a new organisation if missing.

    Returns the list of groups that were created (empty when already seeded).
    """
    OrganizationGroup = apps.get_model("cf_users", "OrganizationGroup")
    specs = [
        {
            "name": "Members",
            "description": "Default group for organisation members (viewer).",
            "is_default": True,
            "permission_codenames": (),
        },
        {
            "name": "Branch Managers",
            "description": "Manage branch-level records (people, events, attendance).",
            "is_default": False,
            "permission_codenames": (
                "view_member",
                "add_member",
                "change_member",
                "view_event",
                "add_event",
                "change_event",
                "view_attendancerecord",
                "add_attendancerecord",
                "change_attendancerecord",
                "view_zone",
                "view_subbranch",
            ),
        },
        {
            "name": "Organisation Admins",
            "description": "Full organisation administration privileges.",
            "is_default": False,
            "permission_codenames": (
                "view_member",
                "add_member",
                "change_member",
                "delete_member",
                "view_event",
                "add_event",
                "change_event",
                "delete_event",
                "view_attendancerecord",
                "add_attendancerecord",
                "change_attendancerecord",
                "delete_attendancerecord",
                "view_organization",
                "change_organization",
                "view_branch",
                "add_branch",
                "change_branch",
                "view_organizationgroup",
                "add_organizationgroup",
                "change_organizationgroup",
                "view_organizationgroupmembership",
                "add_organizationgroupmembership",
                "change_organizationgroupmembership",
            ),
        },
    ]
    created = []
    for spec in specs:
        group, was_created = OrganizationGroup.objects.get_or_create(
            organization=organization,
            name=spec["name"],
            defaults={
                "description": spec["description"],
                "is_default": spec["is_default"],
                "is_active": True,
            },
        )
        if was_created:
            created.append(group)
        if spec["permission_codenames"]:
            perms = Permission.objects.filter(
                codename__in=spec["permission_codenames"]
            )
            group.permissions.add(*perms)
    return created


def user_org_permission_q(user) -> Q:
    """Q filter for Permission rows granted via organisation groups."""
    return Q(
        organization_groups__memberships__user=user,
        organization_groups__is_active=True,
    )


def user_has_org_perm(user, perm: str, *, organization=None) -> bool:
    """
    True if ``user`` holds ``perm`` (``app_label.codename``) via an active
    organisation group. Optionally restrict to one organisation.
    """
    if not user or not getattr(user, "is_authenticated", False) or not user.is_active:
        return False
    if user.is_superuser:
        return True
    try:
        app_label, codename = perm.split(".", 1)
    except ValueError:
        return False
    qs = Permission.objects.filter(
        content_type__app_label=app_label,
        codename=codename,
        organization_groups__memberships__user=user,
        organization_groups__is_active=True,
    )
    if organization is not None:
        org_id = getattr(organization, "pk", organization)
        qs = qs.filter(organization_groups__organization_id=org_id)
    return qs.exists()
