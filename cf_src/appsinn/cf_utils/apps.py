# cf-dev/cf_src/appsinn/cf_utils/apps.py

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CfUtilsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "cf_utils"
    verbose_name = _("CF Utilities")
