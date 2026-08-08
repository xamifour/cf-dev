# cf-dev/cf_src/appsinn/cf_operations/base/models.py

"""
Operations base models: Events, Sermons, Zonal Attendance, Documents.
All models are abstract. Concrete implementations live in cf_operations.models.
"""

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from cf_users.mixins import AuditMixin, ValidateOrgBranchMixin


class VisibilityMixin(models.Model):
    """
    Platform visibility for content (events, sermons, etc.).

    PUBLIC — any platform user (and anonymous browse where allowed).
    ORGANIZATION — users with access to any branch of the owning organisation.
    BRANCH — only users with access to the owning branch.
    """

    VISIBILITY_PUBLIC = "PUBLIC"
    VISIBILITY_ORGANIZATION = "ORGANIZATION"
    VISIBILITY_BRANCH = "BRANCH"
    VISIBILITY_CHOICES = [
        (VISIBILITY_PUBLIC, _("Public (all platform users)")),
        (VISIBILITY_ORGANIZATION, _("Organisation only")),
        (VISIBILITY_BRANCH, _("Branch only")),
    ]

    visibility = models.CharField(
        _("visibility"),
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default=VISIBILITY_PUBLIC,
        db_index=True,
        help_text=_(
            "Public: anyone on the platform. "
            "Organisation only: all branches of this church. "
            "Branch only: only this branch's users."
        ),
    )

    class Meta:
        abstract = True


class AbstractEvent(AuditMixin, VisibilityMixin):
    """A church service, conference, outreach, or any scheduled gathering."""

    RECURRENCE_CHOICES = [
        ("NONE", _("One-off")),
        ("WEEKLY", _("Weekly")),
        ("MONTHLY", _("Monthly")),
        ("CUSTOM", _("Custom")),
    ]
    EVENT_TYPE_CHOICES = [
        ("SERVICE", _("Service")),
        ("CONFERENCE", _("Conference")),
        ("OUTREACH", _("Outreach")),
        ("CAMP", _("Camp")),
        ("TRAINING", _("Training")),
        ("MEETING", _("Meeting")),
        ("OTHER", _("Other")),
    ]

    branch = models.ForeignKey(
        "cf_users.Branch",
        on_delete=models.PROTECT,
        related_name="events",
        verbose_name=_("branch"),
    )
    event_type = models.CharField(
        _("event type"),
        max_length=20,
        choices=EVENT_TYPE_CHOICES,
        default="SERVICE",
        db_index=True,
    )
    title = models.CharField(_("title"), max_length=255)
    description = models.TextField(_("description"), blank=True)
    start_time = models.DateTimeField(
        _("start time"), db_index=True, null=True, blank=True
    )
    end_time = models.DateTimeField(_("end time"), null=True, blank=True)
    recurrence = models.CharField(
        _("recurrence"), max_length=10, choices=RECURRENCE_CHOICES, default="NONE"
    )

    class Meta:
        abstract = True
        ordering = ("-modified_at", "-start_time")

    def __str__(self) -> str:
        return self.title

    def clean(self) -> None:
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError(
                {"end_time": _("End time must be after the start time.")}
            )


