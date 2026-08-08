# cf-dev/cf_src/appsinn/cf_operations/apps.py

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CfOperationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "cf_operations"
    verbose_name = _("CF Operations")
