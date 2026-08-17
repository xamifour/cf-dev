# cf-dev/cf_src/appsinn/cf_users/apps.py

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CfUsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "cf_users"
    verbose_name = _("CF Users")

    def ready(self) -> None:
        from . import signals  # noqa: F401
