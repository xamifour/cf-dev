# cf-dev/cf_src/appsinn/cf_users/api/views.py

"""DRF viewsets for cf_users.

Querysets are tenant-scoped via ``for_user`` when available so list
endpoints stay efficient under multi-org / multi-million-user loads.
"""

from cf_users import settings as app_settings
from cf_users.models import (
    Branch,
    Organization,
)
from cf_users.api.serializers import (
    OrganizationSerializer,
    BranchSerializer,
)
from cf_utils.api.viewsets import CFModelViewSet, CFReadOnlyModelViewSet

class OrganizationViewSet(CFModelViewSet):
    """API for Organization. """
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    tenant_scoped = True
    select_related_fields = ()

    def get_queryset(self):
        if not getattr(app_settings, "CF_USERS_API_ENABLED", True):
            return Organization.objects.none()
        return super().get_queryset()

class BranchViewSet(CFModelViewSet):
    """API for Branch. """
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer
    tenant_scoped = True
    select_related_fields = ('organization',)

    def get_queryset(self):
        if not getattr(app_settings, "CF_USERS_API_ENABLED", True):
            return Branch.objects.none()
        return super().get_queryset()

