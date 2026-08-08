# cf-dev/cf_src/appsinn/cf_operations/api/serializers.py

"""DRF serializers for cf_operations (scale-oriented field sets)."""

from rest_framework import serializers

from cf_operations.models import (
    AttendanceRecord,
    Event,
    EventSession,
    Sermon,
)

class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ("id", "title", "event_type", "branch", "visibility", "start_time", "end_time")
        read_only_fields = ("id",)

class EventSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventSession
        fields = ("id", "name", "event", "start_day", "start_time", "end_day", "end_time", "is_active")
        read_only_fields = ("id",)

class SermonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sermon
        fields = ("id", "title", "branch", "visibility", "event")
        read_only_fields = ("id",)

class AttendanceRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceRecord
        fields = (
            "id",
            "event",
            "session",
            "branch",
            "zone",
            "subgroup",
            "week",
            "month",
            "attendance_at",
            "code",
            "centre_name",
            "leader",
            "address",
            "phone_number",
            "location_provider",
            "fill_from_scope",
        )
        read_only_fields = ("id",)

