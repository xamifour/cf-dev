# cf-dev/cf_src/appsinn/cf_people/forms.py

"""Forms for people admin (zones / sub groups)."""

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import SubBranch


# Current group types offered in UI (legacy SETTLITE still valid in DB).
SUBGROUP_TYPE_CHOICES = [
    ("CELL", _("Cell Group")),
    ("SATELLITE", _("Satellite Fellowship")),
]


def _normalize_group_type(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return "CELL"
    if value == "SETTLITE":
        return "SATELLITE"
    if value == "ZONE":
        return "CELL"
    allowed = {c[0] for c in SUBGROUP_TYPE_CHOICES}
    if value not in allowed:
        raise forms.ValidationError(
            _("Select Cell Group or Satellite Fellowship."),
            code="invalid_choice",
        )
    return value


class SubBranchAdminForm(forms.ModelForm):
    """
    Standalone sub-group admin form.

    Branch is never chosen manually — it is always copied from the zone.
    """

    class Meta:
        model = SubBranch
        fields = (
            "zone",
            "name",
            "group_type",
            "leader",
            "is_active",
            "description",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "group_type" in self.fields:
            self.fields["group_type"].choices = SUBGROUP_TYPE_CHOICES
            self.fields["group_type"].required = True
            if not self.is_bound and not self.initial.get("group_type"):
                self.initial["group_type"] = "CELL"
                self.fields["group_type"].initial = "CELL"
        if self.instance and self.instance.zone_id and not self.instance.branch_id:
            self.instance.branch_id = self.instance.zone.branch_id

    def clean_group_type(self):
        return _normalize_group_type(self.cleaned_data.get("group_type"))

    def clean(self):
        cleaned = super().clean()
        zone = cleaned.get("zone") or getattr(self.instance, "zone", None)
        if zone is not None:
            cleaned["branch"] = zone.branch
            self.instance.branch = zone.branch
            self.instance.zone = zone
        elif not getattr(self.instance, "zone_id", None):
            raise forms.ValidationError(
                {
                    "zone": _(
                        "Select a zone. The sub group branch is taken from the zone."
                    )
                }
            )
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        if obj.zone_id:
            obj.branch_id = obj.zone.branch_id
        if commit:
            obj.save()
            self.save_m2m()
        return obj


class SubBranchInlineForm(forms.ModelForm):
    """
    Inline under Zone — zone/branch come from the parent zone, not the form.
    """

    class Meta:
        model = SubBranch
        fields = ("name", "group_type", "leader", "is_active")

    def __init__(self, *args, **kwargs):
        data = kwargs.get("data")
        if data is not None:
            data = data.copy()
            # Empty/missing group_type → CELL before ChoiceField validates.
            if not (data.get("group_type") or "").strip():
                # formset prefixes fields like "sub_groups-0-group_type"
                # Only rewrite non-prefixed key when present; formset uses prefix.
                pass
            kwargs["data"] = data
        super().__init__(*args, **kwargs)
        # After super(), rewrite prefixed group_type if empty.
        if self.is_bound and self.prefix:
            key = f"{self.prefix}-group_type"
            if key in self.data and not (self.data.get(key) or "").strip():
                mutable = self.data.copy()
                mutable[key] = "CELL"
                self.data = mutable
        elif self.is_bound and not (self.data.get("group_type") or "").strip():
            mutable = self.data.copy()
            mutable["group_type"] = "CELL"
            self.data = mutable

        self.fields["group_type"].choices = SUBGROUP_TYPE_CHOICES
        self.fields["group_type"].required = False  # cleaned to CELL if empty
        if not self.is_bound and not self.initial.get("group_type"):
            self.initial["group_type"] = "CELL"
            self.fields["group_type"].initial = "CELL"
        self.fields["leader"].required = False

    def clean_group_type(self):
        return _normalize_group_type(self.cleaned_data.get("group_type"))

    def save(self, commit=True):
        obj = super().save(commit=False)
        # Parent formset sets zone before save_new; branch follows zone.
        zone = getattr(obj, "zone", None)
        if zone is not None and zone.pk:
            obj.branch_id = zone.branch_id
        if commit:
            obj.save()
            self.save_m2m()
        return obj
