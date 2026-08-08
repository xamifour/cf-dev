"""
CF Church Management System
People base models: Member, Family, Visitor, Follow-up, Department, Cell Group.
All models are abstract. Concrete implementations live in people/models.py.
"""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from cf_users.mixins import AuditMixin, AutoIncrementCodeMixin, ValidateOrgBranchMixin


# ---------------------------------------------------------------------------
# Family
# ---------------------------------------------------------------------------
class AbstractFamily(AuditMixin):
    """Household / family unit."""
    branch = models.ForeignKey("cf_users.Branch", on_delete=models.PROTECT, related_name="families", verbose_name=_("branch"))
    family_name = models.CharField(_("family name"), max_length=255)
    primary_phone = models.CharField(_("primary phone"), max_length=30)
    home_address = models.TextField(_("home address"))

    class Meta:
        abstract = True
        ordering = ("-modified_at", "family_name")

    def __str__(self) -> str:
        return self.family_name


# ---------------------------------------------------------------------------
# Member
# ---------------------------------------------------------------------------
class AbstractMember(AutoIncrementCodeMixin, AuditMixin, ValidateOrgBranchMixin):
    """
    Church membership profile at a branch.

    Person identity (name, email, phone, birth date, gender, address) lives on
    the linked User. This model stores membership-only data (status, family,
    branch, member #). Every Member has exactly one User (portal-ready or
    unusable-password directory).

    ``member_number`` is unique **per organisation** (not platform-wide).
    The prefix is the first three letters of the organisation name (e.g. "Word
    Chapel International" → ``WOR00000001``). Sequences are per organisation.
    """

    STATUS_CHOICES = [
        ("ACTIVE", _("Active")),
        ("INACTIVE", _("Inactive")),
        ("TRANSFERRED", _("Transferred")),
        ("DECEASED", _("Deceased")),
    ]
    code_field = "member_number"
    # Dynamic: first 3 letters of organisation name (see ``_member_code_prefix``).
    code_prefix = ""
    code_length = 8

    organization = models.ForeignKey(
        "cf_users.Organization",
        on_delete=models.PROTECT,
        related_name="members",
        verbose_name=_("organisation"),
        help_text=_("Denormalised from branch for org-scoped member numbers."),
    )
    branch = models.ForeignKey(
        "cf_users.Branch",
        on_delete=models.PROTECT,
        related_name="members",
        verbose_name=_("branch"),
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="member_profile",
        verbose_name=_("user account"),
        help_text=_(
            "Login / person identity. Required. Use an unusable password for "
            "directory-only members until they are invited to the portal."
        ),
    )
    family = models.ForeignKey(
        "cf_people.Family",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="members",
        verbose_name=_("family"),
    )
    member_number = models.CharField(
        _("member number"),
        max_length=50,
        blank=True,
        help_text=_("Unique within the organisation (auto-generated if blank)."),
    )
    membership_status = models.CharField(
        _("membership status"),
        max_length=20,
        choices=STATUS_CHOICES,
        default="ACTIVE",
        db_index=True,
    )

    class Meta:
        abstract = True
        ordering = ("-modified_at", "user__last_name", "user__first_name")
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "member_number"],
                name="%(app_label)s_%(class)s_unique_org_member_number",
            )
        ]
        indexes = [
            models.Index(fields=["organization", "member_number"]),
            models.Index(fields=["branch", "membership_status"]),
        ]

    def __str__(self) -> str:
        return self.get_full_name() or str(self.member_number or self.pk)

    def _sync_organization_from_branch(self) -> None:
        if self.branch_id:
            # Prefer already-loaded relation; fall back to FK id only.
            org_id = getattr(self.branch, "organization_id", None)
            if org_id:
                self.organization_id = org_id

    def _member_code_prefix(self) -> str:
        """
        Three-letter prefix derived from the organisation name.

        Letters only, uppercased, padded with X if the name is short.
        Example: "Grace Assembly" → ``GRA``.
        """
        import re

        self._sync_organization_from_branch()
        org = None
        if self.organization_id:
            org = getattr(self, "organization", None)
            if org is None or getattr(org, "pk", None) != self.organization_id:
                from django.apps import apps  # noqa: PLC0415

                Organization = apps.get_model("cf_users", "Organization")
                org = (
                    Organization.objects.filter(pk=self.organization_id)
                    .only("name", "trade_name")
                    .first()
                )
        elif self.branch_id:
            org = getattr(getattr(self, "branch", None), "organization", None)

        raw = ""
        if org is not None:
            raw = (getattr(org, "trade_name", None) or getattr(org, "name", None) or "")
        letters = re.sub(r"[^A-Za-z]", "", str(raw)).upper()
        if not letters:
            letters = "ORG"
        return (letters + "XXX")[:3]

    def _code_sequence_name(self) -> str:
        org_id = self.organization_id
        if not org_id and self.branch_id:
            org_id = getattr(self.branch, "organization_id", None)
        prefix = self._member_code_prefix()
        if org_id:
            return f"{prefix}_{org_id}_seq"
        return f"{prefix}_seq"

    def _code_sequence_floor(self) -> int:
        """Highest suffix already used for this organisation + prefix."""
        from cf_users.sequences import max_numeric_suffix_for_prefix  # noqa: PLC0415

        self._sync_organization_from_branch()
        prefix = self._member_code_prefix()
        field = self.code_field
        qs = self.__class__.objects.exclude(**{f"{field}__isnull": True}).exclude(
            **{field: ""}
        )
        if self.organization_id:
            qs = qs.filter(organization_id=self.organization_id)
        codes = qs.values_list(field, flat=True)
        return max_numeric_suffix_for_prefix(codes, prefix)

    def _generate_code(self) -> str:
        from cf_users.sequences import format_sequence_code  # noqa: PLC0415

        prefix = self._member_code_prefix()
        return format_sequence_code(
            prefix=prefix,
            length=self.code_length,
            name=self._code_sequence_name(),
            floor=self._code_sequence_floor(),
        )

    # ── Identity proxies (single source of truth: User) ───────────────────
    @property
    def first_name(self) -> str:
        return getattr(self.user, "first_name", "") or ""

    @property
    def last_name(self) -> str:
        return getattr(self.user, "last_name", "") or ""

    @property
    def middle_name(self) -> str:
        return getattr(self.user, "middle_name", "") or ""

    @property
    def email(self) -> str:
        return getattr(self.user, "email", "") or ""

    @property
    def phone_number(self):
        return getattr(self.user, "phone_number", None)

    def get_full_name(self) -> str:
        if self.user_id and hasattr(self.user, "get_full_name"):
            return self.user.get_full_name()
        return f"{self.first_name} {self.last_name}".strip()

    def clean(self) -> None:
        self._sync_organization_from_branch()
        self._validate_org_branch_relation("family")
        if not self.user_id:
            raise ValidationError(
                {"user": _("A member must be linked to a user account for identity.")}
            )
        if self.branch_id and self.organization_id:
            if self.branch.organization_id != self.organization_id:
                raise ValidationError(
                    {
                        "branch": _(
                            "Branch must belong to the same organisation as this member."
                        )
                    }
                )

    def full_clean(self, *args, **kwargs):
        # Ensure organisation is set before field null-checks run.
        self._sync_organization_from_branch()
        return super().full_clean(*args, **kwargs)

    def save(self, *args, **kwargs):
        self._sync_organization_from_branch()
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# Child-specific extension
# ---------------------------------------------------------------------------
class AbstractChildProfile(models.Model):
    """Extra profile fields for members who are minors (1-to-1 extension)."""

    member = models.OneToOneField(
        "cf_people.Member",
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="child_profile",
        verbose_name=_("member"),
    )
    medical_notes = models.TextField(_("medical notes"), blank=True)
    allergies = models.TextField(_("allergies"), blank=True)
    check_in_pin = models.CharField(_("check-in PIN"), max_length=10, blank=True, help_text=_("Secure PIN used by parents/guardians for child check-in authorisation."))

    class Meta:
        abstract = True

    def __str__(self) -> str:
        return f"Child profile – {self.member}"


