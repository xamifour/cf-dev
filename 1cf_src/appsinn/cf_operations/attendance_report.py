# cf-dev/cf_src/appsinn/cf_operations/attendance_report.py

"""
Build Excel-style attendance sheets from AttendanceRecord + optional seat.

Preview always uses a 5-week column layout. Each record’s seat counts go into
the column matching ``record.week`` (default column 1 if week is blank).
Header names come from the selected report scope (org → branch → zone →
sub group). Zone / sub group lines are shown only for those report types.
"""

from __future__ import annotations

from calendar import month_name
from collections import OrderedDict
from collections.abc import Iterable
from datetime import date, datetime
from typing import Any


def default_week_labels() -> list[str]:
    return ["WEEK 1", "WEEK 2", "WEEK 3", "WEEK 4", "WEEK 5"]


def _empty_counts() -> dict[str, int]:
    return {
        "male_adults": 0,
        "female_adults": 0,
        "male_children": 0,
        "female_children": 0,
        "total": 0,
        "new_converts": 0,
        "first_timers": 0,
        "testimonies": 0,
    }


def _seat_counts(seat) -> dict[str, int]:
    if seat is None:
        return _empty_counts()
    return {
        "male_adults": int(seat.male_adults or 0),
        "female_adults": int(seat.female_adults or 0),
        "male_children": int(seat.male_children or 0),
        "female_children": int(seat.female_children or 0),
        "total": int(seat.total or 0),
        "new_converts": int(seat.new_converts or 0),
        "first_timers": int(seat.first_timers or 0),
        "testimonies": int(seat.testimonies or 0),
    }


def _counts_active(cell: dict[str, int]) -> bool:
    return any(
        cell[k]
        for k in (
            "male_adults",
            "female_adults",
            "male_children",
            "female_children",
            "new_converts",
            "first_timers",
            "testimonies",
        )
    )


def _member_name(member) -> str:
    if member is None:
        return ""
    return str(member).strip()


def _org_display_name(org) -> str:
    if org is None:
        return ""
    return (
        (getattr(org, "trade_name", None) or "") or (getattr(org, "name", None) or "")
    ).strip()


def format_report_date(filters: dict[str, str] | None, records: Iterable | None = None) -> str:
    """Human date line for the sheet header (exact / range / month / records)."""
    filters = filters or {}

    def _fmt(value) -> str:
        if isinstance(value, datetime):
            value = value.date()
        if isinstance(value, date):
            return value.strftime("%d %B %Y")
        return str(value)

    raw_date = (filters.get("date") or "").strip()
    if raw_date:
        try:
            return _fmt(datetime.strptime(raw_date, "%Y-%m-%d").date())
        except ValueError:
            return raw_date

    date_from = (filters.get("date_from") or "").strip()
    date_to = (filters.get("date_to") or "").strip()
    if date_from or date_to:
        left, right = date_from or "…", date_to or "…"
        if date_from:
            try:
                left = _fmt(datetime.strptime(date_from, "%Y-%m-%d").date())
            except ValueError:
                pass
        if date_to:
            try:
                right = _fmt(datetime.strptime(date_to, "%Y-%m-%d").date())
            except ValueError:
                pass
        return f"{left} – {right}"

    bits: list[str] = []
    month = (filters.get("month") or "").strip()
    year = (filters.get("year") or "").strip()
    if month:
        try:
            bits.append(month_name[int(month)])
        except (ValueError, IndexError):
            bits.append(month)
    if year:
        bits.append(year)
    if bits:
        return " ".join(bits)

    seen: list[date] = []
    for record in records or []:
        at = getattr(record, "attendance_at", None)
        if not at:
            continue
        seen.append(at.date() if isinstance(at, datetime) else at)
    if seen:
        first, last = min(seen), max(seen)
        if first == last:
            return _fmt(first)
        return f"{_fmt(first)} – {_fmt(last)}"

    try:
        from django.utils import timezone as dj_tz

        return _fmt(dj_tz.localdate())
    except Exception:  # noqa: BLE001
        return _fmt(date.today())