class AbstractEventSession(AuditMixin, ValidateOrgBranchMixin):
    """
    A named session / occurrence under an Event.

    Examples: 1st service, 2nd service, youth service, morning check-in window.
    Attendance records may point at a session when an event has multiple parts.

    Session schedule uses weekday (Sunday–Saturday) + clock time so recurring
    services can be described without a calendar date. Check-in remains absolute
    datetimes for a specific capture window.
    """

    # Sunday-first week (common for church schedules).
    WEEKDAY_SUNDAY = "SUN"
    WEEKDAY_MONDAY = "MON"
    WEEKDAY_TUESDAY = "TUE"
    WEEKDAY_WEDNESDAY = "WED"
    WEEKDAY_THURSDAY = "THU"
    WEEKDAY_FRIDAY = "FRI"
    WEEKDAY_SATURDAY = "SAT"
    WEEKDAY_CHOICES = [
        (WEEKDAY_SUNDAY, _("Sunday")),
        (WEEKDAY_MONDAY, _("Monday")),
        (WEEKDAY_TUESDAY, _("Tuesday")),
        (WEEKDAY_WEDNESDAY, _("Wednesday")),
        (WEEKDAY_THURSDAY, _("Thursday")),
        (WEEKDAY_FRIDAY, _("Friday")),
        (WEEKDAY_SATURDAY, _("Saturday")),
    ]
    # Index used for ordering / same-week comparisons (Sunday = 0).
    WEEKDAY_INDEX = {
        WEEKDAY_SUNDAY: 0,
        WEEKDAY_MONDAY: 1,
        WEEKDAY_TUESDAY: 2,
        WEEKDAY_WEDNESDAY: 3,
        WEEKDAY_THURSDAY: 4,
        WEEKDAY_FRIDAY: 5,
        WEEKDAY_SATURDAY: 6,
    }

    event = models.ForeignKey(
        "cf_operations.Event",
        on_delete=models.CASCADE,
        related_name="sessions",
        verbose_name=_("event"),
    )
    branch = models.ForeignKey(
        "cf_users.Branch",
        on_delete=models.PROTECT,
        related_name="event_sessions",
        verbose_name=_("branch"),
        help_text=_("Usually the same as the event branch (set automatically)."),
    )
    name = models.CharField(
        _("session name"),
        max_length=150,
        help_text=_("e.g. 1st Service, 2nd Service, Youth, Check-in"),
    )
    description = models.TextField(_("description"), blank=True)
    start_day = models.CharField(
        _("start day"),
        max_length=3,
        choices=WEEKDAY_CHOICES,
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Weekday when this session begins (Sunday–Saturday)."),
    )
    start_time = models.TimeField(
        _("start time"),
        null=True,
        blank=True,
        help_text=_("Clock time when this session begins."),
    )
    end_day = models.CharField(
        _("end day"),
        max_length=3,
        choices=WEEKDAY_CHOICES,
        null=True,
        blank=True,
        help_text=_("Weekday when this session ends (Sunday–Saturday)."),
    )
    end_time = models.TimeField(
        _("end time"),
        null=True,
        blank=True,
        help_text=_("Clock time when this session ends."),
    )
    check_in_start = models.DateTimeField(
        _("check-in start"),
        null=True,
        blank=True,
        help_text=_("Optional. When check-in / attendance capture opens."),
    )
    check_in_end = models.DateTimeField(
        _("check-in end"),
        null=True,
        blank=True,
        help_text=_("Optional. When check-in / attendance capture closes."),
    )
    is_active = models.BooleanField(_("is active"), default=True, db_index=True)
    sort_order = models.PositiveSmallIntegerField(
        _("sort order"),
        default=0,
        help_text=_("Lower numbers appear first."),
    )

    class Meta:
        abstract = True
        ordering = ("event", "sort_order", "start_day", "start_time", "name")
        verbose_name = _("event session")
        verbose_name_plural = _("event sessions")

    def __str__(self) -> str:
        event_title = getattr(self.event, "title", None) or _("Event")
        return f"{event_title} · {self.name}"

    @classmethod
    def weekday_minutes(cls, day_code, clock_time):
        """
        Minutes from Sunday 00:00 for a weekday code + time.

        Returns None if either part is missing or the day code is unknown.
        """
        if not day_code or clock_time is None:
            return None
        day_idx = cls.WEEKDAY_INDEX.get(day_code)
        if day_idx is None:
            return None
        return (
            day_idx * 24 * 60
            + clock_time.hour * 60
            + clock_time.minute
            + clock_time.second / 60.0
        )

    @classmethod
    def weekday_code_from_date(cls, value):
        """Map a date/datetime to our Sunday-first weekday code."""
        from datetime import datetime as dt_cls

        if value is None:
            return None
        if isinstance(value, dt_cls):
            value = value.date()
        # Python: Monday=0 … Sunday=6 → our Sunday-first codes
        py_to_code = (
            cls.WEEKDAY_MONDAY,
            cls.WEEKDAY_TUESDAY,
            cls.WEEKDAY_WEDNESDAY,
            cls.WEEKDAY_THURSDAY,
            cls.WEEKDAY_FRIDAY,
            cls.WEEKDAY_SATURDAY,
            cls.WEEKDAY_SUNDAY,
        )
        return py_to_code[value.weekday()]

    def clean(self) -> None:
        if self.event_id:
            if self.event.branch_id and (
                not self.branch_id or self.branch_id != self.event.branch_id
            ):
                self.branch = self.event.branch
            self._validate_org_branch_relation("event")

        start_mins = self.weekday_minutes(self.start_day, self.start_time)
        end_mins = self.weekday_minutes(self.end_day, self.end_time)
        if start_mins is not None and end_mins is not None and start_mins >= end_mins:
            # Same-week ordering; overnight (e.g. Sat 22:00 → Sun 01:00) is allowed
            # only when end wraps past Sunday (end day earlier in week than start).
            wraps_week = self.WEEKDAY_INDEX.get(
                self.end_day, -1
            ) < self.WEEKDAY_INDEX.get(self.start_day, -1)
            if not wraps_week:
                raise ValidationError(
                    {
                        "end_time": _(
                            "Session end must be after session start "
                            "(or end on a later weekday)."
                        )
                    }
                )

        if (
            self.check_in_start
            and self.check_in_end
            and self.check_in_start >= self.check_in_end
        ):
            raise ValidationError(
                {"check_in_end": _("Check-in end must be after check-in start.")}
            )

    def save(self, *args, **kwargs):
        if self.event_id and self.event.branch_id:
            self.branch_id = self.event.branch_id
        super().save(*args, **kwargs)

    def is_check_in_open(self, at=None) -> bool:
        """True if ``at`` (default now) falls inside the check-in window."""
        from django.utils import timezone as dj_tz

        at = at or dj_tz.now()
        if self.check_in_start and at < self.check_in_start:
            return False
        if self.check_in_end and at > self.check_in_end:
            return False
        if self.check_in_start or self.check_in_end:
            return True

        # Fallback: open when ``at`` falls inside the weekly session window.
        start_mins = self.weekday_minutes(self.start_day, self.start_time)
        end_mins = self.weekday_minutes(self.end_day, self.end_time)
        if start_mins is None and end_mins is None:
            return True
        local = dj_tz.localtime(at)
        at_mins = self.weekday_minutes(
            self.weekday_code_from_date(local.date()), local.time()
        )
        if at_mins is None:
            return True
        if start_mins is not None and end_mins is not None:
            if start_mins <= end_mins:
                return start_mins <= at_mins <= end_mins
            # Wraps past Sunday (e.g. Sat night → Sun morning).
            return at_mins >= start_mins or at_mins <= end_mins
        if start_mins is not None and at_mins < start_mins:
            return False
        if end_mins is not None and at_mins > end_mins:
            return False
        return True