class AbstractGuardian(models.Model):
    """Maps a guardian (adult member) to a child (minor member)."""
    child = models.ForeignKey("cf_people.Member", on_delete=models.CASCADE, related_name="guardians", verbose_name=_("child"))
    guardian = models.ForeignKey("cf_people.Member", on_delete=models.PROTECT, related_name="children_links", verbose_name=_("guardian / adult"))
    relationship_type = models.CharField(_("relationship type"), max_length=50, help_text=_("e.g. Father, Mother, Grandparent, Legal Guardian"))

    class Meta:
        abstract = True
        unique_together = ("child", "guardian")

    def __str__(self) -> str:
        return f"{self.guardian} → {self.child} ({self.relationship_type})"

    def clean(self) -> None:
        if self.child_id and self.guardian_id and self.child_id == self.guardian_id:
            raise ValidationError(_("A member cannot be their own guardian."))


# ---------------------------------------------------------------------------
# Visitor
# ---------------------------------------------------------------------------
class AbstractVisitor(AuditMixin):
    """Tracks first-time and returning visitors."""
    CONVERSION_CHOICES = [
        ("PENDING", _("Pending Follow-up")),
        ("IN_PROGRESS", _("Follow-up In Progress")),
        ("CONVERTED", _("Joined as Member")),
        ("DECLINED", _("Not Interested")),
    ]
    branch = models.ForeignKey("cf_users.Branch", on_delete=models.PROTECT, related_name="visitors", verbose_name=_("branch"))
    first_name = models.CharField(_("first name"), max_length=150)
    last_name = models.CharField(_("last name"), max_length=150)
    phone_number = models.CharField(_("phone number"), max_length=30)
    email = models.EmailField(_("email"), null=True, blank=True)
    invited_by = models.ForeignKey("cf_people.Member", on_delete=models.SET_NULL, null=True, blank=True, related_name="invited_visitors", verbose_name=_("invited by"))
    visit_date = models.DateField(_("visit date"), db_index=True)
    conversion_status = models.CharField(_("conversion status"), max_length=30, choices=CONVERSION_CHOICES, default="PENDING", db_index=True)

    class Meta:
        abstract = True
        ordering = ("-modified_at", "-visit_date")

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"


