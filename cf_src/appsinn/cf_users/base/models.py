# cf-dev/cf_src/appsinn/cf_users/base/models.py

"""Abstract user, organisation, and branch models."""

from __future__ import annotations

import uuid
from datetime import timedelta
from functools import cached_property

from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import AbstractUser as DjangoAbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField

from cf_utils.utils import unique_slug

from ..mixins import AuditMixin, AutoIncrementCodeMixin


class UserManager(DjangoUserManager):
    def _create_user(self, username, email, password, **extra_fields):
        user = super()._create_user(username, email, password, **extra_fields)
        if user.email:
            from allauth.account.models import EmailAddress  # noqa: PLC0415

            if not EmailAddress.objects.filter(user=user, primary=True).exists():
                EmailAddress.objects.update_or_create(
                    user=user,
                    email=user.email,
                    defaults={"verified": True, "primary": True},
                )
        return user


class AbstractUser(DjangoAbstractUser):
    """System-wide user account."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(
        _("username"),
        max_length=64,
        unique=True,
        help_text=_(
            "9–64 characters. Letters, digits, and one special character (_ or @) "
            "allowed, but not at the start. No spaces."
        ),
    )
    email = models.EmailField(_("email address"), unique=True)
    first_name = models.CharField(_("first name"), max_length=64)
    last_name = models.CharField(_("last name"), max_length=64)
    middle_name = models.CharField(_("middle name"), max_length=64, blank=True, null=True)
    phone_number = PhoneNumberField(
        _("phone number"),
        unique=True,
        help_text=_("Primary contact number, e.g. +233201234567."),
    )
    phone_number2 = PhoneNumberField(
        _("alternative phone"),
        unique=True,
        blank=True,
        null=True,
        help_text=_("Optional backup number."),
    )
    birth_date = models.DateField(
        _("birth date"),
        blank=True,
        null=True,
        help_text=_("Used for verification, age groups, and birthday greetings."),
    )
    GENDER_CHOICES = [
        ("MALE", _("Male")),
        ("FEMALE", _("Female")),
        ("OTHER", _("Other")),
    ]
    gender = models.CharField(
        _("gender"),
        max_length=20,
        choices=GENDER_CHOICES,
        blank=True,
        null=True,
    )
    address = models.CharField(_("address"), max_length=256)
    city = models.CharField(_("city"), max_length=64)
    country = models.CharField(_("country"), max_length=64)
    geo_address = models.CharField(
        _("GPS address"),
        max_length=32,
        blank=True,
        null=True,
        help_text=_("Digital home address (e.g. Ghana Post GPS code)."),
    )
    url = models.URLField(_("URL"), blank=True, null=True)
    company = models.CharField(_("company"), max_length=128, blank=True, null=True)
    bio = models.TextField(_("bio"), blank=True, null=True)
    notes = models.TextField(_("notes"), blank=True, null=True)
    language = models.CharField(
        _("language"),
        max_length=8,
        choices=settings.LANGUAGES,
        default=settings.LANGUAGE_CODE,
    )
    is_church_staff = models.BooleanField(_("is church staff"), default=False)
    notify_via_inapp = models.BooleanField(_("notify via in-app"), default=True)
    notify_via_email = models.BooleanField(_("notify via email"), default=True)
    notify_via_sms = models.BooleanField(_("notify via SMS"), default=False)
    notify_via_whatsapp = models.BooleanField(_("notify via WhatsApp"), default=False)
    password_updated = models.DateField(_("password updated"), blank=True, null=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True, null=True)
    modified_at = models.DateTimeField(_("modified at"), auto_now=True, null=True)
    created_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users_created",
        verbose_name=_("created by"),
    )
    modified_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users_modified",
        verbose_name=_("modified by"),
    )

    objects = UserManager()

    REQUIRED_FIELDS = [
        "email",
        "first_name",
        "last_name",
        "phone_number",
        "address",
        "city",
        "country",
    ]

    class Meta(DjangoAbstractUser.Meta):
        abstract = True
        ordering = ("-modified_at", "last_name", "first_name")
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["phone_number"]),
            models.Index(fields=["is_church_staff"]),
        ]

    def __str__(self) -> str:
        return self.get_full_name() or self.username or self.email or str(self.pk)

    def clean(self) -> None:
        super().clean()
        if self.email:
            self.email = self.email.lower()
            if (
                self.__class__.objects.filter(email__iexact=self.email)
                .exclude(pk=self.pk)
                .exists()
            ):
                raise ValidationError({"email": _("A user with this email already exists.")})
        if self.phone_number and (
            self.__class__.objects.filter(phone_number=self.phone_number)
            .exclude(pk=self.pk)
            .exists()
        ):
            raise ValidationError(
                {"phone_number": _("A user with this phone number already exists.")}
            )
        if self.phone_number2 and (
            self.__class__.objects.filter(phone_number2=self.phone_number2)
            .exclude(pk=self.pk)
            .exists()
        ):
            raise ValidationError(
                {
                    "phone_number2": _(
                        "A user with this alternative phone number already exists."
                    )
                }
            )
        if self.username:
            from ..validators import validate_username  # noqa: PLC0415

            try:
                validate_username(self.username)
            except ValidationError as exc:
                raise ValidationError({"username": exc.messages}) from exc

    def set_password(self, raw_password):
        self.password_updated = timezone.now().date()
        return super().set_password(raw_password)

    def save(self, *args, **kwargs):
        # Stamp audit fields (User is not an AuditMixin subclass).
        from cf_users.audit import get_current_user  # noqa: PLC0415

        actor = get_current_user()
        if actor is not None and getattr(actor, "is_authenticated", False):
            if self._state.adding and not getattr(self, "created_by_id", None):
                self.created_by = actor
            self.modified_by = actor
        super().save(*args, **kwargs)

    def has_password_expired(self) -> bool:
        if not self.has_usable_password() or not self.password_updated:
            return False
        from .. import settings as app_settings  # noqa: PLC0415

        if self.is_staff:
            expiration_days = app_settings.STAFF_USER_PASSWORD_EXPIRATION
        else:
            expiration_days = app_settings.USER_PASSWORD_EXPIRATION
        if not expiration_days:
            return False
        expiry_date = self.password_updated + timedelta(days=int(expiration_days))
        return expiry_date < timezone.now().date()

    def managed_organization_ids_qs(self):
        """Subquery of managed organisation IDs (scale-safe; not a full list)."""
        from ..tenancy import managed_organization_ids_qs  # noqa: PLC0415

        if self.is_superuser:
            Organization = apps.get_model("cf_users", "Organization")
            return Organization.objects.values("id")
        return managed_organization_ids_qs(self)

    @cached_property
    def organizations_managed(self) -> list:
        """
        Managed organisation IDs for the current user.

        Superusers intentionally get an empty list here — they must use active
        tenant context or explicit superuser short-circuits, never a dump of
        every organisation UUID.
        """
        if self.is_superuser:
            return []
        cache_key = f"user_{self.pk}_orgs_managed"
        orgs = cache.get(cache_key)
        if orgs is not None:
            return orgs
        # Bound materialisation: managers rarely administer huge org counts.
        orgs = list(
            self.org_roles.filter(is_org_manager=True)
            .values_list("organization_id", flat=True)
            .distinct()[:5000]
        )
        cache.set(cache_key, orgs, timeout=3600)
        return orgs

    @property
    def organizations_owned(self) -> list:
        return list(
            self.org_roles.filter(owned_organizations__isnull=False)
            .values_list("organization_id", flat=True)
            .distinct()[:5000]
        )

    @property
    def is_org_owner_of_any_organization(self) -> bool:
        return self.org_roles.filter(owned_organizations__isnull=False).exists()

    def is_org_member(self, organization) -> bool:
        from ..tenancy import user_is_org_member  # noqa: PLC0415

        return user_is_org_member(self, getattr(organization, "pk", organization))

    def is_org_manager(self, organization) -> bool:
        from ..tenancy import user_manages_organization  # noqa: PLC0415

        return user_manages_organization(
            self, getattr(organization, "pk", organization)
        )

    def is_org_owner(self, organization) -> bool:
        if self.is_superuser:
            return True
        org_id = getattr(organization, "pk", organization)
        return self.org_roles.filter(
            organization_id=org_id, owned_organizations__isnull=False
        ).exists()

    def has_access_to_organization(self, organization, obj=None) -> bool:
        from ..tenancy import user_can_access_organization  # noqa: PLC0415

        org_id = getattr(organization, "pk", organization)
        if user_can_access_organization(self, org_id):
            return True
        if obj:
            owner = getattr(obj, "created_by", None) or getattr(obj, "user", None)
            return owner == self
        return False

    def accessible_branch_ids_qs(self):
        from ..tenancy import accessible_branch_ids_qs  # noqa: PLC0415

        if self.is_superuser:
            Branch = apps.get_model("cf_users", "Branch")
            return Branch.objects.values("id")
        return accessible_branch_ids_qs(self)

    @cached_property
    def branches_dict(self) -> dict:
        """
        Small role map for the current user's branches.

        Superusers get an empty map — use active tenant context instead of
        caching every branch in the system.
        """
        if self.is_superuser:
            return {}
        cache_key = f"user_{self.pk}_branches_dict"
        access_map = cache.get(cache_key)
        if access_map is not None:
            return access_map

        Branch = apps.get_model("cf_users", "Branch")
        access_map = {}
        for bu in self.branch_roles.only("branch_id", "role", "is_org_manager")[:5000]:
            access_map[bu.branch_id] = {
                "role": bu.role,
                "is_org_manager": bu.is_org_manager,
            }

        managed_org_ids = self.organizations_managed
        if managed_org_ids:
            for b_id in (
                Branch.objects.filter(organization_id__in=managed_org_ids)
                .values_list("id", flat=True)
                .iterator()
            ):
                access_map.setdefault(
                    b_id, {"role": "ORG_MANAGER", "is_org_manager": True}
                )

        cache.set(cache_key, access_map, timeout=3600)
        return access_map

    def _invalidate_access_cache(self) -> None:
        """Call after changing user roles/permissions."""
        cache.delete_many(
            [f"user_{self.pk}_branches_dict", f"user_{self.pk}_orgs_managed"]
        )
        for key in ("branches_dict", "organizations_managed"):
            self.__dict__.pop(key, None)

    @property
    def accessible_branches(self) -> list:
        """
        Materialised branch IDs for legacy callers.

        Prefer accessible_branch_ids_qs() or active tenant context at scale.
        Superusers return [] (use request.branch / for_user short-circuit).
        """
        if self.is_superuser:
            return []
        return list(self.branches_dict.keys())

    @property
    def branches_managed(self) -> list:
        if self.is_superuser:
            return []
        return [
            b_id
            for b_id, meta in self.branches_dict.items()
            if meta.get("is_org_manager")
        ]

    @property
    def is_branch_manager(self) -> bool:
        if self.is_superuser:
            return True
        return self.branch_roles.filter(is_org_manager=True).exists() or (
            self.org_roles.filter(is_org_manager=True).exists()
        )

    @property
    def is_branch_member(self) -> bool:
        if self.is_superuser:
            return True
        return self.branch_roles.exists() or self.org_roles.exists()

    # ── Church membership composition ─────────────────────────────────────
    @property
    def is_church_member(self) -> bool:
        """True when this login identity has a linked Member profile."""
        return hasattr(self, "member_profile") and self.member_profile is not None

    def get_member_profile(self):
        """Return linked Member or None without raising RelatedObjectDoesNotExist."""
        from django.core.exceptions import ObjectDoesNotExist  # noqa: PLC0415

        try:
            return self.member_profile
        except ObjectDoesNotExist:
            return None


class AbstractOrganization(AutoIncrementCodeMixin, AuditMixin):
    """Top-level entity: denomination, diocese, church network, or independent church."""

    code_field = "code"
    code_prefix = "ORG"
    code_length = 8

    name = models.CharField(_("name"), max_length=128, db_index=True)
    trade_name = models.CharField(
        _("trade / display name"), max_length=128, blank=True, db_index=True
    )
    slug = models.SlugField(
        _("slug"), max_length=128, blank=True, null=True, unique=True, editable=False
    )
    code = models.CharField(
        _("code"),
        max_length=32,
        unique=True,
        blank=True,
        null=True,
        editable=False,
        db_index=True,
        help_text=_("System-generated organisation code (e.g. ORG00000001). Immutable."),
    )
    email = models.EmailField(_("email"), blank=True, db_index=True)
    phone_number = PhoneNumberField(_("phone number"), unique=True, blank=True, null=True)
    url = models.URLField(_("URL"), blank=True)
    description = models.TextField(_("description"), blank=True)
    address = models.CharField(_("address"), max_length=256)
    city = models.CharField(_("city"), max_length=64, db_index=True)
    country = models.CharField(_("country"), max_length=64, db_index=True)
    geo_address = models.CharField(_("GPS address"), max_length=32, blank=True, null=True)
    logo = models.ImageField(
        _("logo"), max_length=256, blank=True, null=True, upload_to="org_logos/"
    )
    logo_svg = models.TextField(_("SVG logo"), blank=True, null=True)
    theme_color = models.CharField(
        _("theme colour"),
        max_length=7,
        blank=True,
        null=True,
        help_text=_("Hex colour code, e.g. #4A90D9."),
    )
    notes = models.TextField(_("notes"), blank=True, null=True)
    notifications_enabled = models.BooleanField(_("notifications enabled"), default=True)
    birthday_greetings_enabled = models.BooleanField(
        _("birthday greetings enabled"),
        default=True,
        help_text=_("When off, no automatic birthday messages are sent for this organisation."),
    )
    birthday_subject = models.CharField(
        _("birthday subject / title"),
        max_length=200,
        blank=True,
        help_text=_(
            "Typed subject/title for automatic birthday messages. "
            "Placeholders: {name}, {org}, {branch}, {year}."
        ),
    )
    birthday_message = models.TextField(
        _("birthday message"),
        blank=True,
        help_text=_(
            "Typed body for automatic birthday messages (organisation default). "
            "Branches may override. Placeholders: {name}, {org}, {branch}, {year}."
        ),
    )
    is_active = models.BooleanField(_("is active"), default=True, db_index=True)

    class Meta:
        abstract = True
        ordering = ("-modified_at", "name")
        indexes = [models.Index(fields=["country", "city"])]

    def __str__(self) -> str:
        return self.trade_name or self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, value=self.trade_name or self.name)
        # AutoIncrementCodeMixin generates code on first save, then persists.
        super().save(*args, **kwargs)


class AbstractOrganizationUser(models.Model):
    """Membership link between User and Organisation."""

    ROLE_CHOICES = [
        ("VIEWER", _("Viewer / Member")),
        ("AUDITOR", _("Denomination Auditor")),
        ("OVERSEER", _("Regional Overseer / Bishop")),
        ("ADMIN", _("HQ Administrator")),
    ]
    ROLE_VIEWER = "VIEWER"
    ROLE_AUDITOR = "AUDITOR"
    ROLE_OVERSEER = "OVERSEER"
    ROLE_ADMIN = "ADMIN"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="org_roles",
        verbose_name=_("user"),
    )
    organization = models.ForeignKey(
        "cf_users.Organization",
        on_delete=models.CASCADE,
        related_name="user_roles",
        verbose_name=_("organisation"),
    )
    role = models.CharField(
        _("role"),
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_VIEWER,
    )
    is_org_manager = models.BooleanField(
        _("is manager"),
        default=False,
        help_text=_(
            "Grants administrative access across this organisation's branches."
        ),
    )
    is_admin = models.BooleanField(_("is admin"), default=False)

    class Meta:
        abstract = True
        constraints = [
            models.UniqueConstraint(
                fields=["user", "organization", "role"],
                name="%(app_label)s_%(class)s_unique_user_org_role",
            )
        ]
        indexes = [
            models.Index(fields=["organization", "is_org_manager"]),
            models.Index(fields=["user", "is_org_manager"]),
        ]

    def __str__(self) -> str:
        return f"{self.user} → {self.organization} ({self.get_role_display()})"

    def clean(self) -> None:
        if not self.user_id or not self.organization_id:
            return
        if self.user.is_org_owner(self.organization) and not self.is_admin:
            raise ValidationError(
                _(
                    "%(username)s is the owner of %(organization)s and cannot be downgraded."
                )
                % {
                    "username": self.user.username,
                    "organization": self.organization,
                }
            )

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)

        if is_new and self.is_org_manager:
            OrganizationOwner = apps.get_model("cf_users", "OrganizationOwner")
            with transaction.atomic():
                if not OrganizationOwner.objects.filter(
                    organization_id=self.organization_id
                ).exists():
                    OrganizationOwner.objects.create(
                        organization=self.organization,
                        organization_user=self,
                    )


class AbstractOrganizationOwner(models.Model):
    """Primary owner of an Organisation."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.OneToOneField(
        "cf_users.Organization",
        on_delete=models.CASCADE,
        related_name="owner_record",
        verbose_name=_("organisation"),
    )
    organization_user = models.ForeignKey(
        "cf_users.OrganizationUser",
        on_delete=models.CASCADE,
        related_name="owned_organizations",
        verbose_name=_("organisation user"),
    )

    class Meta:
        abstract = True

    def __str__(self) -> str:
        return f"Owner of {self.organization}"

    def clean(self) -> None:
        if self.organization_user.organization_id != self.organization_id:
            raise ValidationError(
                {
                    "organization_user": _(
                        "The selected user is not a member of this organization."
                    )
                }
            )


