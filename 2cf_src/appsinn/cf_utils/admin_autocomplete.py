# cf-dev/cf_src/appsinn/cf_utils/admin_autocomplete.py

"""
Django admin autocomplete helpers.

Uses the built-in AutocompleteSelect protocol (Select2 + /admin/autocomplete/)
so custom pages and changelist filters match ModelAdmin.autocomplete_fields.
"""

from __future__ import annotations

from django.contrib import admin
from django.contrib.admin.exceptions import NotRegistered
from django.contrib.admin.filters import RelatedFieldListFilter
from django.contrib.admin.widgets import AutocompleteSelect
from django.db.models.fields.related import RelatedField


def autocomplete_media():
    """Select2 + Django autocomplete.js (same stack as autocomplete_fields)."""
    from django import forms
    from django.conf import settings

    extra = "" if settings.DEBUG else ".min"
    return forms.Media(
        js=(
            f"admin/js/vendor/jquery/jquery{extra}.js",
            f"admin/js/vendor/select2/select2.full{extra}.js",
            "admin/js/jquery.init.js",
            "admin/js/autocomplete.js",
            "cf_utils/admin_theme/js/admin_autocomplete.js",
        ),
        css={
            "screen": (
                f"admin/css/vendor/select2/select2{extra}.css",
                "admin/css/autocomplete.css",
            ),
        },
    )


def autocomplete_widget(field, admin_site=None, attrs=None, required=False):
    """AutocompleteSelect for a ForeignKey / ManyToMany field."""
    site = admin_site or admin.site
    widget = AutocompleteSelect(field, site, attrs=attrs)
    widget.is_required = required
    return widget


class AutocompleteRelatedFieldListFilter(RelatedFieldListFilter):
    """
    Related-field changelist filter that searches via /admin/autocomplete/.

    Falls back to Django's stock related filter when the target ModelAdmin
    has no ``search_fields`` (autocomplete would 404).
    """

    def __init__(self, field, request, params, model, model_admin, field_path):
        self.use_autocomplete = self._can_autocomplete(field, request, model_admin)
        super().__init__(field, request, params, model, model_admin, field_path)
        if self.use_autocomplete:
            self.template = "admin/cf_utils/autocomplete_filter.html"
            self.lookup_choices = self.field_choices(field, request, model_admin)

    @staticmethod
    def _can_autocomplete(field, request, model_admin) -> bool:
        remote = getattr(field, "remote_field", None)
        if remote is None or getattr(remote, "model", None) is None:
            return False
        try:
            related_admin = model_admin.admin_site.get_model_admin(remote.model)
        except (NotRegistered, AttributeError):
            return False
        try:
            return bool(related_admin.get_search_fields(request))
        except Exception:
            return False

    def has_output(self):
        if self.use_autocomplete:
            return True
        return super().has_output()

    def field_choices(self, field, request, model_admin):
        if not getattr(self, "use_autocomplete", False):
            return super().field_choices(field, request, model_admin)
        vals = self.lookup_val
        if not vals:
            return []
        if not isinstance(vals, (list, tuple)):
            vals = [vals]
        pks = [v for v in vals if v not in (None, "")]
        if not pks:
            return []
        rel = field.remote_field.model
        objs = rel.objects.filter(pk__in=pks)
        return [(obj.pk, str(obj)) for obj in objs]

    def autocomplete_config(self) -> dict[str, str]:
        selected_pk = ""
        selected_label = ""
        if self.lookup_choices:
            selected_pk = str(self.lookup_choices[0][0])
            selected_label = str(self.lookup_choices[0][1])
        return {
            "app_label": self.field.model._meta.app_label,
            "model_name": self.field.model._meta.model_name,
            "field_name": self.field.name,
            "param": self.lookup_kwarg,
            "remove": ",".join(
                p for p in (self.lookup_kwarg, self.lookup_kwarg_isnull) if p
            ),
            "selected_pk": selected_pk,
            "selected_label": selected_label,
        }


def _is_related_field(field) -> bool:
    if isinstance(field, RelatedField):
        return True
    return getattr(field, "remote_field", None) is not None


_FILTERS_REGISTERED = False


def register_autocomplete_list_filters() -> None:
    """Prefer AJAX autocomplete for every related changelist filter."""
    global _FILTERS_REGISTERED
    if _FILTERS_REGISTERED:
        return
    from django.contrib.admin import FieldListFilter

    FieldListFilter.register(
        _is_related_field,
        AutocompleteRelatedFieldListFilter,
        take_priority=True,
    )
    _FILTERS_REGISTERED = True
