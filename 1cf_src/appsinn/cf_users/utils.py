# cf-dev/cf_src/appsinn/cf_users/utils.py

import logging

import bleach
from django.conf import settings
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Admin Base Class
# ---------------------------------------------------------------------------
if "reversion" in settings.INSTALLED_APPS:
    from reversion.admin import VersionAdmin as BaseModelAdmin
else:
    from django.contrib.admin import ModelAdmin as BaseModelAdmin


AUDIT_FIELD_NAMES = (
    "id",
    "created_at",
    "modified_at",
    "created_by",
    "modified_by",
)


class BaseAdmin(BaseModelAdmin):
    """
    Base admin class with common settings.

    Changelists prefer most-recently-modified first when the model has
    ``modified_at``; otherwise fall back to model ``Meta.ordering``.
    Subclasses may still set ``ordering`` explicitly.

    Cross-cutting behaviour for all CF model admins:
    - Prepend organisation + branch list filters when the model supports them
    - Extend search to organisation / branch / zone / sub group name fields
    - AuditMixin fields are always read-only under a collapsible Audit section

    Audit fields (``created_by`` / ``modified_by``) are stamped via
    ``AuditUserMiddleware`` + ``AuditMixin.save``; ``save_model`` also sets
    them explicitly as a safety net.
    """

    history_latest_first = True

    def _admin_model_has_field(self, name: str) -> bool:
        """Whether this admin's model has a concrete/related field ``name``."""
        model = getattr(self, "model", None)
        if model is None:
            return False
        try:
            model._meta.get_field(name)
            return True
        except Exception:
            return False

    def _admin_model_field_names(self) -> set[str]:
        model = getattr(self, "model", None)
        if model is None:
            return set()
        return {f.name for f in model._meta.fields}

    def get_ordering(self, request):
        # Prefer an explicit ordering on the concrete admin class.
        explicit = getattr(type(self), "ordering", None)
        if explicit is not None:
            return list(explicit)
        model = getattr(self, "model", None)
        if model is not None and any(
            f.name == "modified_at" for f in model._meta.fields
        ):
            return ["-modified_at"]
        return list(super().get_ordering(request) or [])

    # ── list filters: organisation, branch first ─────────────────────────
    def get_list_filter(self, request):
        from cf_users.multitenancy import (  # noqa: PLC0415
            MultitenantBranchFilter,
            MultitenantOrgFilter,
            resolve_branch_filter_path,
            resolve_organization_filter_path,
        )

        filters = list(super().get_list_filter(request) or [])
        model = self.model
        parent = getattr(self, "multitenant_parent", None)

        # Drop bare duplicates so we can re-insert smart filters at the front.
        stripped = []
        for f in filters:
            if f in (MultitenantOrgFilter, MultitenantBranchFilter):
                continue
            if f in ("organization", "branch", "organization_id", "branch_id"):
                continue
            if f in ("branch__organization", "branch__organization_id"):
                continue
            stripped.append(f)

        prepend = []
        if resolve_organization_filter_path(model, multitenant_parent=parent):
            prepend.append(MultitenantOrgFilter)
        branch_path = resolve_branch_filter_path(model, multitenant_parent=parent)
        if branch_path:
            prepend.append(MultitenantBranchFilter)

        # Drop modified_at so we can always append it last when present.
        middle = []
        for f in stripped:
            if f == "modified_at":
                continue
            middle.append(f)

        result = prepend + middle
        if self._admin_model_has_field("modified_at"):
            result.append("modified_at")
        return result

    # ── search: organisation / branch / zone / sub group ─────────────────
    def get_search_fields(self, request):
        fields = list(super().get_search_fields(request) or [])
        names = self._admin_model_field_names()
        extras: list[str] = []

        if "organization" in names:
            extras.extend(
                (
                    "organization__name",
                    "organization__trade_name",
                    "organization__code",
                )
            )
        if "branch" in names:
            extras.extend(
                (
                    "branch__name",
                    "branch__code",
                    "branch__organization__name",
                    "branch__organization__trade_name",
                    "branch__organization__code",
                )
            )
        if "zone" in names:
            extras.extend(("zone__name", "zone__code"))
        if "subgroup" in names:
            extras.extend(("subgroup__name", "subgroup__code"))

        # Parent-linked models (e.g. AttendanceSeat via record)
        parent = getattr(self, "multitenant_parent", None)
        if parent:
            for rel in (
                f"{parent}__organization__name",
                f"{parent}__branch__name",
                f"{parent}__branch__organization__name",
                f"{parent}__zone__name",
                f"{parent}__subgroup__name",
            ):
                extras.append(rel)

        for path in extras:
            if path not in fields:
                fields.append(path)
        return tuple(fields)

    # ── audit: readonly + collapsed fieldset ─────────────────────────────
    def _audit_fields_present(self) -> list[str]:
        return [f for f in AUDIT_FIELD_NAMES if self._admin_model_has_field(f)]

    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj) or [])
        for name in self._audit_fields_present():
            if name not in ro:
                ro.append(name)
        return tuple(ro)

    @staticmethod
    def _strip_audit_from_fields(fields, audit_set: set[str]):
        if not fields:
            return fields
        out = []
        for item in fields:
            if isinstance(item, (list, tuple)):
                inner = tuple(x for x in item if x not in audit_set)
                if inner:
                    out.append(inner)
            elif item not in audit_set:
                out.append(item)
        return tuple(out)

    def get_fieldsets(self, request, obj=None):
        audit = self._audit_fields_present()
        fieldsets = super().get_fieldsets(request, obj)
        if not audit:
            return fieldsets

        audit_set = set(audit)
        cleaned = []
        for name, opts in fieldsets:
            opts = dict(opts)
            if "fields" in opts:
                opts["fields"] = self._strip_audit_from_fields(
                    opts["fields"], audit_set
                )
            # Keep fieldset even if empty only when it had no fields key
            if opts.get("fields") == ():
                continue
            cleaned.append((name, opts))

        # Pull any existing Audit-like section, merge fields, always place last.
        audit_names = {"audit", "audit trail", "notes & audit"}
        other = []
        audit_fields = list(audit)
        for name, opts in cleaned:
            if (name or "").lower() in audit_names:
                existing = list(opts.get("fields") or ())
                for f in existing:
                    if f not in audit_fields:
                        audit_fields.append(f)
                continue
            other.append((name, opts))

        other.append(
            (
                _("Audit"),
                {
                    "classes": ("collapse",),
                    "fields": tuple(audit_fields),
                },
            )
        )
        return other

    def save_model(self, request, obj, form, change):
        user = getattr(request, "user", None)
        if user is not None and getattr(user, "is_authenticated", False):
            if hasattr(obj, "modified_by_id"):
                obj.modified_by = user
            if (
                not change
                and hasattr(obj, "created_by_id")
                and not getattr(obj, "created_by_id", None)
            ):
                obj.created_by = user
        super().save_model(request, obj, form, change)


