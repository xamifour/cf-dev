# cf-dev/cf_src/appsinn/cf_users/models.py

"""Concrete user and multitenant organisation models."""

from django.utils.translation import gettext_lazy as _

from .base.models import (
    AbstractBranch,
    AbstractBranchUser,
    AbstractOrganization,
    AbstractOrganizationGroup,
    AbstractOrganizationGroupMembership,
    AbstractOrganizationOwner,
    AbstractOrganizationUser,
    AbstractUser,
)
from .managers import TenantManager
from .sequences import CodeSequence  # noqa: F401 — registered model

__all__ = [
    "User",
    "Organization",
    "OrganizationUser",
    "OrganizationOwner",
    "OrganizationGroup",
    "OrganizationGroupMembership",
    "Branch",
    "BranchUser",
    "CodeSequence",
]


class User(AbstractUser):
    class Meta(AbstractUser.Meta):
        abstract = False
        verbose_name = _("user")
        verbose_name_plural = _("users")
        swappable = "AUTH_USER_MODEL"


class Organization(AbstractOrganization):
    objects = TenantManager()

    class Meta(AbstractOrganization.Meta):
        abstract = False
        verbose_name = _("organisation")
        verbose_name_plural = _("organisations")


class OrganizationUser(AbstractOrganizationUser):
    objects = TenantManager()

    class Meta(AbstractOrganizationUser.Meta):
        abstract = False
        verbose_name = _("organisation user")
        verbose_name_plural = _("organisation users")


class OrganizationOwner(AbstractOrganizationOwner):
    objects = TenantManager()

    class Meta(AbstractOrganizationOwner.Meta):
        abstract = False
        verbose_name = _("organisation owner")
        verbose_name_plural = _("organisation owners")


class Branch(AbstractBranch):
    objects = TenantManager()

    class Meta(AbstractBranch.Meta):
        abstract = False
        verbose_name = _("branch")
        verbose_name_plural = _("branches")


class BranchUser(AbstractBranchUser):
    objects = TenantManager()

    class Meta(AbstractBranchUser.Meta):
        abstract = False
        verbose_name = _("branch user")
        verbose_name_plural = _("branch users")


class OrganizationGroup(AbstractOrganizationGroup):
    objects = TenantManager()

    class Meta(AbstractOrganizationGroup.Meta):
        abstract = False


class OrganizationGroupMembership(AbstractOrganizationGroupMembership):
    objects = TenantManager(tenant_parent_field="group")

    class Meta(AbstractOrganizationGroupMembership.Meta):
        abstract = False
