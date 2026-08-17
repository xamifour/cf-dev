# cf-dev/cf_src/appsinn/cf_operations/forms.py

"""Admin forms that use Django's AutocompleteSelect (Select2 + AJAX)."""

from __future__ import annotations

from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import AutocompleteSelect
from django.utils.translation import gettext_lazy as _

from cf_people.models import SubBranch, Zone
from cf_users.models import Branch, Organization

from .models import AttendanceRecord, Event, EventSession


def _autocomplete(field, placeholder="", required=False):
    widget = AutocompleteSelect(
        field,
        admin.site,
        attrs={"data-placeholder": placeholder} if placeholder else None,
    )
    widget.is_required = required
    return widget


class AttendanceReportScopeForm(forms.Form):
    """Scope fields on Generate attendance report — Django admin autocomplete."""

    organization = forms.ModelChoiceField(
        queryset=Organization.objects.none(),
        required=False,
        label=_("Organisation"),
        widget=_autocomplete(
            Branch._meta.get_field("organization"),
            placeholder=_("All organisations"),
        ),
    )
    branch = forms.ModelChoiceField(
        queryset=Branch.objects.none(),
        required=False,
        label=_("Branch"),
        widget=_autocomplete(
            AttendanceRecord._meta.get_field("branch"),
            placeholder=_("All (in your scope)"),
        ),
    )
    event = forms.ModelChoiceField(
        queryset=Event.objects.none(),
        required=False,
        label=_("Event"),
        widget=_autocomplete(
            AttendanceRecord._meta.get_field("event"),
            placeholder=_("All events"),
        ),
    )
    session = forms.ModelChoiceField(
        queryset=EventSession.objects.none(),
        required=False,
        label=_("Session"),
        widget=_autocomplete(
            AttendanceRecord._meta.get_field("session"),
            placeholder=_("All sessions"),
        ),
    )
    zone = forms.ModelChoiceField(
        queryset=Zone.objects.none(),
        required=False,
        label=_("Zone"),
        widget=_autocomplete(
            AttendanceRecord._meta.get_field("zone"),
            placeholder=_("All zones"),
        ),
    )
    subgroup = forms.ModelChoiceField(
        queryset=SubBranch.objects.none(),
        required=False,
        label=_("Sub group"),
        widget=_autocomplete(
            AttendanceRecord._meta.get_field("subgroup"),
            placeholder=_("All sub groups"),
        ),
    )
    week = forms.TypedChoiceField(
        required=False,
        label=_("Week (sheet column)"),
        coerce=lambda v: int(v) if str(v).isdigit() else "",
        empty_value="",
        choices=(),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        org_qs = Organization.objects.all()
        branch_qs = Branch.objects.all()
        event_qs = Event.objects.all()
        session_qs = EventSession.objects.all()
        zone_qs = Zone.objects.all()
        subgroup_qs = SubBranch.objects.all()
        if user is not None:
            org_qs = org_qs.for_user(user)
            branch_qs = branch_qs.for_user(user)
            event_qs = event_qs.for_user(user)
            session_qs = session_qs.for_user(user)
            zone_qs = zone_qs.for_user(user)
            subgroup_qs = subgroup_qs.for_user(user)
        self.fields["organization"].queryset = org_qs
        self.fields["branch"].queryset = branch_qs.select_related("organization")
        self.fields["event"].queryset = event_qs.select_related("branch")
        self.fields["session"].queryset = session_qs.select_related("event", "branch")
        self.fields["zone"].queryset = zone_qs.select_related("branch")
        self.fields["subgroup"].queryset = subgroup_qs.select_related("zone", "branch")
        week_choices = [("", _("All weeks"))]
        for val, label in AttendanceRecord.WEEK_CHOICES:
            week_choices.append((val, _("Week %(n)s") % {"n": label}))
        self.fields["week"].choices = week_choices
        self.fields["week"].widget.attrs.update(
            {
                "class": "cf-select2",
                "data-placeholder": str(_("All weeks")),
            }
        )


class AttendanceImportForm(forms.Form):
    """Import target fields — Django admin autocomplete."""

    branch = forms.ModelChoiceField(
        queryset=Branch.objects.none(),
        required=True,
        label=_("Branch"),
        widget=_autocomplete(
            AttendanceRecord._meta.get_field("branch"),
            placeholder=_("Select a branch…"),
            required=True,
        ),
    )
    event = forms.ModelChoiceField(
        queryset=Event.objects.none(),
        required=False,
        label=_("Event"),
        widget=_autocomplete(
            AttendanceRecord._meta.get_field("event"),
            placeholder=_("Create from sheet title"),
        ),
    )
    excel_file = forms.FileField(
        required=True,
        label=_("Excel file"),
        widget=forms.ClearableFileInput(
            attrs={
                "class": "cf-file-input",
                "accept": ".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            }
        ),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        branch_qs = Branch.objects.all()
        event_qs = Event.objects.all()
        if user is not None:
            branch_qs = branch_qs.for_user(user)
            event_qs = event_qs.for_user(user)
        self.fields["branch"].queryset = branch_qs.select_related("organization")
        self.fields["event"].queryset = event_qs.select_related("branch")
        self.fields["event"].help_text = _(
            "Leave empty to create a new event from the report title on the sheet."
        )
