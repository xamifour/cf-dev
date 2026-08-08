# cf-dev/cf_src/appsinn/cf_utils/api/viewsets.py

"""
Base viewsets optimised for multi-tenant scale.

- Prefer ``TenantManager.for_user`` / active-tenant context over materialising
  large PK lists.
- Use cursor pagination by default.
- Subclasses should declare ``select_related_fields`` / ``prefetch_related_fields``
  to avoid N+1 queries at high cardinality.
"""

from __future__ import annotations

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from cf_utils.api.pagination import CFCursorPagination
from cf_utils.api.permissions import IsAuthenticatedAndActive


class CFModelViewSet(viewsets.ModelViewSet):
    """Standard authenticated model viewset with scale-safe defaults."""

    permission_classes = [IsAuthenticatedAndActive]
    pagination_class = CFCursorPagination
    # Override on subclasses for query efficiency.
    select_related_fields: tuple[str, ...] = ()
    prefetch_related_fields: tuple[str, ...] = ()
    # When True, call ``queryset.for_user(request.user)`` if available.
    tenant_scoped: bool = True

    def get_queryset(self):
        qs = super().get_queryset()
        if self.tenant_scoped and hasattr(qs, "for_user"):
            qs = qs.for_user(self.request.user)
        if self.select_related_fields:
            qs = qs.select_related(*self.select_related_fields)
        if self.prefetch_related_fields:
            qs = qs.prefetch_related(*self.prefetch_related_fields)
        return qs


class CFReadOnlyModelViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only counterpart of :class:`CFModelViewSet`."""

    permission_classes = [IsAuthenticatedAndActive]
    pagination_class = CFCursorPagination
    select_related_fields: tuple[str, ...] = ()
    prefetch_related_fields: tuple[str, ...] = ()
    tenant_scoped: bool = True

    def get_queryset(self):
        qs = super().get_queryset()
        if self.tenant_scoped and hasattr(qs, "for_user"):
            qs = qs.for_user(self.request.user)
        if self.select_related_fields:
            qs = qs.select_related(*self.select_related_fields)
        if self.prefetch_related_fields:
            qs = qs.prefetch_related(*self.prefetch_related_fields)
        return qs


class CFUnauthenticatedReadMixin:
    """Optional mixin: allow GET for anonymous (public content only)."""

    def get_permissions(self):
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [IsAuthenticated()]  # still require login by default
        return super().get_permissions()
