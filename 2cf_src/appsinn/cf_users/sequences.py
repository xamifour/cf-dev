# cf-dev/cf_src/appsinn/cf_users/sequences.py

"""Database-backed monotonic sequences for human-readable codes."""

from __future__ import annotations

import re

from django.db import models, transaction
from django.utils.translation import gettext_lazy as _


class CodeSequence(models.Model):
    """
    Named counter for auto-generated codes (ORG, MBR, TXN, …).

    Uses SELECT … FOR UPDATE so concurrent creates do not collide.
    """

    name = models.CharField(_("name"), max_length=64, unique=True, db_index=True)
    value = models.BigIntegerField(_("value"), default=0)

    class Meta:
        verbose_name = _("code sequence")
        verbose_name_plural = _("code sequences")

    def __str__(self) -> str:
        return f"{self.name}={self.value}"


def next_sequence_value(name: str, *, floor: int = 0) -> int:
    """
    Atomically increment and return the next value for ``name``.

    ``floor`` is the highest value already known to exist outside this counter
    (e.g. max numeric suffix of existing organisation codes). The counter is
    raised to at least ``floor`` before incrementing so missing/reset sequences
    never re-issue codes that are already in use.
    """
    floor = max(0, int(floor or 0))
    with transaction.atomic():
        seq, _created = CodeSequence.objects.select_for_update().get_or_create(
            name=name,
            defaults={"value": floor},
        )
        current = int(seq.value or 0)
        if current < floor:
            current = floor
        current += 1
        seq.value = current
        seq.save(update_fields=["value"])
        return current


def format_sequence_code(
    prefix: str,
    length: int,
    name: str | None = None,
    *,
    floor: int = 0,
) -> str:
    """Return ``PREFIX`` + zero-padded sequence (e.g. ORG00000001)."""
    sequence_name = name or f"{prefix or 'CODE'}_seq"
    value = next_sequence_value(sequence_name, floor=floor)
    # Grow width if the sequence exceeds fixed padding (avoids silent truncation).
    width = max(length, len(str(value)))
    return f"{prefix}{str(value).zfill(width)}"


_CODE_SUFFIX_RE = re.compile(r"^(\D*)(\d+)$")


def max_numeric_suffix_for_prefix(codes, prefix: str) -> int:
    """
    Return the highest integer suffix among codes that start with ``prefix``.

    Examples: ORG00000007 → 7, MBR12 → 12. Non-matching values are ignored.
    """
    prefix = prefix or ""
    max_n = 0
    for raw in codes:
        if raw is None:
            continue
        code = str(raw).strip()
        if not code:
            continue
        if prefix and not code.startswith(prefix):
            continue
        suffix = code[len(prefix) :] if prefix else code
        if suffix.isdigit():
            max_n = max(max_n, int(suffix))
            continue
        # Fallback for unexpected formats like "ORG-7"
        match = _CODE_SUFFIX_RE.match(code)
        if match and (not prefix or match.group(1) == prefix):
            max_n = max(max_n, int(match.group(2)))
    return max_n


def ensure_sequence_at_least(name: str, floor: int) -> int:
    """
    Raise an existing sequence counter to at least ``floor`` (no increment).

    Useful for one-off repair after bulk imports or when codes predate sequences.
    Returns the stored value after the update.
    """
    floor = max(0, int(floor or 0))
    with transaction.atomic():
        seq, _created = CodeSequence.objects.select_for_update().get_or_create(
            name=name,
            defaults={"value": floor},
        )
        if int(seq.value or 0) < floor:
            seq.value = floor
            seq.save(update_fields=["value"])
        return int(seq.value)
