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


class BaseAdmin(BaseModelAdmin):
    """
    Base admin class with common settings.

    Changelists prefer most-recently-modified first when the model has
    ``modified_at``; otherwise fall back to model ``Meta.ordering``.
    Subclasses may still set ``ordering`` explicitly.

    Audit fields (``created_by`` / ``modified_by``) are stamped via
    ``AuditUserMiddleware`` + ``AuditMixin.save``; ``save_model`` also sets
    them explicitly as a safety net.
    """

    history_latest_first = True

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


