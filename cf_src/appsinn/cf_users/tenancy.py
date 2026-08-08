# cf-dev/cf_src/appsinn/cf_users/tenancy.py

"""
Active tenant context and scale-safe membership checks.

Uses SQL EXISTS / subqueries instead of materialising millions of UUID lists.
Active organisation and branch are stored in the session and mirrored on the
request + contextvars for managers/querysets.
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any
from uuid import UUID

from django.apps import apps
from django.core.exceptions import PermissionDenied
from django.db.models import Exists, OuterRef, Q, QuerySet

SESSION_ORG_KEY = "cf_active_organization_id"
SESSION_BRANCH_KEY = "cf_active_branch_id"

_active_organization_id: ContextVar[str | None] = ContextVar(
    "cf_active_organization_id", default=None
)
_active_branch_id: ContextVar[str | None] = ContextVar(
    "cf_active_branch_id", default=None
)


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def set_active_tenant_ids(
    organization_id: Any = None, branch_id: Any = None
) -> None:
    """Set contextvars used by managers outside the request object."""
    _active_organization_id.set(_as_str(organization_id))
    _active_branch_id.set(_as_str(branch_id))


def clear_active_tenant_ids() -> None:
    _active_organization_id.set(None)
    _active_branch_id.set(None)


def get_active_organization_id() -> str | None:
    return _active_organization_id.get()


def get_active_branch_id() -> str | None:
    return _active_branch_id.get()


def managed_organization_ids_qs(user) -> QuerySet:
    """Subquery of organisation PKs this user manages (not materialised)."""
    OrganizationUser = apps.get_model("cf_users", "OrganizationUser")
    return (
        OrganizationUser.objects.filter(user_id=user.pk, is_org_manager=True)
        .values("organization_id")
        .distinct()
    )


def accessible_branch_ids_qs(user) -> QuerySet:
    """
    Subquery of branch PKs the user may access:
    - explicit BranchUser membership, or
    - any branch under a managed organisation.
    """
    Branch = apps.get_model("cf_users", "Branch")
    return (
        Branch.objects.filter(
            Q(user_roles__user_id=user.pk)
            | Q(organization_id__in=managed_organization_ids_qs(user))
        )
        .values("id")
        .distinct()
    )


def user_manages_organization(user, organization_id) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser:
        return True
    OrganizationUser = apps.get_model("cf_users", "OrganizationUser")
    return OrganizationUser.objects.filter(
        user_id=user.pk,
        organization_id=organization_id,
        is_org_manager=True,
    ).exists()


def user_is_org_member(user, organization_id) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser:
        return True
    OrganizationUser = apps.get_model("cf_users", "OrganizationUser")
    return OrganizationUser.objects.filter(
        user_id=user.pk, organization_id=organization_id
    ).exists()


def user_can_access_branch(user, branch_id) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser:
        return True
    Branch = apps.get_model("cf_users", "Branch")
    BranchUser = apps.get_model("cf_users", "BranchUser")
    if BranchUser.objects.filter(user_id=user.pk, branch_id=branch_id).exists():
        return True
    return Branch.objects.filter(
        pk=branch_id,
        organization_id__in=managed_organization_ids_qs(user),
    ).exists()


def user_can_access_organization(user, organization_id) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser:
        return True
    if user_is_org_member(user, organization_id):
        return True
    # Branch-only members can access the org that owns their branch.
    BranchUser = apps.get_model("cf_users", "BranchUser")
    return BranchUser.objects.filter(
        user_id=user.pk, branch__organization_id=organization_id
    ).exists()


def users_visible_to_user_qs(user) -> QuerySet:
    """
    Users visible in admin pickers / lists for ``user``.

    Includes:
    - the user themselves
    - users who share an organisation membership (any role, not only managers)
    - users who share an accessible branch membership

    Superusers see all accounts. Uses subqueries (scale-safe).
    """
    from django.contrib.auth import get_user_model  # noqa: PLC0415

    UserModel = get_user_model()
    if not user or not getattr(user, "is_authenticated", False):
        return UserModel.objects.none()
    if user.is_superuser:
        return UserModel.objects.all()

    OrganizationUser = apps.get_model("cf_users", "OrganizationUser")
    BranchUser = apps.get_model("cf_users", "BranchUser")

    org_ids = organizations_for_user_qs(user).values("id")
    branch_ids = accessible_branch_ids_qs(user)

    peer_org = OrganizationUser.objects.filter(
        organization_id__in=org_ids
    ).values("user_id")
    peer_branch = BranchUser.objects.filter(branch_id__in=branch_ids).values(
        "user_id"
    )
    return UserModel.objects.filter(
        Q(pk__in=peer_org) | Q(pk__in=peer_branch) | Q(pk=user.pk)
    ).exclude(is_superuser=True)


def organizations_for_user_qs(user) -> QuerySet:
    """Organisations the user can switch into (membership or superuser all)."""
    Organization = apps.get_model("cf_users", "Organization")
    if not user or not getattr(user, "is_authenticated", False):
        return Organization.objects.none()
    if user.is_superuser:
        return Organization.objects.filter(is_active=True).order_by("name")
    OrganizationUser = apps.get_model("cf_users", "OrganizationUser")
    BranchUser = apps.get_model("cf_users", "BranchUser")
    return (
        Organization.objects.filter(is_active=True)
        .filter(
            Q(Exists(OrganizationUser.objects.filter(
                user_id=user.pk, organization_id=OuterRef("pk")
            )))
            | Q(Exists(BranchUser.objects.filter(
                user_id=user.pk, branch__organization_id=OuterRef("pk")
            )))
        )
        .order_by("name")
        .distinct()
    )


def branches_for_user_qs(user, organization_id=None) -> QuerySet:
    """Branches the user can switch into, optionally limited to one organisation."""
    Branch = apps.get_model("cf_users", "Branch")
    if not user or not getattr(user, "is_authenticated", False):
        return Branch.objects.none()
    qs = Branch.objects.filter(active=True)
    if organization_id:
        qs = qs.filter(organization_id=organization_id)
    if user.is_superuser:
        return qs.select_related("organization").order_by("name")
    return (
        qs.filter(id__in=accessible_branch_ids_qs(user))
        .select_related("organization")
        .order_by("name")
        .distinct()
    )


def resolve_default_organization(user):
    """Pick a single default organisation without loading all IDs."""
    return organizations_for_user_qs(user).first()


def resolve_default_branch(user, organization=None):
    """Prefer default branch of active org, else first accessible branch."""
    org_id = getattr(organization, "pk", organization)
    qs = branches_for_user_qs(user, organization_id=org_id)
    if org_id:
        default = qs.filter(is_default=True).first()
        if default:
            return default
    return qs.first()


def set_session_tenant(request, organization=None, branch=None) -> None:
    """Persist and activate tenant context for this request/session."""
    org_id = getattr(organization, "pk", organization)
    branch_id = getattr(branch, "pk", branch)

    if org_id:
        request.session[SESSION_ORG_KEY] = str(org_id)
    else:
        request.session.pop(SESSION_ORG_KEY, None)

    if branch_id:
        request.session[SESSION_BRANCH_KEY] = str(branch_id)
    else:
        request.session.pop(SESSION_BRANCH_KEY, None)

    set_active_tenant_ids(org_id, branch_id)
    request.organization = organization
    request.branch = branch


def switch_organization(request, organization_id) -> Any:
    """Validate and switch active organisation; reset branch to org default."""
    user = request.user
    Organization = apps.get_model("cf_users", "Organization")
    try:
        org = Organization.objects.get(pk=organization_id, is_active=True)
    except (Organization.DoesNotExist, ValueError, TypeError) as exc:
        raise PermissionDenied("Invalid organisation.") from exc
    if not user_can_access_organization(user, org.pk):
        raise PermissionDenied("You do not have access to this organisation.")
    branch = resolve_default_branch(user, org)
    if branch and not user_can_access_branch(user, branch.pk):
        branch = None
    set_session_tenant(request, organization=org, branch=branch)
    return org


def switch_branch(request, branch_id) -> Any:
    """Validate and switch active branch (and its organisation)."""
    user = request.user
    Branch = apps.get_model("cf_users", "Branch")
    try:
        branch = Branch.objects.select_related("organization").get(
            pk=branch_id, active=True
        )
    except (Branch.DoesNotExist, ValueError, TypeError) as exc:
        raise PermissionDenied("Invalid branch.") from exc
    if not user_can_access_branch(user, branch.pk):
        raise PermissionDenied("You do not have access to this branch.")
    set_session_tenant(request, organization=branch.organization, branch=branch)
    return branch


def bind_tenant_from_session(request) -> None:
    """
    Load session tenant onto request + contextvars.

    Invalid or unauthorised session values are repaired to a safe default.
    Superusers may operate without a tenant only when none can be resolved.
    """
    user = request.user
    request.organization = None
    request.branch = None
    clear_active_tenant_ids()

    if not getattr(user, "is_authenticated", False):
        return

    Organization = apps.get_model("cf_users", "Organization")
    Branch = apps.get_model("cf_users", "Branch")

    org = None
    branch = None
    raw_org = request.session.get(SESSION_ORG_KEY)
    raw_branch = request.session.get(SESSION_BRANCH_KEY)

    if raw_org:
        try:
            org = Organization.objects.filter(pk=raw_org, is_active=True).first()
            if org and not user_can_access_organization(user, org.pk):
                org = None
        except (ValueError, TypeError):
            org = None

    if raw_branch:
        try:
            branch = (
                Branch.objects.select_related("organization")
                .filter(pk=raw_branch, active=True)
                .first()
            )
            if branch and not user_can_access_branch(user, branch.pk):
                branch = None
            elif branch and org and branch.organization_id != org.pk:
                # Branch must belong to active organisation when both are set.
                branch = None
            elif branch and not org:
                org = branch.organization
        except (ValueError, TypeError):
            branch = None

    if org is None:
        org = resolve_default_organization(user)
    if branch is None and org is not None:
        branch = resolve_default_branch(user, org)
    elif branch is None:
        branch = resolve_default_branch(user)

    if org or branch:
        set_session_tenant(request, organization=org, branch=branch)
    else:
        set_active_tenant_ids(None, None)