# ---------------------------------------------------------------------------
# Follow-up
# ---------------------------------------------------------------------------
class AbstractFollowUp(AuditMixin, ValidateOrgBranchMixin):
    """Records a scheduled or completed follow-up interaction with a visitor."""
    branch = models.ForeignKey("cf_users.Branch", on_delete=models.PROTECT, related_name="follow_ups", verbose_name=_("branch"))
    visitor = models.ForeignKey("cf_people.Visitor", on_delete=models.CASCADE, related_name="follow_ups", verbose_name=_("visitor"))
    assigned_to = models.ForeignKey("cf_people.Member", on_delete=models.PROTECT, related_name="assigned_follow_ups", verbose_name=_("assigned to"))
    scheduled_date = models.DateField(_("scheduled date"), db_index=True)
    completed_date = models.DateField(_("completed date"), null=True, blank=True)
    outcome_notes = models.TextField(_("outcome notes"), blank=True)

    class Meta:
        abstract = True
        ordering = ("-modified_at", "scheduled_date")

    def __str__(self) -> str:
        return f"Follow-up: {self.visitor} → {self.assigned_to}"

    def clean(self) -> None:
        self._validate_org_branch_relation("visitor")
        self._validate_org_branch_relation("assigned_to")
        if self.completed_date and self.scheduled_date and self.completed_date < self.scheduled_date:
            raise ValidationError({"completed_date": _("Completion date cannot be earlier than the scheduled date.")})


# ---------------------------------------------------------------------------
# Department
# ---------------------------------------------------------------------------
class AbstractDepartment(AuditMixin):
    """A ministry department or committee within a branch."""
    branch = models.ForeignKey("cf_users.Branch", on_delete=models.PROTECT, related_name="departments", verbose_name=_("branch"))
    name = models.CharField(_("name"), max_length=255)
    description = models.TextField(_("description"), blank=True)
    is_active = models.BooleanField(_("is active"), default=True)

    class Meta:
        abstract = True
        ordering = ("-modified_at", "name")
        unique_together = ("branch", "name")

    def __str__(self) -> str:
        return self.name


# ---------------------------------------------------------------------------
# Department Membership
# ---------------------------------------------------------------------------
class AbstractDepartmentMember(AuditMixin):
    """Links a Member to a Department."""
    ROLE_CHOICES = [
        ("LEADER", _("Department Leader")),
        ("ASSISTANT", _("Assistant Leader")),
        ("MEMBER", _("Regular Member")),
    ]
    department = models.ForeignKey("cf_people.Department", on_delete=models.CASCADE, related_name="memberships", verbose_name=_("department"))
    member = models.ForeignKey("cf_people.Member", on_delete=models.CASCADE, related_name="department_memberships", verbose_name=_("member"))
    role = models.CharField(_("role"), max_length=20, choices=ROLE_CHOICES, default="MEMBER")

    class Meta:
        abstract = True
        unique_together = ("department", "member")

    def __str__(self) -> str:
        return f"{self.member} – {self.department} ({self.get_role_display()})"


