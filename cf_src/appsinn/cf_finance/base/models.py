# cf-dev/cf_src/appsinn/cf_finance/base/models.py

"""
CF Church Management System
Finance base models: Funds, Financial Periods, Budgets, Transactions, Assets,
HR (Employee, Leave, Payroll).
All models are abstract. Concrete implementations live in finance/models.py.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from cf_users.mixins import AuditMixin, AutoIncrementCodeMixin, ValidateOrgBranchMixin


# ---------------------------------------------------------------------------
# Fund
# ---------------------------------------------------------------------------
class AbstractFund(AuditMixin):
    """
    Branch-scoped church fund / income classification.

    Used to categorise receipts such as tithe, offerings, projects, and charity.
    """

    FUND_TYPE_CHOICES = [
        ("OFFERINGS", _("Offerings")),
        ("TITHE", _("Tithe")),
        ("PROJECT", _("Project")),
        ("CHARITY", _("Charity")),
        ("BUILDING", _("Building fund")),
        ("MISSIONS", _("Missions")),
        ("WELFARE", _("Welfare / benevolence")),
        ("THANKSGIVING", _("Thanksgiving")),
        ("FIRST_FRUITS", _("First fruits")),
        ("PLEDGE", _("Pledge")),
        ("SEED", _("Seed")),
        ("OTHER", _("Other")),
    ]

    branch = models.ForeignKey(
        "cf_users.Branch",
        on_delete=models.PROTECT,
        related_name="funds",
        verbose_name=_("branch"),
    )
    fund_type = models.CharField(
        _("fund type"),
        max_length=20,
        choices=FUND_TYPE_CHOICES,
        db_index=True,
        help_text=_("Primary classification of this fund."),
    )
    name = models.CharField(
        _("name"),
        max_length=150,
        help_text=_(
            "Display name for this fund, e.g. 'General Tithe' or 'New Auditorium Project'."
        ),
    )
    amount = models.DecimalField(
        _("amount"),
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text=_("Current balance or target amount for this fund."),
    )
    description = models.TextField(_("description"), blank=True)
    is_active = models.BooleanField(_("is active"), default=True, db_index=True)

    class Meta:
        abstract = True
        ordering = ("-modified_at", "fund_type", "name")
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "fund_type", "name"],
                name="%(app_label)s_%(class)s_unique_branch_type_name",
            )
        ]
        indexes = [
            models.Index(fields=["branch", "fund_type", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_fund_type_display()} – {self.name}"


# ---------------------------------------------------------------------------
# Financial Period
# ---------------------------------------------------------------------------
class AbstractFinancialPeriod(AuditMixin):
    """Defines an accounting period (e.g. FY2025 Q1) scoped to a branch."""
    branch = models.ForeignKey("cf_users.Branch", on_delete=models.PROTECT, related_name="financial_periods", verbose_name=_("branch"))
    period_name = models.CharField(_("period name"), max_length=100)
    start_date = models.DateField(_("start date"))
    end_date = models.DateField(_("end date"))
    is_closed = models.BooleanField(_("is closed"), default=False)

    class Meta:
        abstract = True
        ordering = ("-modified_at", "-start_date")
        unique_together = ("branch", "period_name")

    def __str__(self) -> str:
        return f"{self.period_name} ({self.branch})"

    def clean(self) -> None:
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValidationError({"end_date": _("End date must be after the start date.")})


# ---------------------------------------------------------------------------
# Budget
# ---------------------------------------------------------------------------
class AbstractBudget(AuditMixin, ValidateOrgBranchMixin):
    """Allocates funds to a department within a financial period."""
    branch = models.ForeignKey("cf_users.Branch", on_delete=models.PROTECT, related_name="budgets", verbose_name=_("branch"))
    financial_period = models.ForeignKey("cf_finance.FinancialPeriod", on_delete=models.PROTECT, related_name="budgets", verbose_name=_("financial period"))
    department = models.ForeignKey("cf_people.Department", on_delete=models.PROTECT, null=True, blank=True, related_name="budgets", verbose_name=_("department"))
    allocated_amount = models.DecimalField(_("allocated amount"), max_digits=15, decimal_places=2)
    notes = models.TextField(_("notes"), blank=True)

    class Meta:
        abstract = True

    def __str__(self) -> str:
        dept = self.department or _("General")
        return f"{dept} – {self.financial_period} ({self.allocated_amount})"

    def clean(self) -> None:
        self._validate_org_branch_relation("financial_period")
        if self.department:
            self._validate_org_branch_relation("department")


# ---------------------------------------------------------------------------
# Transaction
# ---------------------------------------------------------------------------
class AbstractTransaction(AutoIncrementCodeMixin, AuditMixin, ValidateOrgBranchMixin):
    """Records a single income or expense transaction for a branch."""

    TYPE_CHOICES = [
        ("INCOME", _("Income")),
        ("EXPENSE", _("Expense")),
    ]
    code_field = "reference_code"
    code_prefix = "TXN"
    code_length = 8

    branch = models.ForeignKey(
        "cf_users.Branch",
        on_delete=models.PROTECT,
        related_name="transactions",
        verbose_name=_("branch"),
    )
    financial_period = models.ForeignKey(
        "cf_finance.FinancialPeriod",
        on_delete=models.PROTECT,
        related_name="transactions",
        verbose_name=_("financial period"),
    )
    fund = models.ForeignKey(
        "cf_finance.Fund",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="transactions",
        verbose_name=_("fund"),
        help_text=_("Optional church fund this transaction belongs to (e.g. Tithe, Offerings)."),
    )
    transaction_type = models.CharField(
        _("transaction type"), max_length=10, choices=TYPE_CHOICES, db_index=True
    )
    category = models.CharField(_("category"), max_length=100)
    amount = models.DecimalField(_("amount"), max_digits=15, decimal_places=2)
    reference_code = models.CharField(
        _("reference code"), max_length=64, unique=True, blank=True
    )
    gateway_reference = models.CharField(
        _("gateway / payment reference"),
        max_length=255,
        blank=True,
        help_text=_(
            "External reference from a payment gateway or mobile money provider."
        ),
    )
    description = models.TextField(_("description"), blank=True)
    is_approved = models.BooleanField(_("is approved"), default=False, db_index=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_transactions",
        verbose_name=_("approved by"),
    )

    class Meta:
        abstract = True
        ordering = ("-modified_at",)

    def __str__(self) -> str:
        return f"{self.reference_code} – {self.get_transaction_type_display()} {self.amount}"

    def clean(self) -> None:
        self._validate_org_branch_relation("financial_period")
        if self.fund_id:
            self._validate_org_branch_relation("fund")


# ---------------------------------------------------------------------------
# Asset Category
# ---------------------------------------------------------------------------
class AbstractAssetCategory(AuditMixin):
    """Groups assets by type, each with its own annual depreciation rate."""
    branch = models.ForeignKey("cf_users.Branch", on_delete=models.PROTECT, related_name="asset_categories", verbose_name=_("branch"))
    name = models.CharField(_("name"), max_length=150)
    depreciation_rate_annual = models.DecimalField(_("annual depreciation rate (%)"), max_digits=5, decimal_places=2, help_text=_("Percentage of asset value depreciated per year."))

    class Meta:
        abstract = True
        ordering = ("-modified_at", "name")
        unique_together = ("branch", "name")

    def __str__(self) -> str:
        return self.name


# ---------------------------------------------------------------------------
# Asset
# ---------------------------------------------------------------------------
class AbstractAsset(AuditMixin, ValidateOrgBranchMixin):
    """A physical or intangible asset owned by a branch."""
    STATUS_CHOICES = [
        ("OPERATIONAL", _("Operational")),
        ("UNDER_REPAIR", _("Under Repair")),
        ("DISPOSED", _("Disposed / Written Off")),
    ]
    branch = models.ForeignKey("cf_users.Branch", on_delete=models.PROTECT, related_name="assets", verbose_name=_("branch"))
    category = models.ForeignKey("cf_finance.AssetCategory", on_delete=models.PROTECT, related_name="assets", verbose_name=_("category"))
    name = models.CharField(_("name"), max_length=255)
    purchase_cost = models.DecimalField(_("purchase cost"), max_digits=15, decimal_places=2)
    purchase_date = models.DateField(_("purchase date"))
    current_status = models.CharField(_("current status"), max_length=20, choices=STATUS_CHOICES, default="OPERATIONAL", db_index=True)
    notes = models.TextField(_("notes"), blank=True)

    class Meta:
        abstract = True
        ordering = ("-modified_at", "name")

    def __str__(self) -> str:
        return f"{self.name} ({self.get_current_status_display()})"

    def clean(self) -> None:
        self._validate_org_branch_relation("category")


# ---------------------------------------------------------------------------
# HR: Employee
# ---------------------------------------------------------------------------
class AbstractEmployee(AuditMixin, ValidateOrgBranchMixin):
    """Staff employment record linked to a church member profile."""
    STATUS_CHOICES = [
        ("ACTIVE", _("Active")),
        ("SUSPENDED", _("Suspended")),
        ("TERMINATED", _("Terminated")),
    ]
    TYPE_CHOICES = [
        ("PASTORAL", _("Pastoral Staff")),
        ("ADMIN", _("Administrative Staff")),
        ("CONTRACTOR", _("External Contractor")),
        ("VOLUNTEER", _("Stipend Volunteer")),
    ]
    branch = models.ForeignKey("cf_users.Branch", on_delete=models.PROTECT, related_name="employees", verbose_name=_("branch"))
    member = models.OneToOneField("cf_people.Member", on_delete=models.PROTECT, related_name="employee_profile", verbose_name=_("church member profile"))
    job_title = models.CharField(_("job title"), max_length=150)
    employment_type = models.CharField(_("employment type"), max_length=20, choices=TYPE_CHOICES, default="ADMIN")
    status = models.CharField(_("employment status"), max_length=20, choices=STATUS_CHOICES, default="ACTIVE", db_index=True)
    hire_date = models.DateField(_("hire date"))
    termination_date = models.DateField(_("termination date"), null=True, blank=True)
    base_salary = models.DecimalField(_("base salary"), max_digits=15, decimal_places=2, help_text=_("Base contractual pay amount per pay cycle."))
    bank_account_details = models.TextField(_("bank account details"), blank=True)

    class Meta:
        abstract = True
        ordering = ("-modified_at", "member__user__last_name", "member__user__first_name")

    def __str__(self) -> str:
        return f"{self.member} – {self.job_title} ({self.get_employment_type_display()})"

    def clean(self) -> None:
        self._validate_org_branch_relation("member")
        if self.termination_date and self.hire_date and self.termination_date < self.hire_date:
            raise ValidationError({"termination_date": _("Termination date cannot be before the hire date.")})


# ---------------------------------------------------------------------------
# HR: Leave
# ---------------------------------------------------------------------------
class AbstractLeave(AuditMixin, ValidateOrgBranchMixin):
    """A leave request submitted by a member of staff."""
    TYPE_CHOICES = [
        ("ANNUAL", _("Annual Vacation")),
        ("SICK", _("Sick Leave")),
        ("MATERNITY", _("Maternity / Paternity")),
        ("SABBATICAL", _("Pastoral Sabbatical")),
        ("OTHER", _("Unpaid / Other Leave")),
    ]
    STATUS_CHOICES = [
        ("PENDING", _("Pending Approval")),
        ("APPROVED", _("Approved")),
        ("REJECTED", _("Rejected")),
    ]
    branch = models.ForeignKey("cf_users.Branch", on_delete=models.PROTECT, related_name="leaves", verbose_name=_("branch"))
    employee = models.ForeignKey("cf_finance.Employee", on_delete=models.CASCADE, related_name="leave_records", verbose_name=_("employee"))
    leave_type = models.CharField(_("leave type"), max_length=20, choices=TYPE_CHOICES, default="ANNUAL")
    start_date = models.DateField(_("start date"))
    end_date = models.DateField(_("end date"))
    status = models.CharField(_("status"), max_length=20, choices=STATUS_CHOICES, default="PENDING", db_index=True)
    reason = models.TextField(_("reason for leave"), blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_leaves", verbose_name=_("approved by"))

    class Meta:
        abstract = True
        ordering = ("-modified_at", "-start_date")

    def __str__(self) -> str:
        return f"{self.employee.member} – {self.get_leave_type_display()} ({self.status})"

    def clean(self) -> None:
        self._validate_org_branch_relation("employee")
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError({"start_date": _("Start date cannot be after the end date.")})


# ---------------------------------------------------------------------------
# HR: Payroll
# ---------------------------------------------------------------------------
class AbstractPayroll(AuditMixin, ValidateOrgBranchMixin):
    """A payroll run for a single employee covering a defined pay period."""
    STATUS_CHOICES = [
        ("DRAFT", _("Draft")),
        ("APPROVED", _("Approved")),
        ("PAID", _("Disbursed / Paid")),
    ]
    branch = models.ForeignKey("cf_users.Branch", on_delete=models.PROTECT, related_name="payrolls", verbose_name=_("branch"))
    employee = models.ForeignKey("cf_finance.Employee", on_delete=models.PROTECT, related_name="payroll_history", verbose_name=_("employee"))
    pay_period_start = models.DateField(_("pay period start"))
    pay_period_end = models.DateField(_("pay period end"))
    gross_pay = models.DecimalField(_("gross pay"), max_digits=15, decimal_places=2)
    allowances = models.DecimalField(_("allowances"), max_digits=15, decimal_places=2, default=0, help_text=_("Housing, utility, or ministerial travel allowances."))
    deductions = models.DecimalField(_("deductions"), max_digits=15, decimal_places=2, default=0, help_text=_("Tax, health insurance, or pension contributions."))
    net_pay = models.DecimalField(_("net pay"), max_digits=15, decimal_places=2, help_text=_("Calculated take-home amount: gross + allowances − deductions."))
    payment_date = models.DateField(_("payment date"), null=True, blank=True)
    status = models.CharField(_("status"), max_length=20, choices=STATUS_CHOICES, default="DRAFT", db_index=True)

    class Meta:
        abstract = True
        ordering = ("-modified_at", "-pay_period_end")

    def __str__(self) -> str:
        return f"{self.employee.member} – Period to {self.pay_period_end} ({self.get_status_display()})"

    def clean(self) -> None:
        self._validate_org_branch_relation("employee")
        if self.pay_period_start and self.pay_period_end and self.pay_period_start > self.pay_period_end:
            raise ValidationError({"pay_period_start": _("Pay period start cannot be after the end date.")})
        if self.gross_pay is not None:
            allowances = self.allowances or 0
            deductions = self.deductions or 0
            self.net_pay = (self.gross_pay + allowances) - deductions