# cf-dev/cf_src/cf_users/settings.py

from django.conf import settings

from cf_utils.utils import default_or_test

ORGANIZATION_USER_ADMIN = getattr(settings, 'CF_ORGANIZATION_USER_ADMIN', True)
ORGANIZATION_OWNER_ADMIN = getattr(settings, 'CF_ORGANIZATION_OWNER_ADMIN', True)
USERS_AUTH_API = getattr(settings, 'CF_USERS_AUTH_API', True)
USERS_AUTH_THROTTLE_RATE = getattr(
    settings,
    'CF_USERS_AUTH_THROTTLE_RATE',
    default_or_test(value='20/day', test=None),
)
AUTH_BACKEND_AUTO_PREFIXES = getattr(
    settings, 'CF_USERS_AUTH_BACKEND_AUTO_PREFIXES', tuple()
)
EXPORT_USERS_COMMAND_CONFIG = {
    'fields': [
        'id',
        'username',
        'password',
        'email',
        'is_staff',
        'is_active',
        'first_name',
        'last_name',
        'phone_number',
        'birth_date',
        'address',
        'city',
        'country',
        'notes',
        'language',
        'organizations',
        'created_at',
        'modified_at',
        'created_by',
        'modified_by',
    ],
    'select_related': [],
}
USER_PASSWORD_EXPIRATION = getattr(
    settings, 'CF_USERS_USER_PASSWORD_EXPIRATION', 0
)
STAFF_USER_PASSWORD_EXPIRATION = getattr(
    settings, 'CF_USERS_STAFF_USER_PASSWORD_EXPIRATION', 0
)
# Set the AutocompleteFilter view if it is not defined in the settings
setattr(
    settings,
    'CF_AUTOCOMPLETE_FILTER_VIEW',
    getattr(
        settings,
        'CF_AUTOCOMPLETE_FILTER_VIEW',
        'cf_users.views.AutocompleteJsonView',
    ),
)

# ── REST API ──────────────────────────────────────────────────────────────
CF_USERS_API_ENABLED = getattr(settings, "CF_USERS_API_ENABLED", True)
CF_USERS_API_PAGE_SIZE = getattr(settings, "CF_USERS_API_PAGE_SIZE", 50)
CF_USERS_EXPORT_MAX_ROWS = getattr(settings, "CF_USERS_EXPORT_MAX_ROWS", 50_000)
