# cf-dev/cf_src/appsinn/cf_users/managers.py

"""Tenant-aware managers using SQL subqueries (scale-safe)."""

from __future__ import annotations

from django.db import models
from django.db.models import Exists, OuterRef, Q


class TenantQuerySet(models.QuerySet):
    """
    QuerySet that scopes results to a user's accessible organisations/branches.

    Prefer active request tenant (contextvars) when set, so hot paths filter by
    a single org/branch id instead of huge IN lists.
    """

    tenant_parent_field: str | None = None

    def for_user(self, user) -> models.QuerySet:
        """Return rows visible to ``user`` under multitenant rules."""
        if user is None or not getattr(user, "is_authenticated", False):
            return self.none()

        from . import tenancy  # noqa: PLC0415

        active_branch_id = tenancy.get_active_branch_id()
        active_org_id = tenancy.get_active_organization_id()

        # Superuser: full access to every row (no tenant narrowing).
        if getattr(user, "is_superuser", False):
            return self

        model_name = self.model._meta.model_name

        if model_name == "user":
            return self._for_user_admin(user)

        if model_name == "organization":
            return self.filter(
                Exists(
                    _org_user_membership_qs(user, OuterRef("pk"))
                )
                | Exists(
                    _branch_user_for_org_qs(user, OuterRef("pk"))
                )
            )

        if model_name in {"organizationuser", "organizationowner"}:
            return self.filter(
                organization_id__in=tenancy.managed_organization_ids_qs(user)
            )

        if model_name == "branch":
            qs = self.filter(id__in=tenancy.accessible_branch_ids_qs(user))
            if active_org_id:
                qs = qs.filter(organization_id=active_org_id)
            return qs

        if model_name == "branchuser":
            return self.filter(branch_id__in=tenancy.accessible_branch_ids_qs(user))

        # Prefer active branch when present and authorised.
        if self._has_field("branch") and active_branch_id:
            if tenancy.user_can_access_branch(user, active_branch_id):
                return self.filter(branch_id=active_branch_id)

        if self._has_field("branch"):
            return self.filter(branch_id__in=tenancy.accessible_branch_ids_qs(user))

        if self._has_field("organization") and active_org_id:
            if tenancy.user_can_access_organization(user, active_org_id):
                return self.filter(organization_id=active_org_id)

        if self._has_field("organization"):
            # Any org the user belongs to (not only managed) — needed for
            # organisation groups and membership records.
            return self.filter(
                organization_id__in=tenancy.organizations_for_user_qs(user).values("id")
            )

        parent = self.tenant_parent_field
        if parent:
            return self._filter_via_parent(user, parent, active_branch_id, active_org_id)

        return self.none()

    def visible_to(self, user=None) -> models.QuerySet:
        """
        Platform viewing scope for content with optional public visibility.

        - Models without a ``visibility`` field: same as ``for_user``.
        - PUBLIC: any authenticated platform user (and anonymous browsers).
        - ORGANIZATION: users who can access any branch of the content's org.
        - BRANCH: users who can access that specific branch only.

        Use for portal/explore feeds. Staff admin continues to use ``for_user``
        so editors only manage their tenant's rows.
        """
        if not self._has_field("visibility"):
            if user is None or not getattr(user, "is_authenticated", False):
                return self.none()
            return self.for_user(user)

        public_value = getattr(self.model, "VISIBILITY_PUBLIC", "PUBLIC")
        org_value = getattr(self.model, "VISIBILITY_ORGANIZATION", "ORGANIZATION")
        branch_value = getattr(self.model, "VISIBILITY_BRANCH", "BRANCH")
        public_q = Q(visibility=public_value)

        if user is None or not getattr(user, "is_authenticated", False):
            return self.filter(public_q)

        if getattr(user, "is_superuser", False):
            return self

        from . import tenancy  # noqa: PLC0415

        if self._has_field("branch"):
            accessible_branches = tenancy.accessible_branch_ids_qs(user)
            # Orgs the user can see (managed + orgs of accessible branches).
            accessible_orgs = tenancy.managed_organization_ids_qs(user)
            return self.filter(
                public_q
                | Q(visibility=branch_value, branch_id__in=accessible_branches)
                | Q(
                    visibility=org_value,
                    branch__organization_id__in=accessible_orgs,
                )
                | Q(
                    visibility=org_value,
                    branch_id__in=accessible_branches,
                )
            )

        if self._has_field("organization"):
            return self.filter(
                public_q
                | Q(organization_id__in=tenancy.managed_organization_ids_qs(user))
            )

        parent = self.tenant_parent_field
        if parent:
            accessible_branches = tenancy.accessible_branch_ids_qs(user)
            return self.filter(
                public_q
                | Q(
                    **{
                        f"{parent}__branch_id__in": accessible_branches,
                        "visibility": branch_value,
                    }
                )
                | Q(
                    **{
                        f"{parent}__branch_id__in": accessible_branches,
                        "visibility": org_value,
                    }
                )
            )

        return self.filter(public_q)

    def for_active_tenant(self, user=None) -> models.QuerySet:
        """
        Strict scope to the active branch/org only.

        Use for portal list/detail when a tenant context is required.
        """
        from . import tenancy  # noqa: PLC0415

        branch_id = tenancy.get_active_branch_id()
        org_id = tenancy.get_active_organization_id()

        if user is not None and not getattr(user, "is_superuser", False):
            if branch_id and not tenancy.user_can_access_branch(user, branch_id):
                return self.none()
            if org_id and not tenancy.user_can_access_organization(user, org_id):
                return self.none()

        if self._has_field("branch") and branch_id:
            return self.filter(branch_id=branch_id)
        if self._has_field("organization") and org_id:
            return self.filter(organization_id=org_id)
        if self._has_field("branch") and org_id:
            return self.filter(branch__organization_id=org_id)
        parent = self.tenant_parent_field
        if parent and branch_id:
            return self.filter(**{f"{parent}__branch_id": branch_id})
        if parent and org_id:
            return self.filter(**{f"{parent}__branch__organization_id": org_id})
        return self.none() if user and not user.is_superuser else self

    def for_branch(self, branch) -> models.QuerySet:
        branch_id = getattr(branch, "pk", branch)
        if self._has_field("branch"):
            return self.filter(branch_id=branch_id)
        parent = self.tenant_parent_field
        if parent:
            return self.filter(**{f"{parent}__branch_id": branch_id})
        return self.none()

    def for_organization(self, organization) -> models.QuerySet:
        org_id = getattr(organization, "pk", organization)
        if self._has_field("organization"):
            return self.filter(organization_id=org_id)
        if self._has_field("branch"):
            return self.filter(branch__organization_id=org_id)
        parent = self.tenant_parent_field
        if parent:
            return self.filter(**{f"{parent}__branch__organization_id": org_id})
        return self.none()

    def _for_superuser(self, active_branch_id, active_org_id) -> models.QuerySet:
        if self._has_field("branch") and active_branch_id:
            return self.filter(branch_id=active_branch_id)
        if self._has_field("organization") and active_org_id:
            return self.filter(organization_id=active_org_id)
        if self._has_field("branch") and active_org_id:
            return self.filter(branch__organization_id=active_org_id)
        if self.model._meta.model_name == "branch" and active_org_id:
            return self.filter(organization_id=active_org_id)
        if self.model._meta.model_name == "organization" and active_org_id:
            return self.filter(pk=active_org_id)
        return self

    def _has_field(self, name: str) -> bool:
        try:
            self.model._meta.get_field(name)
            return True
        except Exception:
            return False

    def _filter_via_parent(
        self, user, parent: str, active_branch_id, active_org_id
    ) -> models.QuerySet:
        from . import tenancy  # noqa: PLC0415

        try:
            parent_field = self.model._meta.get_field(parent)
            parent_model = parent_field.remote_field.model
        except Exception:
            return self.none()

        if self._parent_has_field(parent_model, "branch"):
            if active_branch_id and tenancy.user_can_access_branch(user, active_branch_id):
                return self.filter(**{f"{parent}__branch_id": active_branch_id})
            return self.filter(
                **{f"{parent}__branch_id__in": tenancy.accessible_branch_ids_qs(user)}
            )
        if self._parent_has_field(parent_model, "organization"):
            if active_org_id and tenancy.user_can_access_organization(user, active_org_id):
                return self.filter(**{f"{parent}__organization_id": active_org_id})
            return self.filter(
                **{
                    f"{parent}__organization_id__in": tenancy.managed_organization_ids_qs(
                        user
                    )
                }
            )
        return self.none()

    @staticmethod
    def _parent_has_field(model, name: str) -> bool:
        try:
            model._meta.get_field(name)
            return True
        except Exception:
            return False

    def _for_user_admin(self, user) -> models.QuerySet:
        from . import tenancy  # noqa: PLC0415

        return tenancy.users_visible_to_user_qs(user)


