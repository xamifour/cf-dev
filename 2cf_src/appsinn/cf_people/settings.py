# cf-dev/cf_src/appsinn/cf_people/settings.py

"""
App-level defaults for cf_people (overridable via Django / project settings).

Import from this module in other packages that extend cf_people. Prefer
``getattr(django.conf.settings, "CF_…")`` overrides for deployment config.
"""

from django.conf import settings

from cf_utils.utils import default_or_test

# API list page size override for this app (falls back to cf_utils defaults).
CF_PEOPLE_API_PAGE_SIZE = getattr(
    settings,
    "CF_PEOPLE_API_PAGE_SIZE",
    getattr(settings, "CF_API_PAGE_SIZE", 50),
)

# Feature flags
CF_PEOPLE_API_ENABLED = getattr(settings, "CF_PEOPLE_API_ENABLED", True)

# Soft limit for bulk export / admin actions (avoid full-table dumps).
CF_PEOPLE_EXPORT_MAX_ROWS = getattr(
    settings,
    "CF_PEOPLE_EXPORT_MAX_ROWS",
    default_or_test(value=50_000, test=1_000),
)