class AbstractSermon(AuditMixin, VisibilityMixin, ValidateOrgBranchMixin):
    """
    A sermon preached at an event.

    Speaker may be a church Member or a guest (non-member) speaker.
    """

    branch = models.ForeignKey(
        "cf_users.Branch",
        on_delete=models.PROTECT,
        related_name="sermons",
        verbose_name=_("branch"),
    )
    event = models.ForeignKey(
        "cf_operations.Event",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sermons",
        verbose_name=_("event"),
    )
    speaker = models.ForeignKey(
        "cf_people.Member",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sermons",
        verbose_name=_("member speaker"),
        help_text=_("Optional. Use when the preacher is a registered member."),
    )
    guest_speaker_name = models.CharField(
        _("guest speaker name"),
        max_length=255,
        blank=True,
        help_text=_("Use for guest speakers who are not members of this church."),
    )
    guest_speaker_title = models.CharField(
        _("guest speaker title"),
        max_length=150,
        blank=True,
        help_text=_("e.g. Pastor, Evangelist, Bishop."),
    )
    guest_speaker_church = models.CharField(
        _("guest speaker church / organisation"),
        max_length=255,
        blank=True,
    )
    title = models.CharField(_("title"), max_length=255)
    scripture_reference = models.CharField(
        _("scripture reference"),
        max_length=255,
        blank=True,
        help_text=_("e.g. John 3:16, Romans 8:28–30"),
    )
    audio_url = models.URLField(_("audio URL"), max_length=1000, blank=True)
    video_url = models.URLField(_("video URL"), max_length=1000, blank=True)
    notes = models.TextField(_("sermon notes"), blank=True)

    class Meta:
        abstract = True
        ordering = ("-modified_at",)

    def __str__(self) -> str:
        return f"{self.title} – {self.get_speaker_display()}"

    def get_speaker_display(self) -> str:
        if self.speaker_id:
            return str(self.speaker)
        parts = [self.guest_speaker_title, self.guest_speaker_name]
        label = " ".join(p for p in parts if p).strip()
        if self.guest_speaker_church:
            label = f"{label} ({self.guest_speaker_church})" if label else self.guest_speaker_church
        return label or str(_("Unknown speaker"))

    def clean(self) -> None:
        if self.event:
            self._validate_org_branch_relation("event")
        if self.speaker_id:
            self._validate_org_branch_relation("speaker")
        if not self.speaker_id and not (self.guest_speaker_name or "").strip():
            raise ValidationError(
                {
                    "guest_speaker_name": _(
                        "Provide a member speaker or a guest speaker name."
                    )
                }
            )