def _org_user_membership_qs(user, organization_outer_ref):
    from django.apps import apps

    OrganizationUser = apps.get_model("cf_users", "OrganizationUser")
    return OrganizationUser.objects.filter(
        user_id=user.pk, organization_id=organization_outer_ref
    )


def _branch_user_for_org_qs(user, organization_outer_ref):
    from django.apps import apps

    BranchUser = apps.get_model("cf_users", "BranchUser")
    return BranchUser.objects.filter(
        user_id=user.pk, branch__organization_id=organization_outer_ref
    )


class TenantManager(models.Manager.from_queryset(TenantQuerySet)):
    """Default manager that exposes tenant scoping helpers."""

    def __init__(self, *args, tenant_parent_field: str | None = None, **kwargs):
        self.tenant_parent_field = tenant_parent_field
        super().__init__(*args, **kwargs)

    def get_queryset(self) -> TenantQuerySet:
        qs = super().get_queryset()
        qs.tenant_parent_field = self.tenant_parent_field
        return qs

    def for_user(self, user) -> models.QuerySet:
        return self.get_queryset().for_user(user)

    def visible_to(self, user=None) -> models.QuerySet:
        return self.get_queryset().visible_to(user=user)

    def for_active_tenant(self, user=None) -> models.QuerySet:
        return self.get_queryset().for_active_tenant(user=user)
