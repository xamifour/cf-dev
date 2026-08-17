# cf-dev/cf_src/appsinn/cf_finance/admin.py

"""Admin registrations for finance and HR domain models."""

from django.contrib import admin

from cf_users.multitenancy import MultitenantAdminMixin, MultitenantBranchFilter
from cf_users.utils import BaseAdmin

from .models import (
    Asset,
    AssetCategory,
    Budget,
    Employee,
    FinancialPeriod,
    Fund,
    Leave,
    Payroll,
    Transaction,
)


@admin.register(Fund)
class FundAdmin(MultitenantAdminMixin, BaseAdmin):
    list_display = ("name", "fund_type", "amount", "branch", "is_active")
    list_filter = (MultitenantBranchFilter, "fund_type", "is_active")
    search_fields = ("name", "description")
    autocomplete_fields = ("branch",)
    ordering = ("-modified_at", "branch", "fund_type", "name")


@admin.register(FinancialPeriod)
class FinancialPeriodAdmin(MultitenantAdminMixin, BaseAdmin):
    list_display = ("period_name", "branch", "start_date", "end_date", "is_closed")
    list_filter = (MultitenantBranchFilter, "is_closed")
    search_fields = ("period_name",)
    autocomplete_fields = ("branch",)


@admin.register(Budget)
class BudgetAdmin(MultitenantAdminMixin, BaseAdmin):
    multitenant_shared_relations = ["financial_period", "department"]
    list_display = ("branch", "financial_period", "department", "allocated_amount")
    list_filter = (MultitenantBranchFilter,)
    autocomplete_fields = ("branch", "financial_period", "department")


@admin.register(Transaction)
class TransactionAdmin(MultitenantAdminMixin, BaseAdmin):
    multitenant_shared_relations = ["financial_period", "fund"]
    list_display = (
        "reference_code",
        "branch",
        "fund",
        "transaction_type",
        "amount",
        "is_approved",
        "created_at",
    )
    list_filter = (
        MultitenantBranchFilter,
        "transaction_type",
        "is_approved",
        "fund__fund_type",
    )
    search_fields = ("reference_code", "category", "gateway_reference", "fund__name")
    readonly_fields = ("reference_code",)
    autocomplete_fields = ("branch", "financial_period", "fund", "approved_by")


@admin.register(AssetCategory)
class AssetCategoryAdmin(MultitenantAdminMixin, BaseAdmin):
    list_display = ("name", "branch", "depreciation_rate_annual")
    list_filter = (MultitenantBranchFilter,)
    search_fields = ("name",)
    autocomplete_fields = ("branch",)


@admin.register(Asset)
class AssetAdmin(MultitenantAdminMixin, BaseAdmin):
    multitenant_shared_relations = ["category"]
    list_display = ("name", "branch", "category", "purchase_cost", "current_status")
    list_filter = (MultitenantBranchFilter, "current_status")
    search_fields = ("name",)
    autocomplete_fields = ("branch", "category")


@admin.register(Employee)
class EmployeeAdmin(MultitenantAdminMixin, BaseAdmin):
    multitenant_shared_relations = ["member"]
    list_display = ("member", "branch", "job_title", "employment_type", "status")
    list_filter = (MultitenantBranchFilter, "employment_type", "status")
    search_fields = (
        "member__user__first_name",
        "member__user__last_name",
        "job_title",
    )
    autocomplete_fields = ("branch", "member")


@admin.register(Leave)
class LeaveAdmin(MultitenantAdminMixin, BaseAdmin):
    multitenant_shared_relations = ["employee"]
    list_display = ("employee", "branch", "leave_type", "start_date", "end_date", "status")
    list_filter = (MultitenantBranchFilter, "leave_type", "status")
    autocomplete_fields = ("branch", "employee", "approved_by")


@admin.register(Payroll)
class PayrollAdmin(MultitenantAdminMixin, BaseAdmin):
    multitenant_shared_relations = ["employee"]
    list_display = (
        "employee",
        "branch",
        "pay_period_end",
        "gross_pay",
        "net_pay",
        "status",
    )
    list_filter = (MultitenantBranchFilter, "status")
    autocomplete_fields = ("branch", "employee")
