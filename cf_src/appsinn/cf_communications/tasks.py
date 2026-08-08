# cf-dev/cf_src/appsinn/cf_communications/tasks.py

"""Scheduled communications tasks (birthday greetings, etc.)."""

from __future__ import annotations

import calendar
import logging
from datetime import date

from celery import shared_task
from django.apps import apps
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

logger = logging.getLogger(__name__)
User = get_user_model()


def _is_leap(year: int) -> bool:
    return calendar.isleap(year)


def _matches_today(birth: date, today: date) -> bool:
    if birth.month == today.month and birth.day == today.day:
        return True
    # Celebrate 29 Feb on 28 Feb in non-leap years.
    if (
        birth.month == 2
        and birth.day == 29
        and today.month == 2
        and today.day == 28
        and not _is_leap(today.year)
    ):
        return True
    return False


def _resolve_branch_for_user(user):
    """Pick a branch for notification tenancy (member branch, else first access)."""
    member = getattr(user, "member_profile", None)
    if member is not None and getattr(member, "branch_id", None):
        return member.branch

    BranchUser = apps.get_model("cf_users", "BranchUser")
    link = (
        BranchUser.objects.filter(user_id=user.pk)
        .select_related("branch", "branch__organization")
        .first()
    )
    if link is not None:
        return link.branch

    OrganizationUser = apps.get_model("cf_users", "OrganizationUser")
    ou = (
        OrganizationUser.objects.filter(user_id=user.pk)
        .select_related("organization")
        .first()
    )
    if ou is not None:
        Branch = apps.get_model("cf_users", "Branch")
        return (
            Branch.objects.filter(organization_id=ou.organization_id, is_default=True)
            .first()
            or Branch.objects.filter(organization_id=ou.organization_id).first()
        )
    return None


def _format_birthday_template(template: str, **ctx) -> str:
    """Format typed templates; unknown keys left alone via safe substitution."""
    if not template:
        return ""
    try:
        return template.format(**ctx)
    except (KeyError, ValueError) as exc:
        logger.warning("Birthday template format failed (%s): %s", template[:80], exc)
        # Best-effort replace known placeholders only.
        out = template
        for key, value in ctx.items():
            out = out.replace("{%s}" % key, str(value))
        return out


def resolve_birthday_copy(branch, user, today: date) -> tuple[str, str] | None:
    """
    Resolve subject + body from branch override, else organisation.

    Returns None if greetings are disabled or no typed message is configured.
    """
    organization = getattr(branch, "organization", None)
    if organization is None:
        return None

    if not getattr(organization, "birthday_greetings_enabled", True):
        return None
    if not getattr(branch, "birthday_greetings_enabled", True):
        return None

    subject = (branch.birthday_subject or "").strip() or (
        organization.birthday_subject or ""
    ).strip()
    body = (branch.birthday_message or "").strip() or (
        organization.birthday_message or ""
    ).strip()

    if not body:
        return None

    if not subject:
        subject = "Happy Birthday, {name}!"

    name = user.get_full_name() or user.first_name or user.username or "friend"
    org_name = str(organization.trade_name or organization.name or "")
    branch_name = str(branch.name or "")
    ctx = {
        "name": name,
        "org": org_name,
        "branch": branch_name,
        "year": today.year,
    }
    return (
        _format_birthday_template(subject, **ctx),
        _format_birthday_template(body, **ctx),
    )


@shared_task(name="cf_communications.tasks.send_birthday_messages")
def send_birthday_messages(for_date: str | None = None) -> dict:
    """
    Send birthday greetings to users whose User.birth_date is today.

    Message text is typed on Organisation and/or Branch (branch overrides org).
    Channels follow each user's notify_via_* preferences.
    Idempotent: BirthdayGreetingLog enforces one send per user per year.
    """
    today = date.fromisoformat(for_date) if for_date else timezone.localdate()
    BirthdayGreetingLog = apps.get_model("cf_communications", "BirthdayGreetingLog")
    Notification = apps.get_model("cf_communications", "Notification")

    month, day = today.month, today.day
    dob_q = Q(birth_date__month=month, birth_date__day=day)
    if month == 2 and day == 28 and not _is_leap(today.year):
        dob_q |= Q(birth_date__month=2, birth_date__day=29)

    already = BirthdayGreetingLog.objects.filter(year=today.year).values_list(
        "user_id", flat=True
    )

    candidates = (
        User.objects.filter(is_active=True)
        .filter(dob_q)
        .exclude(pk__in=already)
        .select_related("member_profile", "member_profile__branch")
        .distinct()
    )

    sent = 0
    skipped = 0

    for user in candidates.iterator(chunk_size=100):
        birth = getattr(user, "birth_date", None)
        if birth is None or not _matches_today(birth, today):
            skipped += 1
            continue

        branch = _resolve_branch_for_user(user)
        if branch is None:
            logger.info(
                "Birthday skip user=%s: no branch context for notification.",
                user.pk,
            )
            skipped += 1
            continue

        # Ensure organization is loaded for template resolution.
        if not getattr(branch, "organization_id", None):
            skipped += 1
            continue
        if (
            not hasattr(branch, "organization")
            or branch.organization is None
        ):
            Branch = apps.get_model("cf_users", "Branch")
            branch = (
                Branch.objects.select_related("organization")
                .filter(pk=branch.pk)
                .first()
            )
            if branch is None:
                skipped += 1
                continue

        copy = resolve_birthday_copy(branch, user, today)
        if copy is None:
            logger.info(
                "Birthday skip user=%s: greetings disabled or no typed message "
                "on org/branch.",
                user.pk,
            )
            skipped += 1
            continue

        title, message = copy
        channels: list[str] = []
        try:
            Notification.create_and_notify(
                recipient=user,
                branch=branch,
                title=title,
                message=message,
                sms_text=title,
                notif_type="info",
            )
            if getattr(user, "notify_via_email", True) and user.email:
                channels.append("email")
            if getattr(user, "notify_via_inapp", True):
                channels.append("inapp")
            if getattr(user, "notify_via_sms", False) and user.phone_number:
                channels.append("sms")
            if getattr(user, "notify_via_whatsapp", False) and user.phone_number:
                channels.append("whatsapp")

            BirthdayGreetingLog.objects.get_or_create(
                user=user,
                year=today.year,
                defaults={
                    "for_date": today,
                    "channel_summary": ",".join(channels) or "logged",
                },
            )
            sent += 1
        except Exception as exc:  # noqa: BLE001
            logger.exception("Birthday message failed for user=%s: %s", user.pk, exc)
            skipped += 1

    logger.info("Birthday messages: sent=%s skipped=%s date=%s", sent, skipped, today)
    return {"sent": sent, "skipped": skipped, "date": today.isoformat()}