# ---------------------------------------------------------------------------
# Attendance (event-scoped; Excel multi-week layout is preview-only)
# ---------------------------------------------------------------------------


class AbstractAttendanceRecord(AuditMixin, ValidateOrgBranchMixin):
    """
    One attendance capture for an Event.

    Depends on: Event (required), optional Session / Zone / Sub group.
    Optional ``week`` (1–5) only labels which sheet column to use in the
    Excel-style preview — records are not pre-created for every week.
    Optional ``month`` / ``attendance_at`` label when the capture happened.
    Headcounts live on the related AttendanceSeat (0 or 1).
    """

    WEEK_CHOICES = [
        (1, _("1")),
        (2, _("2")),
        (3, _("3")),
        (4, _("4")),
        (5, _("5")),
    ]
    MONTH_CHOICES = [
        (1, _("January")),
        (2, _("February")),
        (3, _("March")),
        (4, _("April")),
        (5, _("May")),
        (6, _("June")),
        (7, _("July")),
        (8, _("August")),
        (9, _("September")),
        (10, _("October")),
        (11, _("November")),
        (12, _("December")),
    ]

    event = models.ForeignKey(
        "cf_operations.Event",
        on_delete=models.PROTECT,
        related_name="attendance_records",
        verbose_name=_("event"),
        help_text=_("The service, outreach, or gathering this attendance is for."),
        null=True,
        blank=False,
    )
    session = models.ForeignKey(
        "cf_operations.EventSession",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_records",
        verbose_name=_("event session"),
        help_text=_(
            "Optional. Which session of the event (e.g. 1st service, 2nd service)."
        ),
    )
    branch = models.ForeignKey(
        "cf_users.Branch",
        on_delete=models.PROTECT,
        related_name="attendance_records",
        verbose_name=_("branch"),
    )
    zone = models.ForeignKey(
        "cf_people.Zone",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_records",
        verbose_name=_("zone"),
        help_text=_("Optional. Zone under the branch where attendance was taken."),
    )
    subgroup = models.ForeignKey(
        "cf_people.SubBranch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_records",
        verbose_name=_("sub group"),
        help_text=_("Optional. Cell / satellite under the zone."),
    )
    week = models.PositiveSmallIntegerField(
        _("week"),
        choices=WEEK_CHOICES,
        null=True,
        blank=True,
        db_index=True,
        help_text=_(
            "Optional. Which week column (1–5) this record maps to on the "
            "Excel-style preview sheet."
        ),
    )
    month = models.PositiveSmallIntegerField(
        _("month"),
        choices=MONTH_CHOICES,
        null=True,
        blank=True,
        db_index=True,
        help_text=_(
            "Optional. Calendar month this attendance relates to "
            "(January–December)."
        ),
    )
    attendance_at = models.DateTimeField(
        _("attendance date/time"),
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Optional. When this attendance was taken."),
    )
    serial_number = models.PositiveIntegerField(_("S/N"), default=1)
    centre_name = models.CharField(
        _("centre name"),
        max_length=255,
        blank=True,
        help_text=_("Cell / centre name as on the sheet (if not linked to a sub group)."),
    )
    leader = models.ForeignKey(
        "cf_people.Member",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="led_attendance_records",
        verbose_name=_("leader"),
        help_text=_("Optional. Cell / centre leader (member)."),
    )
    location = models.CharField(_("location"), max_length=512, blank=True)
    location_provider = models.CharField(
        _("location provider"),
        max_length=255,
        blank=True,
        help_text=_("Optional. Who provided or hosts this location."),
    )
    contact = models.CharField(_("contact"), max_length=64, blank=True)

    class Meta:
        abstract = True
        ordering = ("-modified_at", "serial_number", "centre_name")

    def __str__(self) -> str:
        label = self.centre_name or (
            str(self.subgroup) if self.subgroup_id else ""
        ) or (str(self.zone) if self.zone_id else "")
        event_title = getattr(self.event, "title", None) or _("Event")
        week_bit = f" · W{self.week}" if self.week else ""
        if label:
            return f"{event_title} · {label}{week_bit}"
        return f"{event_title} · {self.serial_number}{week_bit}"

    def get_leader_display(self) -> str:
        if self.leader_id:
            return str(self.leader)
        return ""

    def clean(self) -> None:
        if self.event_id and self.branch_id:
            if self.event.branch_id != self.branch_id:
                raise ValidationError(
                    {
                        "event": _(
                            "Event must belong to the same branch as this attendance record."
                        )
                    }
                )
        if self.session_id:
            if self.event_id and self.session.event_id != self.event_id:
                raise ValidationError(
                    {
                        "session": _(
                            "Session must belong to the same event as this record."
                        )
                    }
                )
            if not self.event_id:
                self.event = self.session.event
            if self.session.branch_id and self.branch_id != self.session.branch_id:
                raise ValidationError(
                    {
                        "session": _(
                            "Session branch must match the attendance record branch."
                        )
                    }
                )
        if self.zone_id:
            if self.zone.branch_id != self.branch_id:
                raise ValidationError(
                    {"zone": _("Zone must belong to the same branch.")}
                )
            self._validate_org_branch_relation("zone")
        if self.subgroup_id:
            if self.subgroup.branch_id != self.branch_id:
                raise ValidationError(
                    {"subgroup": _("Sub group must belong to the same branch.")}
                )
            if self.zone_id and self.subgroup.zone_id != self.zone_id:
                raise ValidationError(
                    {
                        "subgroup": _(
                            "Sub group must belong to the selected zone."
                        )
                    }
                )
            self._validate_org_branch_relation("subgroup")
        if self.leader_id:
            if self.branch_id and self.leader.branch_id != self.branch_id:
                raise ValidationError(
                    {"leader": _("Leader must belong to the same branch.")}
                )
            self._validate_org_branch_relation("leader")
        if self.subgroup_id and not (self.centre_name or "").strip():
            self.centre_name = self.subgroup.name
        # If month blank but attendance_at set, leave month for staff to set
        # (or they may set month without a precise datetime).

    def save(self, *args, **kwargs):
        if self.session_id and not self.event_id:
            self.event_id = self.session.event_id
        if self.event_id and not self.branch_id:
            self.branch_id = self.event.branch_id
        if self.subgroup_id and not self.zone_id:
            self.zone_id = self.subgroup.zone_id
        if self.subgroup_id and not (self.centre_name or "").strip():
            self.centre_name = self.subgroup.name
        super().save(*args, **kwargs)


