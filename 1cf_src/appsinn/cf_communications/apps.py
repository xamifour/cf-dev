# cf-dev/cf_src/appsinn/cf_communications/apps.py

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CfCommunicationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "cf_communications"
    verbose_name = _("CF Communications")
