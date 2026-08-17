# cf-dev/cf_src/appsinn/cf_people/services.py

"""Domain services for User ↔ Member composition."""

from __future__ import annotations

import re
import uuid
from typing import Any

from django.contrib.auth import get_user_model
from django.db import transaction

from .models import Member

User = get_user_model()


def _unique_username(base: str) -> str:
    """Build a username that satisfies project validators and uniqueness."""
    cleaned = re.sub(r"[^A-Za-z0-9_@]", "", (base or "member").replace(" ", ""))
    if not cleaned:
        cleaned = "member"
    if not re.match(r"^[A-Za-z0]", cleaned):
        cleaned = f"m{cleaned}"
    # Prefer 9–64 chars (project username rules); pad if needed.
    if len(cleaned) < 9:
        cleaned = f"{cleaned}{uuid.uuid4().hex}"[:9]
    cleaned = cleaned[:64]
    candidate = cleaned
    n = 1
    while User.objects.filter(username=candidate).exists():
        suffix = str(n)
        candidate = f"{cleaned[: 64 - len(suffix)]}{suffix}"
        n += 1
    return candidate


def _unique_email(first_name: str, last_name: str) -> str:
    base = f"{first_name}.{last_name}".lower()
    base = re.sub(r"[^a-z0-9.]+", "", base) or "member"
    domain = "members.local"
    candidate = f"{base}@{domain}"
    n = 1
    while User.objects.filter(email__iexact=candidate).exists():
        candidate = f"{base}{n}@{domain}"
        n += 1
    return candidate


def _unique_phone() -> str:
    """Generate a unique E.164-like placeholder phone for offline members."""
    # Ghana-style test range under +23320… for generated offline accounts.
    for _ in range(50):
        digits = uuid.uuid4().int % 10_000_000
        phone = f"+23320{digits:07d}"
        if not User.objects.filter(phone_number=phone).exists():
            return phone
    return f"+23320{uuid.uuid4().hex[:7]}"


@transaction.atomic
def create_user_for_member_identity(
    *,
    first_name: str,
    last_name: str,
    middle_name: str = "",
    email: str | None = None,
    phone_number: str | None = None,
    address: str = "",
    city: str = "",
    country: str = "",
    password: str | None = None,
    is_active: bool = True,
    **extra_user_fields: Any,
) -> Any:
    """
    Create a User that owns person identity fields for a Member.

    If ``password`` is omitted, the account gets an unusable password (directory
    / offline member until invited to the portal).
    """
    username_base = f"{first_name}{last_name}".lower() or "member"
    user = User(
        username=_unique_username(username_base),
        email=(email or _unique_email(first_name, last_name)).lower(),
        first_name=first_name,
        last_name=last_name,
        middle_name=middle_name or None,
        phone_number=phone_number or _unique_phone(),
        address=address or "—",
        city=city or "—",
        country=country or "—",
        is_active=is_active,
        **extra_user_fields,
    )
    if password:
        user.set_password(password)
    else:
        user.set_unusable_password()
    user.save()
    return user


@transaction.atomic
def create_member(
    *,
    branch,
    first_name: str,
    last_name: str,
    gender: str,
    user=None,
    middle_name: str = "",
    email: str | None = None,
    phone_number: str | None = None,
    address: str = "",
    city: str = "",
    country: str = "",
    password: str | None = None,
    family=None,
    birth_date=None,
    membership_status: str = "ACTIVE",
    **member_fields: Any,
) -> Member:
    """
    Create a Member with composition: identity on User, membership on Member.

    Provide an existing ``user`` or identity fields to create one.
    Birth date is stored only on User (``birth_date``).
    """
    if user is None:
        user = create_user_for_member_identity(
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name,
            email=email,
            phone_number=phone_number,
            address=address or getattr(branch, "address", "") or "—",
            city=city or getattr(branch, "city", "") or "—",
            country=country or getattr(branch, "country", "") or "—",
            password=password,
            gender=gender or None,
            birth_date=birth_date,
        )
    else:
        # Keep linked User identity in sync when creating with both.
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        if middle_name:
            user.middle_name = middle_name
        if gender:
            user.gender = gender
        if birth_date is not None:
            user.birth_date = birth_date
        user.save(
            update_fields=[
                "first_name",
                "last_name",
                "middle_name",
                "gender",
                "birth_date",
                "modified_at",
            ]
        )

    member = Member(
        branch=branch,
        user=user,
        family=family,
        membership_status=membership_status,
        **member_fields,
    )
    # Organisation is denormalised from branch (required for org-scoped member #).
    member._sync_organization_from_branch()
    member.full_clean()
    member.save()
    return member
