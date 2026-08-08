# cf-dev/cf_src/appsinn/cf_people/models.py

"""Concrete people domain models."""

from django.utils.translation import gettext_lazy as _

from cf_users.managers import TenantManager

from .base.models import (
    AbstractChildProfile,
    AbstractDepartment,
    AbstractDepartmentMember,
    AbstractFamily,
    AbstractFollowUp,
    AbstractGuardian,
    AbstractMember,
    AbstractSubBranch,
    AbstractVisitor,
    AbstractZone,
)


class Family(AbstractFamily):
    objects = TenantManager()

    class Meta(AbstractFamily.Meta):
        abstract = False
        verbose_name = _("family")
        verbose_name_plural = _("families")


class Member(AbstractMember):
    objects = TenantManager()

    class Meta(AbstractMember.Meta):
        abstract = False
        verbose_name = _("member")
        verbose_name_plural = _("members")


class ChildProfile(AbstractChildProfile):
    objects = TenantManager(tenant_parent_field="member")

    class Meta(AbstractChildProfile.Meta):
        abstract = False
        verbose_name = _("child profile")
        verbose_name_plural = _("child profiles")


class Guardian(AbstractGuardian):
    objects = TenantManager(tenant_parent_field="child")

    class Meta(AbstractGuardian.Meta):
        abstract = False
        verbose_name = _("guardian")
        verbose_name_plural = _("guardians")


class Visitor(AbstractVisitor):
    objects = TenantManager()

    class Meta(AbstractVisitor.Meta):
        abstract = False
        verbose_name = _("visitor")
        verbose_name_plural = _("visitors")


class FollowUp(AbstractFollowUp):
    objects = TenantManager()

    class Meta(AbstractFollowUp.Meta):
        abstract = False
        verbose_name = _("follow-up")
        verbose_name_plural = _("follow-ups")


class Department(AbstractDepartment):
    objects = TenantManager()

    class Meta(AbstractDepartment.Meta):
        abstract = False
        verbose_name = _("department")
        verbose_name_plural = _("departments")


class DepartmentMember(AbstractDepartmentMember):
    objects = TenantManager(tenant_parent_field="department")

    class Meta(AbstractDepartmentMember.Meta):
        abstract = False
        verbose_name = _("department member")
        verbose_name_plural = _("department members")


class Zone(AbstractZone):
    """Pastoral / geographic area under a Branch."""

    objects = TenantManager()

    class Meta(AbstractZone.Meta):
        abstract = False
        verbose_name = _("zone")
        verbose_name_plural = _("zones")


class SubBranch(AbstractSubBranch):
    """Cell or satellite group under a Zone."""

    objects = TenantManager()

    class Meta(AbstractSubBranch.Meta):
        abstract = False
        verbose_name = _("sub group")
        verbose_name_plural = _("sub groups")
