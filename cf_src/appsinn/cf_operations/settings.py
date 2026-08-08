# cf-dev/cf_src/appsinn/cf_operations/settings.py

"""
App-level defaults for cf_operations (overridable via Django / project settings).

Import from this module in other packages that extend cf_operations. Prefer
``getattr(django.conf.settings, "CF_…")`` overrides for deployment config.
"""

from django.conf import settings

from cf_utils.utils import default_or_test

# API list page size override for this app (falls back to cf_utils defaults).
CF_OPERATIONS_API_PAGE_SIZE = getattr(
    settings,
    "CF_OPERATIONS_API_PAGE_SIZE",
    getattr(settings, "CF_API_PAGE_SIZE", 50),
)

# Feature flags
CF_OPERATIONS_API_ENABLED = getattr(settings, "CF_OPERATIONS_API_ENABLED", True)

# Soft limit for bulk export / admin actions (avoid full-table dumps).
CF_OPERATIONS_EXPORT_MAX_ROWS = getattr(
    settings,
    "CF_OPERATIONS_EXPORT_MAX_ROWS",
    default_or_test(value=50_000, test=1_000),
)
