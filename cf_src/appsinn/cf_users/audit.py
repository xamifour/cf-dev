# cf-dev/cf_src/appsinn/cf_users/audit.py

"""Request-scoped current user for AuditMixin created_by / modified_by."""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any

_current_user: ContextVar[Any] = ContextVar("cf_audit_user", default=None)


def get_current_user():
    """Return the authenticated user for the active request, or None."""
    return _current_user.get()


def set_current_user(user) -> None:
    _current_user.set(user)


def clear_current_user() -> None:
    _current_user.set(None)
