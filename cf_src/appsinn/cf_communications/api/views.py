# cf-dev/cf_src/appsinn/cf_communications/api/views.py

"""DRF viewsets for cf_communications.

Querysets are tenant-scoped via ``for_user`` when available so list
endpoints stay efficient under multi-org / multi-million-user loads.
"""

from cf_communications import settings as app_settings
from cf_communications.models import (
    BroadcastMessage,
    Notification,
)
from cf_communications.api.serializers import (
    NotificationSerializer,
    BroadcastMessageSerializer,
)
from cf_utils.api.viewsets import CFModelViewSet, CFReadOnlyModelViewSet

class NotificationViewSet(CFModelViewSet):
    """API for Notification. """
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    tenant_scoped = True
    select_related_fields = ('branch',)

    def get_queryset(self):
        if not getattr(app_settings, "CF_COMMUNICATIONS_API_ENABLED", True):
            return Notification.objects.none()
        return super().get_queryset()

class BroadcastMessageViewSet(CFModelViewSet):
    """API for BroadcastMessage. """
    queryset = BroadcastMessage.objects.all()
    serializer_class = BroadcastMessageSerializer
    tenant_scoped = True
    select_related_fields = ('branch',)

    def get_queryset(self):
        if not getattr(app_settings, "CF_COMMUNICATIONS_API_ENABLED", True):
            return BroadcastMessage.objects.none()
        return super().get_queryset()

