# cf-dev/cf_src/appsinn/cf_operations/admin.py

"""Admin registrations for operations domain models."""

from django.contrib import admin, messages
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _

from cf_users.multitenancy import MultitenantAdminMixin, MultitenantBranchFilter
from cf_users.utils import BaseAdmin

from .attendance_export import export_sheet_pdf, export_sheet_xlsx
from .attendance_import import import_attendance_from_excel
from .attendance_report import (
    build_sheet_from_records,
    format_report_date,
    resolve_sheet_header,
)
from .forms import AttendanceImportForm, AttendanceReportScopeForm
from .models import (
    AttendanceRecord,
    AttendanceSeat,
    Document,
    DocumentCategory,
    Event,
    EventSession,
    Sermon,
)


# ---------------------------------------------------------------------------
# Events, sessions & sermons
# ---------------------------------------------------------------------------
class EventSessionInline(admin.TabularInline):
    model = EventSession
    extra = 1
    fields = (
        "name",
        "sort_order",
        "start_day",
        "start_time",
        "end_day",
        "end_time",
        "is_active",
        "branch",
    )
    readonly_fields = ("branch",)
    show_change_link = True
    ordering = ("sort_order", "start_day", "start_time", "name")


@admin.register(Event)
class EventAdmin(MultitenantAdminMixin, BaseAdmin):
    list_display = (
        "title",
        "event_type",
        "branch",
        "visibility",
        "start_time",
        "end_time",
        "recurrence",
    )
    list_filter = (MultitenantBranchFilter, "event_type", "visibility", "recurrence")
    search_fields = ("title", "description")
    autocomplete_fields = ("branch",)
    inlines = [EventSessionInline]
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "branch",
                    "event_type",
                    "title",
                    "description",
                    "visibility",
                )
            },
        ),
        (
            _("Schedule"),
            {"fields": ("start_time", "end_time", "recurrence")},
        ),
    )

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for obj in formset.deleted_objects:
            obj.delete()
        event = form.instance
        for instance in instances:
            if isinstance(instance, EventSession):
                instance.event = event
                instance.branch = event.branch
            instance.save()
        formset.save_m2m()


@admin.register(EventSession)
class EventSessionAdmin(MultitenantAdminMixin, BaseAdmin):
    multitenant_shared_relations = ["event"]
    list_display = (
        "name",
        "event",
        "branch",
        "start_day",
        "start_time",
        "end_day",
        "end_time",
        "check_in_start",
        "check_in_end",
        "is_active",
        "sort_order",
    )
    list_filter = (MultitenantBranchFilter, "is_active", "start_day")
    search_fields = ("name", "event__title", "description")
    autocomplete_fields = ("event", "branch")
    fieldsets = (
        (
            None,
            {
                "fields": ("event", "branch", "name", "sort_order", "is_active"),
                "description": _(
                    "A session is a named part of an event (e.g. 1st service). "
                    "Branch is taken from the event on save."
                ),
            },
        ),
        (
            _("Session schedule"),
            {
                "fields": (
                    "start_day",
                    "start_time",
                    "end_day",
                    "end_time",
                    "description",
                ),
                "description": _(
                    "Weekday + clock time (e.g. Sunday 07:00–09:00 for 1st service, "
                    "Sunday 10:00–12:00 for 2nd service)."
                ),
            },
        ),
        (
            _("Check-in window"),
            {
                "classes": ("collapse",),
                "fields": ("check_in_start", "check_in_end"),
                "description": _(
                    "Optional absolute date/time window for attendance capture."
                ),
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        if obj.event_id:
            obj.branch = obj.event.branch
        super().save_model(request, obj, form, change)


@admin.register(Sermon)
class SermonAdmin(MultitenantAdminMixin, BaseAdmin):
    multitenant_shared_relations = ["event", "speaker"]
    list_display = (
        "title",
        "speaker_label",
        "branch",
        "visibility",
        "event",
        "scripture_reference",
    )
    list_filter = (MultitenantBranchFilter, "visibility")
    search_fields = (
        "title",
        "scripture_reference",
        "guest_speaker_name",
        "guest_speaker_church",
        "speaker__user__first_name",
        "speaker__user__last_name",
    )
    autocomplete_fields = ("branch", "event", "speaker")
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "branch",
                    "event",
                    "title",
                    "scripture_reference",
                    "visibility",
                )
            },
        ),
        (
            _("Speaker"),
            {
                "description": _(
                    "A sermon may be preached by a registered member or by a guest "
                    "who is not a member of this organisation."
                ),
                "fields": (
                    "speaker",
                    "guest_speaker_name",
                    "guest_speaker_title",
                    "guest_speaker_church",
                ),
            },
        ),
        (
            _("Media & notes"),
            {
                "classes": ("collapse",),
                "fields": ("audio_url", "video_url", "notes"),
            },
        ),
    )

    @admin.display(description=_("speaker"))
    def speaker_label(self, obj):
        return obj.get_speaker_display()


