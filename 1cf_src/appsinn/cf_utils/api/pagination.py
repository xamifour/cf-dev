# cf-dev/cf_src/appsinn/cf_utils/api/pagination.py

"""
Pagination strategies for multi-tenant scale.

Prefer cursor pagination for large / append-only collections so list endpoints
stay O(page) rather than O(offset) under millions of rows per organisation.
"""

from __future__ import annotations

from rest_framework.pagination import CursorPagination, PageNumberPagination

from cf_utils import settings as app_settings


class CFCursorPagination(CursorPagination):
    """
    Default list pagination for CF APIs.

    Ordering must be unique and indexed (typically ``-created_at`` + ``id``).
    """

    page_size = app_settings.CF_API_PAGE_SIZE
    max_page_size = app_settings.CF_API_MAX_PAGE_SIZE
    page_size_query_param = "page_size"
    # Prefer last modification so edited rows surface at the top of feeds.
    ordering = "-modified_at"
    cursor_query_param = "cursor"


class CFPageNumberPagination(PageNumberPagination):
    """Offset pagination for small admin-style collections only."""

    page_size = app_settings.CF_API_PAGE_SIZE
    max_page_size = app_settings.CF_API_MAX_PAGE_SIZE
    page_size_query_param = "page_size"