# ---------------------------------------------------------------------------
# Zone (area under a Branch)
# ---------------------------------------------------------------------------
class AbstractZone(AuditMixin):
    """
    Geographic / pastoral area under a Branch.

    Hierarchy: Organisation → Branch → Zone → Sub group (cell / satellite).

    Uniqueness (per branch):
    - ``name`` must be unique within a branch
    - ``code`` must be unique within a branch when provided (blank codes allowed)
    """

    branch = models.ForeignKey(
        "cf_users.Branch",
        on_delete=models.PROTECT,
        related_name="zones",
        verbose_name=_("branch"),
    )
    name = models.CharField(
        _("name"),
        max_length=255,
        help_text=_("e.g. ZONE 13, Kasoa West. Unique within the branch."),
    )
    code = models.CharField(
        _("code"),
        max_length=32,
        blank=True,
        null=True,
        help_text=_("Optional short code, e.g. Z13. Unique within the branch."),
    )
    description = models.TextField(_("description"), blank=True)
    coordinator = models.ForeignKey(
        "cf_people.Member",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="coordinated_zones",
        verbose_name=_("zonal coordinator"),
    )
    is_active = models.BooleanField(_("is active"), default=True)

    class Meta:
        abstract = True
        ordering = ("-modified_at", "branch", "name")
        verbose_name = _("zone")
        verbose_name_plural = _("zones")
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "name"],
                name="%(app_label)s_%(class)s_unique_branch_name",
            ),
            models.UniqueConstraint(
                fields=["branch", "code"],
                condition=models.Q(code__isnull=False) & ~models.Q(code=""),
                name="%(app_label)s_%(class)s_unique_branch_code",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.branch})"

    def clean(self) -> None:
        super().clean()
        # Normalise empty code so multiple zones may omit code without clashing.
        if self.code is not None and not str(self.code).strip():
            self.code = None
        else:
            if self.code is not None:
                self.code = str(self.code).strip()

        if not self.branch_id:
            return

        qs = self.__class__.objects.filter(branch_id=self.branch_id)
        if self.pk:
            qs = qs.exclude(pk=self.pk)

        if self.name and qs.filter(name__iexact=self.name.strip()).exists():
            raise ValidationError(
                {
                    "name": _(
                        "A zone with this name already exists in this branch."
                    )
                }
            )
        if self.code and qs.filter(code__iexact=self.code).exists():
            raise ValidationError(
                {
                    "code": _(
                        "A zone with this code already exists in this branch."
                    )
                }
            )

    def save(self, *args, **kwargs):
        if self.code is not None and not str(self.code).strip():
            self.code = None
        elif self.code is not None:
            self.code = str(self.code).strip()
        if self.name:
            self.name = self.name.strip()
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# Sub group (Cell / Satellite under a Zone)
# ---------------------------------------------------------------------------
class AbstractSubBranch(AuditMixin, ValidateOrgBranchMixin):
    """
    A cell or satellite fellowship under a Zone.

    Hierarchy: Organisation → Branch → Zone → Sub group.
    ``branch`` is denormalised from ``zone.branch`` for tenant filtering.
    """

    GROUP_CHOICES = [
        ("CELL", _("Cell Group")),
        ("SATELLITE", _("Satellite Fellowship")),
        # Legacy spelling kept for migrated rows
        ("SETTLITE", _("Satellite Fellowship (legacy)")),
    ]
    branch = models.ForeignKey(
        "cf_users.Branch",
        on_delete=models.PROTECT,
        related_name="sub_groups",
        verbose_name=_("branch"),
    )
    zone = models.ForeignKey(
        "cf_people.Zone",
        on_delete=models.PROTECT,
        related_name="sub_groups",
        verbose_name=_("zone"),
        help_text=_("Sub groups (cells / satellites) belong to a zone under the branch."),
    )
    name = models.CharField(_("name"), max_length=255)
    description = models.TextField(_("description"), blank=True)
    leader = models.ForeignKey(
        "cf_people.Member",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="led_sub_groups",
        verbose_name=_("leader"),
    )
    group_type = models.CharField(
        _("group type"),
        max_length=20,
        choices=GROUP_CHOICES,
        default="CELL",
        db_index=True,
    )
    is_active = models.BooleanField(_("is active"), default=True)

    class Meta:
        abstract = True
        ordering = ("-modified_at", "zone", "name")
        unique_together = ("zone", "name")
        verbose_name = _("sub group")
        verbose_name_plural = _("sub groups")

    def __str__(self) -> str:
        return f"{self.name} ({self.get_group_type_display()})"

    def clean(self) -> None:
        if self.zone_id:
            # Align branch with zone for tenancy + integrity.
            if self.zone.branch_id and (
                not self.branch_id or self.branch_id != self.zone.branch_id
            ):
                self.branch = self.zone.branch
            self._validate_org_branch_relation("zone")
        if self.leader_id:
            self._validate_org_branch_relation("leader")

    def save(self, *args, **kwargs):
        if self.zone_id and self.zone.branch_id:
            self.branch_id = self.zone.branch_id
        super().save(*args, **kwargs)