# cf-dev/cf_src/appsinn/cf_utils/api/permissions.py

"""Reusable DRF permissions for tenant-scoped resources."""

from __future__ import annotations

from rest_framework.permissions import BasePermission, IsAuthenticated


class IsAuthenticatedAndActive(IsAuthenticated):
    """Authenticated users who still have ``is_active``."""

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return bool(request.user and request.user.is_active)


class IsStaffUser(BasePermission):
    """Staff / superuser only (platform ops APIs)."""

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and (u.is_staff or u.is_superuser))


class IsObjectOwnerOrStaff(BasePermission):
    """
    Object-level: owner (``created_by`` / ``author`` / ``user``) or staff.

    Views may set ``owner_field`` (default tries common names).
    """

    def has_object_permission(self, request, view, obj):
        u = request.user
        if not u or not u.is_authenticated:
            return False
        if u.is_staff or u.is_superuser:
            return True
        field = getattr(view, "owner_field", None)
        if field:
            return getattr(obj, f"{field}_id", None) == u.pk or getattr(
                obj, field, None
            ) == u
        for name in ("created_by_id", "author_id", "user_id", "owner_id"):
            if hasattr(obj, name) and getattr(obj, name) == u.pk:
                return True
        return False
