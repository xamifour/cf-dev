# cf-dev/cf_src/appsinn/cf_communications/settings.py

"""App-level defaults for communications channels (overridable via Django settings)."""

from django.conf import settings

# ── Email ─────────────────────────────────────────────────────────────────
CF_EMAIL_TEMPLATE = getattr(
    settings,
    "CF_EMAIL_TEMPLATE",
    getattr(settings, "OPENWISP_EMAIL_TEMPLATE", "cf_communications/email_template.html"),
)
# Backward-compatible aliases used by utils (OpenWISP-style names).
OPENWISP_EMAIL_TEMPLATE = CF_EMAIL_TEMPLATE
OPENWISP_EMAIL_LOGO = getattr(
    settings,
    "CF_EMAIL_LOGO",
    getattr(settings, "OPENWISP_EMAIL_LOGO", "static/assets/img/logo2.svg"),
)
OPENWISP_HTML_EMAIL = getattr(
    settings,
    "CF_HTML_EMAIL",
    getattr(settings, "OPENWISP_HTML_EMAIL", True),
)

# ── WhatsApp ──────────────────────────────────────────────────────────────
WHATSAPP_DEFAULT_TEMPLATE = getattr(settings, "WHATSAPP_DEFAULT_TEMPLATE", None)
WHATSAPP_TEMPLATE_LANGUAGE = getattr(settings, "WHATSAPP_TEMPLATE_LANGUAGE", "en_US")

# ── SMS ───────────────────────────────────────────────────────────────────
SMS_DEFAULT_TEMPLATE = getattr(settings, "SMS_DEFAULT_TEMPLATE", "{message}")

# ── In-app ────────────────────────────────────────────────────────────────
INAPP_DEFAULT_TEMPLATE = getattr(settings, "INAPP_DEFAULT_TEMPLATE", "{message}")
INAPP_DEFAULT_TITLE_TEMPLATE = getattr(settings, "INAPP_DEFAULT_TITLE_TEMPLATE", "{title}")

# Birthday greetings: typed on Organisation / Branch (see admin Birthday messages).

# ── REST API ──────────────────────────────────────────────────────────────
CF_COMMUNICATIONS_API_ENABLED = getattr(settings, "CF_COMMUNICATIONS_API_ENABLED", True)
CF_COMMUNICATIONS_API_PAGE_SIZE = getattr(settings, "CF_COMMUNICATIONS_API_PAGE_SIZE", 50)
CF_COMMUNICATIONS_EXPORT_MAX_ROWS = getattr(
    settings, "CF_COMMUNICATIONS_EXPORT_MAX_ROWS", 50_000
)
