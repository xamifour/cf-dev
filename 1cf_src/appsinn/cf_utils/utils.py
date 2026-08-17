# cf-dev/cf_src/appsinn/cf_utils/utils.py

"""Shared utility helpers for CF applications."""

from __future__ import annotations

import re
import sys
from typing import Any

from django.utils.text import slugify


def default_or_test(value: Any, test: Any = None) -> Any:
    """
    Return ``test`` when running under the Django test runner, else ``value``.

    Used for settings that should be relaxed or deterministic during tests.
    """
    if test is not None and _is_running_tests():
        return test
    return value


def _is_running_tests() -> bool:
    return "test" in sys.argv or any("pytest" in arg for arg in sys.argv)


def unique_slug(
    instance,
    *,
    value: str,
    slug_field: str = "slug",
    max_length: int = 128,
) -> str:
    """
    Build a unique slug for ``instance`` based on ``value``.

    Collision handling appends ``-2``, ``-3``, … deterministically.
    """
    base = slugify(value)[:max_length] or "item"
    base = re.sub(r"-+", "-", base).strip("-")
    candidate = base
    model = instance.__class__
    counter = 2
    while True:
        qs = model.objects.filter(**{slug_field: candidate})
        if instance.pk:
            qs = qs.exclude(pk=instance.pk)
        if not qs.exists():
            return candidate
        suffix = f"-{counter}"
        candidate = f"{base[: max_length - len(suffix)]}{suffix}"
        counter += 1