# ---------------------------------------------------------------------------
# SVG Sanitization (Security)
# ---------------------------------------------------------------------------
def sanitize_svg(svg_code: str) -> str:
    """Sanitize SVG content to prevent XSS attacks."""
    if not svg_code:
        return svg_code

    # Early rejection of dangerous content
    if "javascript:" in svg_code.lower() or "<script" in svg_code.lower():
        raise ValueError("Potentially unsafe SVG detected.")

    allowed_tags = {
        "svg", "g", "path", "circle", "rect", "line", "polyline",
        "polygon", "text", "defs", "use", "title", "desc"
    }

    allowed_attributes = {
        "*": ["style", "class", "id", "fill", "stroke", "transform", "viewBox"],
        "svg": ["width", "height", "viewBox", "xmlns", "xmlns:xlink"],
        "path": ["d", "fill"],
        "circle": ["cx", "cy", "r"],
        "rect": ["x", "y", "width", "height", "rx", "ry"],
        "line": ["x1", "y1", "x2", "y2"],
        "polygon": ["points"],
        "polyline": ["points"],
        "text": ["x", "y", "font-size", "text-anchor", "dominant-baseline"],
        "use": ["xlink:href"],
    }

    cleaned = bleach.clean(
        svg_code,
        tags=allowed_tags,
        attributes=allowed_attributes,
        strip=True,
    )
    return cleaned.strip()


# ---------------------------------------------------------------------------
# Cache Invalidation
# ---------------------------------------------------------------------------
def invalidate_user_access_cache(user):
    """Invalidate user's access cache (organizations & branches)."""
    if not user or not hasattr(user, "pk"):
        return

    try:
        cache.delete_many([
            f"user_{user.pk}_branches_dict",
            f"user_{user.pk}_orgs_managed",
        ])
        # Clear cached_property cache
        for key in ("branches_dict", "organizations_managed"):
            user.__dict__.pop(key, None)
    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to invalidate cache for user %s: %s", user.pk, e)


def invalidate_users_access_cache(users_qs):
    """Bulk invalidate cache for multiple users."""
    for user in users_qs.only("pk").iterator():
        invalidate_user_access_cache(user)


# ---------------------------------------------------------------------------
# Legacy / Dynamic Form Helpers (Kept for backwards compatibility if needed)
# ---------------------------------------------------------------------------
def usermodel_add_form(model, additional_fields):
    """Dynamically extend User add form fieldsets."""
    for position, field_name in additional_fields:
        # Add form fieldsets
        fieldsets = model.add_form.Meta.fieldsets[0][1]["fields"][:]
        model.add_form.Meta.fieldsets[0][1]["fields"] = (
            fieldsets[:position] + [field_name] + fieldsets[position:]
        )


def usermodel_change_form(model, additional_fields):
    """Dynamically extend User change form fieldsets."""
    for position, field_name in additional_fields:
        fieldsets = model.fieldsets[1][1]["fields"][:]
        model.fieldsets[1][1]["fields"] = (
            fieldsets[:position] + [field_name] + fieldsets[position:]
        )


def usermodel_list_and_search(model, additional_fields):
    """Dynamically extend list_display and search_fields."""
    for position, field_name in additional_fields:
        displays = model.list_display[:]
        model.list_display = displays[:position] + [field_name] + displays[position:]
        model.search_fields += (field_name,)


