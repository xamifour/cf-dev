# cf-dev/cf_src/appsinn/cf_communications/api/serializers.py

"""DRF serializers for cf_communications (scale-oriented field sets)."""

from rest_framework import serializers

from cf_communications.models import (
    BroadcastMessage,
    Notification,
)

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = (
            "id",
            "organization",
            "branch",
            "recipient",
            "notification_type",
            "title",
            "message",
            "seen",
        )
        read_only_fields = ("id",)


class BroadcastMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = BroadcastMessage
        fields = (
            "id",
            "organization",
            "title",
            "body",
            "status",
            "target_all",
        )
        read_only_fields = ("id",)

