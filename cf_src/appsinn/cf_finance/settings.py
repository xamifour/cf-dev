# cf-dev/cf_src/appsinn/cf_finance/settings.py

"""
App-level defaults for cf_finance (overridable via Django / project settings).

Import from this module in other packages that extend cf_finance. Prefer
``getattr(django.conf.settings, "CF_…")`` overrides for deployment config.
"""

from django.conf import settings

from cf_utils.utils import default_or_test

# API list page size override for this app (falls back to cf_utils defaults).
CF_FINANCE_API_PAGE_SIZE = getattr(
    settings,
    "CF_FINANCE_API_PAGE_SIZE",
    getattr(settings, "CF_API_PAGE_SIZE", 50),
)

# Feature flags
CF_FINANCE_API_ENABLED = getattr(settings, "CF_FINANCE_API_ENABLED", True)

# Soft limit for bulk export / admin actions (avoid full-table dumps).
CF_FINANCE_EXPORT_MAX_ROWS = getattr(
    settings,
    "CF_FINANCE_EXPORT_MAX_ROWS",
    default_or_test(value=50_000, test=1_000),
)