class AbstractBranch(AuditMixin):
    """A physical or virtual campus / branch of an Organisation."""

    TYPE_CHOICES = [
        ("PARENT", _("Parent / Main Campus")),
        ("CHILD", _("Child / Satellite Campus")),
    ]
    organization = models.ForeignKey(
        "cf_users.Organization",
        on_delete=models.CASCADE,
        related_name="branches",
        verbose_name=_("organisation"),
    )
    branch_type = models.CharField(
        _("branch type"), max_length=10, choices=TYPE_CHOICES, default="CHILD"
    )
    name = models.CharField(_("name"), max_length=128, db_index=True)
    slug = models.SlugField(
        _("slug"), max_length=128, blank=True, null=True, unique=True, editable=False
    )
    description = models.CharField(_("description"), max_length=512, blank=True, null=True)
    active = models.BooleanField(_("is active"), default=True, db_index=True)
    is_default = models.BooleanField(
        _("is default"),
        default=False,
        help_text=_("Only one branch per organisation may be the default."),
    )
    address = models.CharField(_("address"), max_length=256)
    city = models.CharField(_("city"), max_length=64, db_index=True)
    country = models.CharField(_("country"), max_length=64, db_index=True)
    geo_address = models.CharField(_("GPS address"), max_length=32, blank=True, null=True)
    notifications_enabled = models.BooleanField(_("notifications enabled"), default=True)
    birthday_greetings_enabled = models.BooleanField(
        _("birthday greetings enabled"),
        default=True,
        help_text=_(
            "When off, no automatic birthday messages are sent for this branch. "
            "Organisation-level must also be enabled."
        ),
    )
    birthday_subject = models.CharField(
        _("birthday subject / title"),
        max_length=200,
        blank=True,
        help_text=_(
            "Optional branch override for the subject. Leave blank to use the "
            "organisation text. Placeholders: {name}, {org}, {branch}, {year}."
        ),
    )
    birthday_message = models.TextField(
        _("birthday message"),
        blank=True,
        help_text=_(
            "Optional branch override for the birthday body. Leave blank to use "
            "the organisation message. Placeholders: {name}, {org}, {branch}, {year}."
        ),
    )

    class Meta:
        abstract = True
        ordering = ("-modified_at",)
        indexes = [
            models.Index(fields=["organization", "active"]),
            models.Index(fields=["organization", "is_default"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "is_default"],
                condition=models.Q(is_default=True),
                name="%(app_label)s_%(class)s_unique_default_branch",
            )
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = f"{self.organization_id}-{self.name}" if self.organization_id else self.name
            self.slug = unique_slug(self, value=base)
        super().save(*args, **kwargs)


class AbstractBranchUser(AuditMixin):
    """Membership link between a User and a Branch."""

    ROLE_CHOICES = [
        ("ADMIN", _("Administrator")),
        ("EDITOR", _("Editor")),
        ("VIEWER", _("Viewer")),
    ]
    ROLE_ADMIN = "ADMIN"
    ROLE_EDITOR = "EDITOR"
    ROLE_VIEWER = "VIEWER"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="branch_roles",
        verbose_name=_("user"),
    )
    branch = models.ForeignKey(
        "cf_users.Branch",
        on_delete=models.CASCADE,
        related_name="user_roles",
        verbose_name=_("branch"),
    )
    role = models.CharField(
        _("role"), max_length=20, choices=ROLE_CHOICES, default=ROLE_VIEWER
    )
    is_org_manager = models.BooleanField(_("is manager"), default=False, db_index=True)

    class Meta:
        abstract = True
        constraints = [
            models.UniqueConstraint(
                fields=["user", "branch"],
                name="%(app_label)s_%(class)s_unique_user_branch",
            )
        ]
        indexes = [
            models.Index(fields=["branch", "is_org_manager"]),
            models.Index(fields=["user", "is_org_manager"]),
        ]

    def __str__(self) -> str:
        return f"{self.user} @ {self.branch} ({self.get_role_display()})"

    def ensure_organization_membership(self) -> None:
        """
        Every branch user is automatically an organisation user.

        Default role is Viewer / Member. Existing org memberships are left
        unchanged (role is not downgraded). Default organisation groups are
        applied when missing.
        """
        if not self.user_id or not self.branch_id:
            return
        OrganizationUser = apps.get_model("cf_users", "OrganizationUser")
        OrganizationGroup = apps.get_model("cf_users", "OrganizationGroup")
        OrganizationGroupMembership = apps.get_model(
            "cf_users", "OrganizationGroupMembership"
        )
        org_id = self.branch.organization_id
        if not org_id:
            return
        if not OrganizationUser.objects.filter(
            user_id=self.user_id, organization_id=org_id
        ).exists():
            OrganizationUser.objects.create(
                user_id=self.user_id,
                organization_id=org_id,
                role="VIEWER",
                is_org_manager=False,
                is_admin=False,
            )
        # Assign default organisation groups (idempotent).
        default_groups = OrganizationGroup.objects.filter(
            organization_id=org_id, is_default=True, is_active=True
        )
        for group in default_groups.iterator():
            OrganizationGroupMembership.objects.get_or_create(
                group=group,
                user_id=self.user_id,
            )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.ensure_organization_membership()


