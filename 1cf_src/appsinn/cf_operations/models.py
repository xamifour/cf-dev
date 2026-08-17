# cf-dev/cf_src/appsinn/cf_operations/models.py

"""Concrete operations domain models."""

from django.utils.translation import gettext_lazy as _

from cf_users.managers import TenantManager

from .base.models import (
    AbstractAttendanceRecord,
    AbstractAttendanceSeat,
    AbstractDocument,
    AbstractDocumentCategory,
    AbstractEvent,
    AbstractEventSession,
    AbstractSermon,
)


class Event(AbstractEvent):
    objects = TenantManager()

    class Meta(AbstractEvent.Meta):
        abstract = False
        verbose_name = _("event")
        verbose_name_plural = _("events")


class EventSession(AbstractEventSession):
    """Named session under an Event (e.g. 1st / 2nd service)."""

    objects = TenantManager()

    class Meta(AbstractEventSession.Meta):
        abstract = False
        verbose_name = _("event session")
        verbose_name_plural = _("event sessions")


class Sermon(AbstractSermon):
    objects = TenantManager()

    class Meta(AbstractSermon.Meta):
        abstract = False
        verbose_name = _("sermon")
        verbose_name_plural = _("sermons")


class AttendanceRecord(AbstractAttendanceRecord):
    """Attendance for an event (optional session / zone / subgroup / week)."""

    objects = TenantManager()

    class Meta(AbstractAttendanceRecord.Meta):
        abstract = False
        verbose_name = _("attendance record")
        verbose_name_plural = _("attendance records")


class AttendanceSeat(AbstractAttendanceSeat):
    """Headcount seat (MA/FA/MC/FC/…) for one attendance record."""

    objects = TenantManager(tenant_parent_field="record")

    class Meta(AbstractAttendanceSeat.Meta):
        abstract = False


class DocumentCategory(AbstractDocumentCategory):
    objects = TenantManager()

    class Meta(AbstractDocumentCategory.Meta):
        abstract = False
        verbose_name = _("document category")
        verbose_name_plural = _("document categories")


class Document(AbstractDocument):
    objects = TenantManager()

    class Meta(AbstractDocument.Meta):
        abstract = False
        verbose_name = _("document")
        verbose_name_plural = _("documents")