# ---------------------------------------------------------------------------
# Attendance records (source of truth) + on-the-fly reports
# ---------------------------------------------------------------------------
class AttendanceSeatInline(admin.StackedInline):
    """
    Headcounts (MA/FA/MC/FC/…) for this attendance record.

    Shown on the Attendance record add/change form. Optional — leave blank
    if you only need the centre row without counts yet.
    """

    model = AttendanceSeat
    # Always show one seat form so MA/FA fields are visible (not hidden
    # behind “Add another attendance seat”).
    extra = 1
    max_num = 1
    verbose_name = _("attendance seat (MA / FA / MC / FC …)")
    verbose_name_plural = _("attendance seat (MA / FA / MC / FC …)")
    fields = (
        "male_adults",
        "female_adults",
        "male_children",
        "female_children",
        "total",
        "new_converts",
        "first_timers",
        "testimonies",
    )
    readonly_fields = ("total",)


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(MultitenantAdminMixin, BaseAdmin):
    """
    Source of truth for attendance.

    Scoped by Event + optional session / zone / sub group. Optional ``week``
    only labels the Excel preview column — weeks are not pre-populated.
    Excel-style sheets are generated on the fly (Generate report).
    """

    multitenant_shared_relations = [
        "event",
        "session",
        "zone",
        "subgroup",
    ]
    list_display = (
        "code",
        "event",
        "session",
        "week",
        "month",
        "attendance_at",
        "centre_name",
        "leader",
        "zone",
        "subgroup",
        "branch",
    )
    list_filter = (
        MultitenantBranchFilter,
        "event",
        "week",
        "month",
        "attendance_at",
        "zone",
    )
    search_fields = (
        "code",
        "centre_name",
        "leader",
        "address",
        "phone_number",
        "location_provider",
        "event__title",
        "session__name",
        "zone__name",
        "subgroup__name",
    )
    autocomplete_fields = (
        "event",
        "session",
        "branch",
        "zone",
        "subgroup",
    )
    readonly_fields = (
        "created_at",
        "modified_at",
        "created_by",
        "modified_by",
    )
    inlines = [AttendanceSeatInline]
    ordering = ("-modified_at", "code")
    change_list_template = "admin/cf_operations/attendancerecord/change_list.html"
    date_hierarchy = "attendance_at"
    fieldsets = (
        (
            _("Scope"),
            {
                "fields": (
                    "event",
                    "session",
                    "branch",
                    "zone",
                    "subgroup",
                    "week",
                    "month",
                    "attendance_at",
                ),
                "description": _(
                    "Attendance is for an Event (optional session) under a Branch. "
                    "Optionally scope to Zone and/or Sub group. "
                    "Optional week (1–5) maps this record into that column on the "
                    "Excel-style preview. Optional month and date/time describe "
                    "when the attendance happened. "
                    "Use “Generate report” on the list page for the sheet."
                ),
            },
        ),
        (
            _("Centre / sheet row (overrides)"),
            {
                "fields": (
                    "fill_from_scope",
                    "code",
                    "centre_name",
                    "leader",
                    "address",
                    "phone_number",
                    "location_provider",
                ),
                "description": _(
                    "These fields override scope defaults for the sheet. "
                    "Leave blank to use: sub group (if linked), else zone, "
                    "else branch, else organisation. "
                    "Tick “fill from scope” and save to copy those values into "
                    "the fields (code, centre name, leader, address, phone of "
                    "the scope leader, location provider)."
                ),
            },
        ),
        (
            _("Audit"),
            {
                "classes": ("collapse",),
                "fields": (
                    "created_at",
                    "modified_at",
                    "created_by",
                    "modified_by",
                ),
            },
        ),
    )

    def get_urls(self):
        info = self.model._meta.app_label, self.model._meta.model_name
        custom = [
            path(
                "generate-report/",
                self.admin_site.admin_view(self.generate_report_view),
                name="%s_%s_generate_report" % info,
            ),
            path(
                "import-excel/",
                self.admin_site.admin_view(self.import_excel_view),
                name="%s_%s_import_excel" % info,
            ),
        ]
        return custom + super().get_urls()

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["generate_report_url"] = reverse(
            "admin:cf_operations_attendancerecord_generate_report"
        )
        extra_context["import_excel_url"] = reverse(
            "admin:cf_operations_attendancerecord_import_excel"
        )
        return super().changelist_view(request, extra_context=extra_context)

    def generate_report_view(self, request):
        """Build Excel-layout sheet live from filtered attendance records."""
        from calendar import month_name
        from datetime import datetime

        from cf_people.models import SubBranch, Zone
        from cf_users.models import Branch, Organization

        scope_form = AttendanceReportScopeForm(request.GET, user=request.user)
        scope_form.is_valid()
        cleaned = scope_form.cleaned_data

        def _scope_pk(name):
            obj = cleaned.get(name)
            if obj is None or obj == "":
                return (request.GET.get(name) or "").strip()
            return str(getattr(obj, "pk", obj))

        filters = {
            "organization": _scope_pk("organization"),
            "branch": _scope_pk("branch"),
            "event": _scope_pk("event"),
            "session": _scope_pk("session"),
            "zone": _scope_pk("zone"),
            "subgroup": _scope_pk("subgroup"),
            "week": _scope_pk("week"),
            "month": (request.GET.get("month") or "").strip(),
            "year": (request.GET.get("year") or "").strip(),
            "date": (request.GET.get("date") or "").strip(),
            "date_from": (request.GET.get("date_from") or "").strip(),
            "date_to": (request.GET.get("date_to") or "").strip(),
            "weekday": (request.GET.get("weekday") or "").strip(),
            "location_provider": (request.GET.get("location_provider") or "").strip(),
        }
        qs = self.get_queryset(request).select_related(
            "branch",
            "branch__organization",
            "branch__organization__leader",
            "branch__organization__leader__user",
            "branch__leader",
            "branch__leader__user",
            "event",
            "session",
            "zone",
            "zone__leader",
            "zone__leader__user",
            "subgroup",
            "subgroup__leader",
            "subgroup__leader__user",
            "seat",
        )
        if filters["organization"]:
            qs = qs.filter(branch__organization_id=filters["organization"])
        if filters["branch"]:
            qs = qs.filter(branch_id=filters["branch"])
        if filters["event"]:
            qs = qs.filter(event_id=filters["event"])
        if filters["session"]:
            qs = qs.filter(session_id=filters["session"])
        if filters["zone"]:
            qs = qs.filter(zone_id=filters["zone"])
        if filters["subgroup"]:
            qs = qs.filter(subgroup_id=filters["subgroup"])
        if filters["week"]:
            try:
                qs = qs.filter(week=int(filters["week"]))
            except ValueError:
                pass
        if filters["month"]:
            try:
                qs = qs.filter(month=int(filters["month"]))
            except ValueError:
                pass
        if filters["year"]:
            try:
                year = int(filters["year"])
                qs = qs.filter(attendance_at__year=year)
            except ValueError:
                pass
        if filters["date"]:
            try:
                day = datetime.strptime(filters["date"], "%Y-%m-%d").date()
                qs = qs.filter(attendance_at__date=day)
            except ValueError:
                pass
        if filters["date_from"]:
            try:
                start = datetime.strptime(filters["date_from"], "%Y-%m-%d").date()
                qs = qs.filter(attendance_at__date__gte=start)
            except ValueError:
                pass
        if filters["date_to"]:
            try:
                end = datetime.strptime(filters["date_to"], "%Y-%m-%d").date()
                qs = qs.filter(attendance_at__date__lte=end)
            except ValueError:
                pass
        if filters["weekday"]:
            # HTML 0=Mon … 6=Sun → Django week_day 1=Sun … 7=Sat
            try:
                html_wd = int(filters["weekday"])
                django_wd = ((html_wd + 1) % 7) + 1
                qs = qs.filter(attendance_at__week_day=django_wd)
            except ValueError:
                pass
        if filters["location_provider"]:
            qs = qs.filter(
                location_provider__icontains=filters["location_provider"]
            )

        active_filters = {k: v for k, v in filters.items() if v}
        generated = bool(active_filters) or request.GET.get("all") == "1"
        attendance_sheet = None
        filter_summary = ""

        org_obj = None
        if filters["organization"]:
            org_obj = (
                Organization.objects.for_user(request.user)
                .select_related("leader", "leader__user")
                .filter(pk=filters["organization"])
                .first()
            )
        branch_obj = None
        if filters["branch"]:
            branch_obj = (
                Branch.objects.for_user(request.user)
                .select_related(
                    "organization",
                    "organization__leader",
                    "organization__leader__user",
                    "leader",
                    "leader__user",
                )
                .filter(pk=filters["branch"])
                .first()
            )
        zone_obj = None
        if filters["zone"]:
            zone_obj = (
                Zone.objects.for_user(request.user)
                .select_related(
                    "branch",
                    "branch__organization",
                    "branch__organization__leader",
                    "branch__organization__leader__user",
                    "branch__leader",
                    "branch__leader__user",
                    "leader",
                    "leader__user",
                )
                .filter(pk=filters["zone"])
                .first()
            )
        subgroup_obj = None
        if filters["subgroup"]:
            subgroup_obj = (
                SubBranch.objects.for_user(request.user)
                .select_related(
                    "zone",
                    "zone__leader",
                    "zone__leader__user",
                    "branch",
                    "branch__organization",
                    "branch__organization__leader",
                    "branch__organization__leader__user",
                    "branch__leader",
                    "branch__leader__user",
                    "leader",
                    "leader__user",
                )
                .filter(pk=filters["subgroup"])
                .first()
            )
        # Organisation-only report: use the user's single org when none picked.
        if (
            org_obj is None
            and branch_obj is None
            and zone_obj is None
            and subgroup_obj is None
        ):
            user_orgs = list(
                Organization.objects.for_user(request.user)
                .select_related("leader", "leader__user")[:2]
            )
            if len(user_orgs) == 1:
                org_obj = user_orgs[0]

        header = resolve_sheet_header(
            organization=org_obj,
            branch=branch_obj,
            zone=zone_obj,
            subgroup=subgroup_obj,
            report_date=format_report_date(filters, qs if generated else []),
        )

        if generated:
            bits = []
            if filters["month"]:
                try:
                    bits.append(month_name[int(filters["month"])])
                except (ValueError, IndexError):
                    bits.append(f"month={filters['month']}")
            if filters["year"]:
                bits.append(filters["year"])
            if filters["date"]:
                bits.append(filters["date"])
            if filters["date_from"] or filters["date_to"]:
                bits.append(
                    f"{filters['date_from'] or '…'} → {filters['date_to'] or '…'}"
                )
            if filters["week"]:
                bits.append(f"Week {filters['week']}")
            if filters["weekday"]:
                wd_labels = [
                    _("Monday"),
                    _("Tuesday"),
                    _("Wednesday"),
                    _("Thursday"),
                    _("Friday"),
                    _("Saturday"),
                    _("Sunday"),
                ]
                try:
                    bits.append(str(wd_labels[int(filters["weekday"])]))
                except (ValueError, IndexError):
                    pass
            filter_summary = " · ".join(bits)
            attendance_sheet = build_sheet_from_records(
                qs,
                organization_name=header["organization_name"],
                branch_name=header["branch_name"],
                zone_name=header["zone_name"],
                subgroup_name=header["subgroup_name"],
                report_date=header["report_date"],
                show_zone=header["show_zone"],
                show_subgroup=header["show_subgroup"],
                header_leader_name=header["leader_name"],
                filter_summary=filter_summary,
                coordinator_name=header["leader_name"],
            )

            # File download (Excel / PDF) using the same filtered sheet.
            download = (request.GET.get("download") or "").strip().lower()
            if download in ("xlsx", "excel") and attendance_sheet is not None:
                from django.http import HttpResponse

                payload = export_sheet_xlsx(attendance_sheet)
                response = HttpResponse(
                    payload,
                    content_type=(
                        "application/vnd.openxmlformats-officedocument."
                        "spreadsheetml.sheet"
                    ),
                )
                response["Content-Disposition"] = (
                    'attachment; filename="attendance_report.xlsx"'
                )
                return response
            if download == "pdf" and attendance_sheet is not None:
                from django.http import HttpResponse

                payload = export_sheet_pdf(attendance_sheet)
                response = HttpResponse(payload, content_type="application/pdf")
                response["Content-Disposition"] = (
                    'attachment; filename="attendance_report.pdf"'
                )
                return response

        # Years present in scope (for year dropdown)
        year_values = (
            self.get_queryset(request)
            .exclude(attendance_at__isnull=True)
            .dates("attendance_at", "year", order="DESC")
        )
        years = [d.year for d in year_values]

        # Preserve query string for download links (without download param).
        qs_params = request.GET.copy()
        qs_params.pop("download", None)
        download_query = qs_params.urlencode()

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": _("Generate attendance report"),
            "scope_form": scope_form,
            "filters": filters,
            "years": years,
            "month_choices": AttendanceRecord.MONTH_CHOICES,
            "week_choices": AttendanceRecord.WEEK_CHOICES,
            "weekday_choices": [
                (0, _("Monday")),
                (1, _("Tuesday")),
                (2, _("Wednesday")),
                (3, _("Thursday")),
                (4, _("Friday")),
                (5, _("Saturday")),
                (6, _("Sunday")),
            ],
            "generated": generated,
            "attendance_sheet": attendance_sheet,
            "download_query": download_query,
        }
        return render(
            request,
            "admin/cf_operations/attendancerecord/report.html",
            context,
        )

    def import_excel_view(self, request):
        """Import Excel rows as attendance records; report is generated later."""
        import_form = AttendanceImportForm(
            request.POST or None,
            request.FILES or None,
            user=request.user,
        )
        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            # Page heading comes from the template hero (avoid duplicate h1).
            "title": "",
            "import_form": import_form,
        }

        if request.method == "POST":
            if not import_form.is_valid():
                if not request.FILES.get("excel_file"):
                    messages.error(request, _("Please choose an Excel file (.xlsx)."))
                elif not import_form.cleaned_data.get("branch"):
                    messages.error(request, _("Select a branch."))
                else:
                    messages.error(request, _("Select a valid branch you can access."))
                return render(
                    request,
                    "admin/cf_operations/attendancerecord/import_excel.html",
                    context,
                )
            branch = import_form.cleaned_data["branch"]
            event = import_form.cleaned_data.get("event")
            upload = import_form.cleaned_data["excel_file"]
            if event is not None and event.branch_id != branch.pk:
                messages.error(
                    request,
                    _(
                        "Selected event was not found under that branch "
                        "(or you do not have access)."
                    ),
                )
                return render(
                    request,
                    "admin/cf_operations/attendancerecord/import_excel.html",
                    context,
                )

            try:
                result = import_attendance_from_excel(
                    branch=branch,
                    file_obj=upload,
                    event=event,
                    created_by=request.user,
                )
            except Exception as exc:  # noqa: BLE001
                messages.error(request, _("Import failed: %s") % exc)
                return render(
                    request,
                    "admin/cf_operations/attendancerecord/import_excel.html",
                    context,
                )

            for warning in result.warnings:
                messages.warning(request, warning)
            messages.success(
                request,
                _(
                    "Imported %(records)s attendance records "
                    "(%(seats)s with seat counts) for “%(title)s”. "
                    "Use Generate report to view the sheet."
                )
                % {
                    "records": result.records_created,
                    "seats": result.seats_created,
                    "title": result.report_title
                    or (result.event.title if result.event else ""),
                },
            )
            url = reverse("admin:cf_operations_attendancerecord_generate_report")
            if result.event is not None:
                url += f"?event={result.event.pk}&branch={branch.pk}"
            return redirect(url)

        return render(
            request,
            "admin/cf_operations/attendancerecord/import_excel.html",
            context,
        )

    def save_model(self, request, obj, form, change):
        if obj.session_id and not obj.event_id:
            obj.event = obj.session.event
        if obj.event_id and not obj.branch_id:
            obj.branch = obj.event.branch
        if obj.subgroup_id and not obj.zone_id:
            obj.zone = obj.subgroup.zone
        super().save_model(request, obj, form, change)


