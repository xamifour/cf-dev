# cf-dev/cf_src/appsinn/cf_finance/apps.py

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CfFinanceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "cf_finance"
    verbose_name = _("CF Finance")
