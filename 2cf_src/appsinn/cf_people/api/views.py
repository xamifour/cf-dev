# cf-dev/cf_src/appsinn/cf_people/api/views.py

"""DRF viewsets for cf_people.

Querysets are tenant-scoped via ``for_user`` when available so list
endpoints stay efficient under multi-org / multi-million-user loads.
"""

from cf_people import settings as app_settings
from cf_people.models import (
    Member,
    SubBranch,
    Visitor,
    Zone,
)
from cf_people.api.serializers import (
    MemberSerializer,
    ZoneSerializer,
    SubBranchSerializer,
    VisitorSerializer,
)
from cf_utils.api.viewsets import CFModelViewSet, CFReadOnlyModelViewSet

class MemberViewSet(CFModelViewSet):
    """API for Member. """
    queryset = Member.objects.all()
    serializer_class = MemberSerializer
    tenant_scoped = True
    select_related_fields = ('branch',)

    def get_queryset(self):
        if not getattr(app_settings, "CF_PEOPLE_API_ENABLED", True):
            return Member.objects.none()
        return super().get_queryset()

class ZoneViewSet(CFModelViewSet):
    """API for Zone. """
    queryset = Zone.objects.all()
    serializer_class = ZoneSerializer
    tenant_scoped = True
    select_related_fields = ('branch',)

    def get_queryset(self):
        if not getattr(app_settings, "CF_PEOPLE_API_ENABLED", True):
            return Zone.objects.none()
        return super().get_queryset()

class SubBranchViewSet(CFModelViewSet):
    """API for SubBranch. """
    queryset = SubBranch.objects.all()
    serializer_class = SubBranchSerializer
    tenant_scoped = True
    select_related_fields = ('branch', 'zone')

    def get_queryset(self):
        if not getattr(app_settings, "CF_PEOPLE_API_ENABLED", True):
            return SubBranch.objects.none()
        return super().get_queryset()

class VisitorViewSet(CFModelViewSet):
    """API for Visitor. """
    queryset = Visitor.objects.all()
    serializer_class = VisitorSerializer
    tenant_scoped = True
    select_related_fields = ('branch',)

    def get_queryset(self):
        if not getattr(app_settings, "CF_PEOPLE_API_ENABLED", True):
            return Visitor.objects.none()
        return super().get_queryset()

