# cf-dev/cf_src/appsinn/cf_finance/models.py

"""Concrete finance and HR domain models."""

from django.utils.translation import gettext_lazy as _

from cf_users.managers import TenantManager

from .base.models import (
    AbstractAsset,
    AbstractAssetCategory,
    AbstractBudget,
    AbstractEmployee,
    AbstractFinancialPeriod,
    AbstractFund,
    AbstractLeave,
    AbstractPayroll,
    AbstractTransaction,
)


class Fund(AbstractFund):
    objects = TenantManager()

    class Meta(AbstractFund.Meta):
        abstract = False
        verbose_name = _("fund")
        verbose_name_plural = _("funds")


class FinancialPeriod(AbstractFinancialPeriod):
    objects = TenantManager()

    class Meta(AbstractFinancialPeriod.Meta):
        abstract = False
        verbose_name = _("financial period")
        verbose_name_plural = _("financial periods")


class Budget(AbstractBudget):
    objects = TenantManager()

    class Meta(AbstractBudget.Meta):
        abstract = False
        verbose_name = _("budget")
        verbose_name_plural = _("budgets")


class Transaction(AbstractTransaction):
    objects = TenantManager()

    class Meta(AbstractTransaction.Meta):
        abstract = False
        verbose_name = _("transaction")
        verbose_name_plural = _("transactions")


class AssetCategory(AbstractAssetCategory):
    objects = TenantManager()

    class Meta(AbstractAssetCategory.Meta):
        abstract = False
        verbose_name = _("asset category")
        verbose_name_plural = _("asset categories")


class Asset(AbstractAsset):
    objects = TenantManager()

    class Meta(AbstractAsset.Meta):
        abstract = False
        verbose_name = _("asset")
        verbose_name_plural = _("assets")


class Employee(AbstractEmployee):
    objects = TenantManager()

    class Meta(AbstractEmployee.Meta):
        abstract = False
        verbose_name = _("employee")
        verbose_name_plural = _("employees")


class Leave(AbstractLeave):
    objects = TenantManager()

    class Meta(AbstractLeave.Meta):
        abstract = False
        verbose_name = _("leave")
        verbose_name_plural = _("leave records")


class Payroll(AbstractPayroll):
    objects = TenantManager()

    class Meta(AbstractPayroll.Meta):
        abstract = False
        verbose_name = _("payroll")
        verbose_name_plural = _("payrolls")
