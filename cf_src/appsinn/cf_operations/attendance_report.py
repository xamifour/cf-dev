# cf-dev/cf_src/appsinn/cf_operations/attendance_report.py

"""
Build Excel-style attendance sheets from AttendanceRecord + optional seat.

Preview always uses a 5-week column layout. Each record’s seat counts go into
the column matching ``record.week`` (default column 1 if week is blank).
Zone name is taken from linked Zone FKs when present.
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterable
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


def build_sheet_from_records(
    records: Iterable,
    *,
    assembly_name: str = "",
    zone_name: str = "",
    report_title: str = "",
    coordinator_name: str = "",
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

    if records and not assembly_name:
        branch = getattr(records[0], "branch", None)
        if branch is not None:
            org = getattr(branch, "organization", None)
            assembly_name = (
                (getattr(org, "trade_name", None) or getattr(org, "name", None) or "")
                or getattr(branch, "name", "")
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

    # Zone leader name (for LEADER NAME header) when not supplied explicitly.
    leader_name = coordinator_name or ""
    if records and not leader_name:
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
            leader_name = next(iter(zone_leaders))
        elif len(zone_leaders) > 1:
            leader_name = "Multiple leaders"

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
            leader_name = record.get_display_leader()
            address = record.get_display_address()
            phone = record.get_display_phone_number()
            location_provider = record.get_display_location_provider()
        else:
            code = (record.code or "").strip()
            centre = (record.centre_name or "").strip()
            leader_name = (record.leader or "").strip()
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
            leader_name.lower(),
            address.lower(),
            phone.lower(),
            zone_label.lower(),
        )
        if key not in grouped:
            grouped[key] = {
                "code": code,
                "centre_name": centre,
                "leader_name": leader_name,
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

    return {
        "assembly_name": assembly_name or "Assembly",
        "zone_name": zone_name or "—",
        "report_title": report_title or "Attendance report",
        # leader_name is the preferred key (from Zone.leader); coordinator_name kept for compat.
        "leader_name": leader_name or "",
        "coordinator_name": leader_name or coordinator_name or "",
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