class AbstractOrganizationGroup(AuditMixin):
    """
    Organisation-scoped permission group.

    Each organisation manages its own groups (unlike global Django auth groups).
    Privileges are standard Django permissions; enforced via
    ``OrganizationGroupBackend`` and MultitenantAdminMixin.
    """

    organization = models.ForeignKey(
        "cf_users.Organization",
        on_delete=models.CASCADE,
        related_name="permission_groups",
        verbose_name=_("organisation"),
    )
    name = models.CharField(_("name"), max_length=150)
    description = models.TextField(_("description"), blank=True)
    permissions = models.ManyToManyField(
        "auth.Permission",
        blank=True,
        related_name="organization_groups",
        verbose_name=_("permissions"),
        help_text=_(
            "Privileges granted to members of this group within the organisation."
        ),
    )
    is_default = models.BooleanField(
        _("default for new members"),
        default=False,
        help_text=_(
            "When enabled, users who join a branch of this organisation "
            "are added to this group automatically."
        ),
    )
    is_active = models.BooleanField(_("is active"), default=True, db_index=True)

    class Meta:
        abstract = True
        ordering = ("-modified_at", "name")
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"],
                name="%(app_label)s_%(class)s_unique_org_group_name",
            )
        ]
        indexes = [
            models.Index(fields=["organization", "is_default", "is_active"]),
        ]
        verbose_name = _("organisation group")
        verbose_name_plural = _("organisation groups")

    def __str__(self) -> str:
        return f"{self.organization}: {self.name}"


