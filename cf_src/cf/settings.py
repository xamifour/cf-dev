# cf-dev/cf_src/cf/settings.py

import os
import sys
from pathlib import Path

import environ

# ── Process detection ─────────────────────────────────────────────────────
IS_CELERY = "celery" in sys.argv[0] or os.environ.get("IS_CELERY") == "1"

# ── Paths ─────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
APPS_DIR = BASE_DIR / "appsinn"

# Ensure apps under appsinn are importable as top-level packages.
_appsinn = str(APPS_DIR)
if _appsinn not in sys.path:
    sys.path.insert(0, _appsinn)

# ── Environment ───────────────────────────────────────────────────────────
env = environ.Env()
# Prefer repo-local .env for development, then host-level production files.
for env_path in (
    BASE_DIR.parent / ".env",
    BASE_DIR / ".env",
    Path("/etc/cf/config.env"),
    Path("/etc/cf/secrets.env"),
):
    if env_path.exists():
        env.read_env(str(env_path))

# ── Core ──────────────────────────────────────────────────────────────────
DEBUG = env.bool("DEBUG", default=True)
SECRET_KEY = (
    env.str("SECRET_KEY_DEV", default="dev-insecure-change-me")
    if DEBUG
    else env.str("SECRET_KEY_LIVE")
)

ALLOWED_HOSTS = (
    env.list("ALLOWED_HOSTS_DEV", default=["127.0.0.1", "localhost"])
    if DEBUG
    else env.list("ALLOWED_HOSTS_LIVE")
)

if not DEBUG and not ALLOWED_HOSTS:
    raise ValueError("ALLOWED_HOSTS must be set in production.")

SITE_ID = 1
ROOT_URLCONF = "cf.urls"
WSGI_APPLICATION = "cf.wsgi.application"
ASGI_APPLICATION = "cf.asgi.application"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Authentication ────────────────────────────────────────────────────────
AUTH_USER_MODEL = "cf_users.User"

AUTHENTICATION_BACKENDS = [
    "cf_users.backends.UsersAuthenticationBackend",
    "cf_users.backends.OrganizationGroupBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# Portal is the primary surface for organisation users.
# Staff operators use /admin/ (requires is_staff).
LOGIN_URL = "portal_login"
LOGIN_REDIRECT_URL = "portal_dashboard"
LOGOUT_REDIRECT_URL = "portal_login"

ACCOUNT_LOGIN_METHODS = {"username", "email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "username*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = "optional"

# ── Installed Apps ────────────────────────────────────────────────────────
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.humanize",
    # allauth
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    # CF apps
    "cf_utils.apps.CfUtilsConfig",
    "cf_users.apps.CfUsersConfig",
    "cf_people.apps.CfPeopleConfig",
    "cf_operations.apps.CfOperationsConfig",
    "cf_communications.apps.CfCommunicationsConfig",
    "cf_finance.apps.CfFinanceConfig",
    "cf_social.apps.CfSocialConfig",
    # Third-party
    "django_extensions",
    "rest_framework",
    "drf_yasg",
    "widget_tweaks",
    "django_ckeditor_5",
    "phonenumber_field",
    "channels",
    # Admin last among app groups
    "django.contrib.admin",
]

if DEBUG:
    INSTALLED_APPS += ["debug_toolbar"]

# ── Middleware ────────────────────────────────────────────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "cf_users.middleware.AuditUserMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "cf_users.middleware.TenantContextMiddleware",
    "cf_users.middleware.PasswordExpirationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

if DEBUG:
    MIDDLEWARE.insert(
        MIDDLEWARE.index("django.contrib.auth.middleware.AuthenticationMiddleware") + 1,
        "debug_toolbar.middleware.DebugToolbarMiddleware",
    )

# ── Templates ─────────────────────────────────────────────────────────────
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "OPTIONS": {
            "loaders": [
                "django.template.loaders.filesystem.Loader",
                "django.template.loaders.app_directories.Loader",
            ],
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "cf_users.context_processors.user_organization_and_branch",
            ],
        },
    },
]

# ── Database ──────────────────────────────────────────────────────────────
if env.str("DEFAULT_DB_NAME", default=""):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env.str("DEFAULT_DB_NAME"),
            "USER": env.str("DEFAULT_DB_USER"),
            "PASSWORD": env.str("DEFAULT_DB_PASSWORD"),
            "HOST": env.str("DEFAULT_DB_HOST", default="127.0.0.1"),
            "PORT": env.str("DEFAULT_DB_PORT", default="5432"),
            "CONN_MAX_AGE": env.int("DEFAULT_DB_CONN_MAX_AGE", default=0),
        }
    }
else:
    # Local/dev fallback when PostgreSQL is not configured.
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ── Password Validation ───────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "cf_users.validators.PasswordReuseValidator"},
]