@admin.register(AttendanceSeat)
class AttendanceSeatAdmin(MultitenantAdminMixin, BaseAdmin):
    """
    Standalone list of seat headcounts (MA/FA/…).

    Prefer editing seats via the inline on Attendance record; this list is
    for browsing/searching seats across records.
    """

    multitenant_parent = "record"
    multitenant_shared_relations = ["record"]
    list_display = (
        "record",
        "male_adults",
        "female_adults",
        "male_children",
        "female_children",
        "total",
        "new_converts",
        "first_timers",
        "testimonies",
    )
    search_fields = (
        "record__centre_name",
        "record__event__title",
        "record__zone__name",
    )
    autocomplete_fields = ("record",)
    readonly_fields = ("total",)
    fieldsets = (
        (
            None,
            {
                "fields": ("record",),
                "description": _(
                    "Usually add/edit seats from the Attendance record page "
                    "(inline “attendance seat (MA / FA / MC / FC …)”)."
                ),
            },
        ),
        (
            _("Headcounts"),
            {
                "fields": (
                    "male_adults",
                    "female_adults",
                    "male_children",
                    "female_children",
                    "total",
                    "new_converts",
                    "first_timers",
                    "testimonies",
                )
            },
        ),
    )


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------
@admin.register(DocumentCategory)
class DocumentCategoryAdmin(MultitenantAdminMixin, BaseAdmin):
    list_display = ("name", "branch", "required_role_access")
    list_filter = (MultitenantBranchFilter,)
    search_fields = ("name",)
    autocomplete_fields = ("branch",)


@admin.register(Document)
class DocumentAdmin(MultitenantAdminMixin, BaseAdmin):
    multitenant_shared_relations = ["category"]
    list_display = ("title", "branch", "category", "is_confidential")
    list_filter = (MultitenantBranchFilter, "is_confidential")
    search_fields = ("title",)
    autocomplete_fields = ("branch", "category")