def resolve_sheet_header(
    *,
    organization=None,
    branch=None,
    zone=None,
    subgroup=None,
    report_date: str = "",
    leader_name: str = "",
) -> dict[str, Any]:
    """
    Header lines and LEADER NAME from the selected scope.

    Most-specific selected unit wins for the leader: sub group → zone →
    branch → organisation.
    """
    org = organization
    if org is None and branch is not None:
        org = getattr(branch, "organization", None)
    if org is None and zone is not None:
        org = getattr(getattr(zone, "branch", None), "organization", None)
    if org is None and subgroup is not None:
        org = getattr(getattr(subgroup, "branch", None), "organization", None)

    br = branch
    if br is None and zone is not None:
        br = getattr(zone, "branch", None)
    if br is None and subgroup is not None:
        br = getattr(subgroup, "branch", None)

    zn = zone
    if zn is None and subgroup is not None:
        zn = getattr(subgroup, "zone", None)

    show_zone = zone is not None or subgroup is not None
    show_subgroup = subgroup is not None

    if not leader_name:
        if subgroup is not None:
            leader_name = _member_name(getattr(subgroup, "leader", None))
        elif zone is not None:
            leader_name = _member_name(getattr(zone, "leader", None))
        elif branch is not None:
            leader_name = _member_name(getattr(branch, "leader", None))
        elif org is not None:
            leader_name = _member_name(getattr(org, "leader", None))

    zone_name = ""
    if show_zone and zn is not None:
        zone_name = (getattr(zn, "name", None) or "").strip()

    return {
        "organization_name": _org_display_name(org),
        "branch_name": (getattr(br, "name", None) or "").strip() if br else "",
        "zone_name": zone_name,
        "subgroup_name": (
            (getattr(subgroup, "name", None) or "").strip() if subgroup else ""
        ),
        "report_date": report_date or "",
        "show_zone": show_zone,
        "show_subgroup": show_subgroup,
        "leader_name": leader_name or "",
    }


