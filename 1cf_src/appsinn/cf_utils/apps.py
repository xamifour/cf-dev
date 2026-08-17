# cf-dev/cf_src/appsinn/cf_utils/apps.py

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CfUtilsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "cf_utils"
    verbose_name = _("CF Utilities")

    def ready(self) -> None:
        # Admin theme assets: cf_utils/static/cf_utils/admin_theme/
        # Templates: cf_utils/templates/admin/{base_site,index}.html
        # (loaded because cf_utils is listed before django.contrib.admin)
        pass