class AbstractAttendanceSeat(models.Model):
    """
    Headcount seat for one attendance record (MA/FA/MC/FC/…).

    Not pre-created for weeks 1–5; add only when counts are known.
    Preview still lays seats into week columns using the parent record’s ``week``.
    """

    id = models.BigAutoField(primary_key=True)
    record = models.OneToOneField(
        "cf_operations.AttendanceRecord",
        on_delete=models.CASCADE,
        related_name="seat",
        verbose_name=_("attendance record"),
    )
    male_adults = models.PositiveIntegerField(_("male adult (MA)"), default=0)
    female_adults = models.PositiveIntegerField(_("female adult (FA)"), default=0)
    male_children = models.PositiveIntegerField(_("male children (MC)"), default=0)
    female_children = models.PositiveIntegerField(
        _("female children (FC)"), default=0
    )
    total = models.PositiveIntegerField(
        _("total (T)"),
        default=0,
        help_text=_("Usually MA+FA+MC+FC; recomputed on save."),
    )
    new_converts = models.PositiveIntegerField(_("new converts (N/C)"), default=0)
    first_timers = models.PositiveIntegerField(_("first timers (F/T)"), default=0)
    testimonies = models.PositiveIntegerField(_("testimonies (TS)"), default=0)

    class Meta:
        abstract = True
        ordering = ("record",)
        verbose_name = _("attendance seat")
        verbose_name_plural = _("attendance seats")

    def __str__(self) -> str:
        return f"{self.record} · seat (T={self.total})"

    def recompute_total(self) -> int:
        return (
            int(self.male_adults or 0)
            + int(self.female_adults or 0)
            + int(self.male_children or 0)
            + int(self.female_children or 0)
        )

    def save(self, *args, **kwargs):
        self.total = self.recompute_total()
        super().save(*args, **kwargs)