def build_sheet_from_records(
    records: Iterable,
    *,
    assembly_name: str = "",
    organization_name: str = "",
    branch_name: str = "",
    zone_name: str = "",
    subgroup_name: str = "",
    report_date: str = "",
    report_title: str = "",
    coordinator_name: str = "",
    header_leader_name: str | None = None,
    show_zone: bool | None = None,
    show_subgroup: bool | None = None,
    week_labels: list[str] | None = None,
    filter_summary: str = "",
) -> dict[str, Any]:
    """
    Aggregate attendance records into an Excel-layout context dict.
    """
    records = list(records)
    labels = week_labels or default_week_labels()
    while len(labels) < 5:
        labels.append(f"WEEK {len(labels) + 1}")
    labels = labels[:5]

    org_name = (organization_name or assembly_name or "").strip()
    if records and not org_name:
        rec_branch = getattr(records[0], "branch", None)
        if rec_branch is not None:
            org = getattr(rec_branch, "organization", None)
            org_name = (
                _org_display_name(org)
                or getattr(rec_branch, "name", "")
                or "Assembly"
            )

    if records and not zone_name:
        zones = {
            (r.zone.name if getattr(r, "zone_id", None) else None) for r in records
        }
        zones.discard(None)
        if len(zones) == 1:
            zone_name = next(iter(zones))
        elif len(zones) > 1:
            zone_name = "Multiple zones"
        else:
            zone_name = ""

    # Header LEADER NAME is the scope leader — never the last row's leader.
    if header_leader_name is not None:
        header_leader = header_leader_name
    else:
        header_leader = coordinator_name or ""
        if records and not header_leader:
            zone_leaders: set[str] = set()
            for r in records:
                zone = getattr(r, "zone", None)
                if zone is None:
                    continue
                leader = getattr(zone, "leader", None)
                if leader is not None:
                    zone_leaders.add(str(leader).strip())
            zone_leaders.discard("")
            if len(zone_leaders) == 1:
                header_leader = next(iter(zone_leaders))
            elif len(zone_leaders) > 1:
                header_leader = "Multiple leaders"

    if records and not report_title:
        events = {
            (r.event.title if getattr(r, "event_id", None) else None) for r in records
        }
        events.discard(None)
        if len(events) == 1:
            report_title = next(iter(events))
        elif len(events) > 1:
            report_title = "Attendance report"
        else:
            report_title = "Attendance report"

    # Pivot: one preview row per centre identity; week columns from record.week.
    grouped: OrderedDict[tuple, dict[str, Any]] = OrderedDict()

    week_totals = [_empty_counts() for _ in range(5)]
    active_cells = 0
    months_seen: set[int] = set()

    def _sort_code(r):
        if hasattr(r, "get_display_code"):
            return (r.get_display_code() or "").lower()
        return (r.code or "").lower()

    def _sort_centre(r):
        if hasattr(r, "get_display_centre_name"):
            return (r.get_display_centre_name() or "").lower()
        return (r.centre_name or "").lower()

    ordered = sorted(
        records,
        key=lambda r: (
            _sort_code(r),
            _sort_centre(r),
            str(getattr(r, "pk", "")),
        ),
    )

    for record in ordered:
        # Prefer stored overrides; fall back to scope (sub group → zone → branch → org).
        if hasattr(record, "get_display_centre_name"):
            code = record.get_display_code()
            centre = record.get_display_centre_name()
            row_leader = record.get_display_leader()
            address = record.get_display_address()
            phone = record.get_display_phone_number()
            location_provider = record.get_display_location_provider()
        else:
            code = (record.code or "").strip()
            centre = (record.centre_name or "").strip()
            row_leader = (record.leader or "").strip()
            address = (record.address or "").strip()
            phone = (getattr(record, "phone_number", None) or "").strip()
            location_provider = (
                getattr(record, "location_provider", None) or ""
            ).strip()
        zone_label = (
            record.zone.name if getattr(record, "zone_id", None) else ""
        )
        if getattr(record, "month", None):
            months_seen.add(int(record.month))
        key = (
            code.lower(),
            centre.lower(),
            row_leader.lower(),
            address.lower(),
            phone.lower(),
            zone_label.lower(),
        )
        if key not in grouped:
            grouped[key] = {
                "code": code,
                "centre_name": centre,
                "leader_name": row_leader,
                "address": address,
                "contact": phone,  # Excel CONTACT column ← phone_number
                "zone_name": zone_label,
                "location_provider": location_provider,
                "weeks": [_empty_counts() for _ in range(5)],
                "records": [],
            }
        row = grouped[key]
        if zone_label and not row["zone_name"]:
            row["zone_name"] = zone_label
        if location_provider and not row.get("location_provider"):
            row["location_provider"] = location_provider
        row["records"].append(record)

        seat = getattr(record, "seat", None)
        cell = _seat_counts(seat)
        week_idx = (record.week or 1) - 1
        if week_idx < 0 or week_idx > 4:
            week_idx = 0
        for k, v in cell.items():
            row["weeks"][week_idx][k] += v
            week_totals[week_idx][k] += v

    rows = []
    for row in grouped.values():
        if any(_counts_active(w) for w in row["weeks"]):
            active_cells += 1
        rows.append(row)

    grand = {
        "total": sum(w["total"] for w in week_totals),
        "new_converts": sum(w["new_converts"] for w in week_totals),
        "first_timers": sum(w["first_timers"] for w in week_totals),
        "testimonies": sum(w["testimonies"] for w in week_totals),
    }
    filled_weeks = sum(1 for w in week_totals if w["total"] > 0) or 1
    average = round(grand["total"] / filled_weeks, 1) if rows else 0

    month_label = ""
    if len(months_seen) == 1:
        from django.utils.translation import gettext as _

        month_names = dict(
            [
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
        )
        month_label = month_names.get(next(iter(months_seen)), "")

    if show_zone is None:
        show_zone = bool(zone_name and zone_name != "—")
    if show_subgroup is None:
        show_subgroup = bool(subgroup_name)

    org_name = org_name or "Assembly"

    return {
        "assembly_name": org_name,
        "organization_name": org_name,
        "branch_name": branch_name or "",
        "zone_name": zone_name or "",
        "subgroup_name": subgroup_name or "",
        "report_date": report_date or "",
        "show_zone": bool(show_zone),
        "show_subgroup": bool(show_subgroup),
        "report_title": report_title or "Attendance report",
        # leader_name is the scope leader (org/branch/zone/sub group).
        "leader_name": header_leader or "",
        "coordinator_name": header_leader or coordinator_name or "",
        "week_labels": labels,
        "rows": rows,
        "week_totals": week_totals,
        "grand": grand,
        "average": average,
        "total_cells": len(rows),
        "active_cells": active_cells,
        "month_label": month_label,
        "filter_summary": filter_summary or "",
        "record_count": len(records),
    }
