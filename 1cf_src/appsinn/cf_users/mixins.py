# cf-dev/cf_src/appsinn/cf_users/mixins.py

"""Shared model mixins for CF domain applications."""

from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _


class ValidateOrgBranchMixin:
    """Utility mixin that validates branch consistency between related objects."""

    def _validate_org_branch_relation(
        self,
        rel: str,
        branch_field: str = "branch",
        field_error: str = "branch",
    ) -> None:
        related_obj = getattr(self, rel, None)
        current_branch = getattr(self, branch_field, None)
        if related_obj is None or current_branch is None:
            return
        related_branch = getattr(related_obj, "branch", None)
        if related_branch and current_branch.pk != related_branch.pk:
            raise ValidationError(
                {
                    field_error: _(
                        "The branch of this record does not match the branch of the related object."
                    )
                }
            )


class AuditMixin(models.Model):
    """
    Adds UUID PK, timestamps and audit fields to models.

    On every save during a request, ``created_by`` / ``modified_by`` are filled
    from the authenticated request user (see ``AuditUserMiddleware``).
    ``id``, ``created_at`` and ``modified_at`` are always set by the ORM.

    Default list ordering is most recently modified first. Subclasses may
    override for structural order (e.g. week number, sort_order).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True, db_index=True)
    modified_at = models.DateTimeField(_("modified at"), auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="%(app_label)s_%(class)s_created",
        verbose_name=_("created by"),
    )
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="%(app_label)s_%(class)s_modified",
        verbose_name=_("modified by"),
    )

    class Meta:
        abstract = True
        ordering = ("-modified_at",)

    def _apply_audit_user(self) -> None:
        """Stamp created_by / modified_by from the request context when set."""
        from cf_users.audit import get_current_user  # noqa: PLC0415

        user = get_current_user()
        if user is None or not getattr(user, "is_authenticated", False):
            return
        # Only set if the FK fields exist on this instance (always for mixin).
        if self._state.adding and not getattr(self, "created_by_id", None):
            self.created_by = user
        self.modified_by = user

    def save(self, *args, **kwargs):
        self._apply_audit_user()
        super().save(*args, **kwargs)


class AutoIncrementCodeMixin(models.Model):
    """
    Generates immutable zero-padded prefixed codes on first save.

    Uses a database sequence (SELECT … FOR UPDATE) so concurrent creates scale
    without scanning the whole table. The sequence is floor-aligned to the
    highest existing code for this model/prefix so a missing or reset counter
    cannot re-issue an in-use code (avoids UNIQUE IntegrityError on create).
    """

    code_field: str = "code"
    code_length: int = 8
    code_prefix: str = ""
    # Optional override for sequence name (defaults to "{prefix}_seq").
    code_sequence_name: str | None = None
    # Retries if a unique code collision still occurs (race / desynced data).
    code_generate_max_attempts: int = 5

    class Meta:
        abstract = True

    def _code_sequence_name(self) -> str:
        if self.code_sequence_name:
            return self.code_sequence_name
        return f"{self.code_prefix or 'CODE'}_seq"

    def _code_sequence_floor(self) -> int:
        """Highest numeric suffix already stored for this prefix on this model."""
        from .sequences import max_numeric_suffix_for_prefix  # noqa: PLC0415

        field = self.code_field
        codes = (
            self.__class__.objects.exclude(**{f"{field}__isnull": True})
            .exclude(**{field: ""})
            .values_list(field, flat=True)
        )
        return max_numeric_suffix_for_prefix(codes, self.code_prefix or "")

    def _generate_code(self) -> str:
        from .sequences import format_sequence_code  # noqa: PLC0415

        return format_sequence_code(
            prefix=self.code_prefix,
            length=self.code_length,
            name=self._code_sequence_name(),
            floor=self._code_sequence_floor(),
        )

    def save(self, *args, **kwargs):
        from django.db import IntegrityError  # noqa: PLC0415

        field = self.code_field
        if self._state.adding and not getattr(self, field, None):
            attempts = max(1, int(self.code_generate_max_attempts))
            last_exc: Exception | None = None
            for _attempt in range(attempts):
                # Nested atomic so a failed unique insert does not poison the
                # outer request transaction (admin form save).
                try:
                    with transaction.atomic():
                        setattr(self, field, self._generate_code())
                        super().save(*args, **kwargs)
                    return
                except IntegrityError as exc:
                    last_exc = exc
                    # Clear PK if the backend assigned one before the failure.
                    if self.pk and not self.__class__.objects.filter(pk=self.pk).exists():
                        self.pk = None
                    setattr(self, field, None)
                    self._state.adding = True
                    continue
            if last_exc is not None:
                raise last_exc
            return
        if not self._state.adding:
            try:
                db_instance = self.__class__.objects.get(pk=self.pk)
            except self.__class__.DoesNotExist:
                pass
            else:
                if getattr(db_instance, field) != getattr(self, field):
                    raise ValidationError(
                        _("The code field cannot be modified after creation.")
                    )
        super().save(*args, **kwargs)