class AbstractOrganizationGroupMembership(AuditMixin):
    """User membership in an organisation permission group."""

    group = models.ForeignKey(
        "cf_users.OrganizationGroup",
        on_delete=models.CASCADE,
        related_name="memberships",
        verbose_name=_("group"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organization_group_memberships",
        verbose_name=_("user"),
    )

    class Meta:
        abstract = True
        ordering = ("-modified_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["group", "user"],
                name="%(app_label)s_%(class)s_unique_group_user",
            )
        ]
        verbose_name = _("organisation group membership")
        verbose_name_plural = _("organisation group memberships")

    def __str__(self) -> str:
        return f"{self.user} ∈ {self.group}"

    def clean(self) -> None:
        if not self.group_id or not self.user_id:
            return
        from cf_users.audit import get_current_user  # noqa: PLC0415

        actor = get_current_user()
        # Superusers may assign any user to any org group (platform admin).
        if actor is not None and getattr(actor, "is_superuser", False):
            return
        OrganizationUser = apps.get_model("cf_users", "OrganizationUser")
        if not OrganizationUser.objects.filter(
            user_id=self.user_id, organization_id=self.group.organization_id
        ).exists():
            raise ValidationError(
                {
                    "user": _(
                        "User must be a member of the organisation before "
                        "joining its groups."
                    )
                }
            )