# ── Internationalization ──────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
LANGUAGES = [
    ("en", "English"),
    ("en-us", "English (US)"),
    ("fr", "French"),
]
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ── Static & Media ────────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []

if not DEBUG:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }

# ── Cache (Redis with local-memory fallback) ──────────────────────────────
REDIS_HOST = env.str("REDIS_HOST", default="127.0.0.1")
REDIS_PORT = env.int("REDIS_PORT", default=6379)
USE_REDIS_CACHE = env.bool("USE_REDIS_CACHE", default=False)

if USE_REDIS_CACHE:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}/6",
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
            },
            "KEY_PREFIX": "cf_",
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "cf-default",
            "KEY_PREFIX": "cf_",
        }
    }

# ── Celery ────────────────────────────────────────────────────────────────
CELERY_BROKER_URL = env.str(
    "CELERY_BROKER_URL",
    default=f"redis://{REDIS_HOST}:{REDIS_PORT}/5",
)
CELERY_RESULT_BACKEND = env.str(
    "CELERY_RESULT_BACKEND",
    default=f"redis://{REDIS_HOST}:{REDIS_PORT}/5",
)
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = "UTC"
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=DEBUG)
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BEAT_SCHEDULE = {
    "password-expiration-email-daily": {
        "task": "cf_users.tasks.password_expiration_email",
        "schedule": 60 * 60 * 24,
    },
    # Automatic birthday greetings (copy typed on Organisation / Branch).
    "birthday-messages-daily": {
        "task": "cf_communications.tasks.send_birthday_messages",
        "schedule": 60 * 60 * 24,
    },
}

# ── Password Expiration (project + app settings bridge) ───────────────────
USER_PASSWORD_EXPIRATION = env.int("USER_PASSWORD_EXPIRATION", default=90)
STAFF_USER_PASSWORD_EXPIRATION = env.int("STAFF_USER_PASSWORD_EXPIRATION", default=60)
# App settings module reads CF_USERS_* keys.
CF_USERS_USER_PASSWORD_EXPIRATION = env.int(
    "CF_USERS_USER_PASSWORD_EXPIRATION",
    default=USER_PASSWORD_EXPIRATION,
)
CF_USERS_STAFF_USER_PASSWORD_EXPIRATION = env.int(
    "CF_USERS_STAFF_USER_PASSWORD_EXPIRATION",
    default=STAFF_USER_PASSWORD_EXPIRATION,
)

# ── Email ─────────────────────────────────────────────────────────────────
EMAIL_BACKEND = env.str(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
DEFAULT_FROM_EMAIL = env.str("DEFAULT_FROM_EMAIL", default="noreply@example.com")
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# ── DRF (scale defaults: cursor pagination, throttles) ────────────────────
# App packages under appsinn/*/api/ and cf_utils.api share these defaults so
# list endpoints stay O(page) under 1M+ orgs and high per-org user volume.
CF_API_PAGE_SIZE = env.int("CF_API_PAGE_SIZE", default=50)
CF_API_MAX_PAGE_SIZE = env.int("CF_API_MAX_PAGE_SIZE", default=200)

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "cf_utils.api.pagination.CFCursorPagination",
    "PAGE_SIZE": CF_API_PAGE_SIZE,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "cf_users_auth": env.str("CF_USERS_AUTH_THROTTLE_RATE", default="20/day"),
        "user": env.str("CF_API_THROTTLE_USER", default="1000/hour"),
        "anon": env.str("CF_API_THROTTLE_ANON", default="100/hour"),
    },
    "DEFAULT_FILTER_BACKENDS": [
        "rest_framework.filters.OrderingFilter",
    ],
    "ORDERING_PARAM": "ordering",
}

# ── CKEditor 5 ────────────────────────────────────────────────────────────
CKEDITOR_5_CONFIGS = {
    "default": {
        "toolbar": [
            "heading",
            "|",
            "bold",
            "italic",
            "link",
            "bulletedList",
            "numberedList",
            "blockQuote",
        ],
    }
}
# Staff-only uploads (admin Organisation notes, etc.)
CKEDITOR_5_FILE_UPLOAD_PERMISSION = "staff"
CKEDITOR_5_UPLOAD_FILE_TYPES = ["jpeg", "jpg", "png", "gif", "webp"]

# ── Phone numbers ─────────────────────────────────────────────────────────
PHONENUMBER_DEFAULT_REGION = env.str("PHONENUMBER_DEFAULT_REGION", default="GH")

# ── Debug toolbar ─────────────────────────────────────────────────────────
INTERNAL_IPS = env.list("INTERNAL_IPS", default=["127.0.0.1"])

# ── Logging ───────────────────────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "cf_users": {
            "handlers": ["console"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
        "cf_finance": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "cf_operations": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "cf_people": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# ── Security (Production) ─────────────────────────────────────────────────
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    CSRF_COOKIE_SAMESITE = "Lax"
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
