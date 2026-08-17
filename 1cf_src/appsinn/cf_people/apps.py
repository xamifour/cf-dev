# cf-dev/cf_src/appsinn/cf_people/apps.py

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CfPeopleConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "cf_people"
    verbose_name = _("CF People")
