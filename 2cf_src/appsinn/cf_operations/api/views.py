# cf-dev/cf_src/appsinn/cf_operations/api/views.py

"""DRF viewsets for cf_operations.

Querysets are tenant-scoped via ``for_user`` when available so list
endpoints stay efficient under multi-org / multi-million-user loads.
"""

from cf_operations import settings as app_settings
from cf_operations.models import (
    AttendanceRecord,
    Event,
    EventSession,
    Sermon,
)
from cf_operations.api.serializers import (
    EventSerializer,
    EventSessionSerializer,
    SermonSerializer,
    AttendanceRecordSerializer,
)
from cf_utils.api.viewsets import CFModelViewSet, CFReadOnlyModelViewSet

class EventViewSet(CFModelViewSet):
    """API for Event. """
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    tenant_scoped = True
    select_related_fields = ('branch',)

    def get_queryset(self):
        if not getattr(app_settings, "CF_OPERATIONS_API_ENABLED", True):
            return Event.objects.none()
        return super().get_queryset()

class EventSessionViewSet(CFModelViewSet):
    """API for EventSession. """
    queryset = EventSession.objects.all()
    serializer_class = EventSessionSerializer
    tenant_scoped = True
    select_related_fields = ('event',)

    def get_queryset(self):
        if not getattr(app_settings, "CF_OPERATIONS_API_ENABLED", True):
            return EventSession.objects.none()
        return super().get_queryset()

class SermonViewSet(CFModelViewSet):
    """API for Sermon. """
    queryset = Sermon.objects.all()
    serializer_class = SermonSerializer
    tenant_scoped = True
    select_related_fields = ('branch', 'event')

    def get_queryset(self):
        if not getattr(app_settings, "CF_OPERATIONS_API_ENABLED", True):
            return Sermon.objects.none()
        return super().get_queryset()

class AttendanceRecordViewSet(CFModelViewSet):
    """API for AttendanceRecord. """
    queryset = AttendanceRecord.objects.all()
    serializer_class = AttendanceRecordSerializer
    tenant_scoped = True
    select_related_fields = ('branch', 'event', 'zone')

    def get_queryset(self):
        if not getattr(app_settings, "CF_OPERATIONS_API_ENABLED", True):
            return AttendanceRecord.objects.none()
        return super().get_queryset()

