# cf-dev/cf_src/appsinn/cf_social/apps.py

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CfSocialConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "cf_social"
    verbose_name = _("CF Social")

    def ready(self):
        from . import signals  # noqa: F401
