# cf-dev/cf_src/appsinn/cf_utils/settings.py

"""
App-level defaults for shared CF utilities (overridable via Django settings).

Other apps import from here for cross-cutting limits that must remain
consistent under multi-tenant scale (1M+ orgs, 1M+ users/org).
"""

from django.conf import settings

from cf_utils.utils import default_or_test

# Cursor page size for list APIs. Keep modest so responses stay small at scale.
CF_API_PAGE_SIZE = getattr(settings, "CF_API_PAGE_SIZE", 50)
CF_API_MAX_PAGE_SIZE = getattr(settings, "CF_API_MAX_PAGE_SIZE", 200)

# Hard cap on how many related rows a nested serializer may expand.
CF_API_NESTED_LIMIT = getattr(settings, "CF_API_NESTED_LIMIT", 100)

# Prefer cursor pagination for unbounded feeds (users, posts, logs).
CF_API_DEFAULT_PAGINATION = getattr(
    settings,
    "CF_API_DEFAULT_PAGINATION",
    "cf_utils.api.pagination.CFCursorPagination",
)

# Throttle labels consumed by REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"].
CF_API_THROTTLE_USER = getattr(
    settings,
    "CF_API_THROTTLE_USER",
    default_or_test(value="1000/hour", test="10000/hour"),
)
CF_API_THROTTLE_ANON = getattr(
    settings,
    "CF_API_THROTTLE_ANON",
    default_or_test(value="100/hour", test="10000/hour"),
)