class AbstractDocumentCategory(AuditMixin):
    """Classifies documents by type and sets the minimum access role required."""

    branch = models.ForeignKey(
        "cf_users.Branch",
        on_delete=models.PROTECT,
        related_name="document_categories",
        verbose_name=_("branch"),
    )
    name = models.CharField(_("name"), max_length=150)
    required_role_access = models.CharField(
        _("required access role"), max_length=50, default="VIEWER"
    )

    class Meta:
        abstract = True
        ordering = ("-modified_at", "name")
        unique_together = ("branch", "name")

    def __str__(self) -> str:
        return self.name


class AbstractDocument(AuditMixin, ValidateOrgBranchMixin):
    """A file or document stored against a branch, organised by category."""

    branch = models.ForeignKey(
        "cf_users.Branch",
        on_delete=models.PROTECT,
        related_name="documents",
        verbose_name=_("branch"),
    )
    category = models.ForeignKey(
        "cf_operations.DocumentCategory",
        on_delete=models.PROTECT,
        related_name="documents",
        verbose_name=_("category"),
    )
    title = models.CharField(_("title"), max_length=255)
    file = models.FileField(
        _("file"), upload_to="branch_documents/%Y/%m/", null=True, blank=True
    )
    is_confidential = models.BooleanField(_("is confidential"), default=False)
    notes = models.TextField(_("notes"), blank=True)

    class Meta:
        abstract = True
        ordering = ("-modified_at", "title")

    def __str__(self) -> str:
        return self.title

    def clean(self) -> None:
        self._validate_org_branch_relation("category")
