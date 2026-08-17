# cf-dev/cf_src/appsinn/cf_utils/api/serializers.py

"""Shared serializer helpers."""

from __future__ import annotations

from rest_framework import serializers


class AuditModelSerializer(serializers.ModelSerializer):
    """Expose AuditMixin fields as read-only on write APIs."""

    class Meta:
        abstract = True
        read_only_fields = (
            "id",
            "created_at",
            "modified_at",
            "created_by",
            "modified_by",
        )

    def create(self, validated_data):
        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None
        if user and user.is_authenticated:
            validated_data.setdefault("created_by", user)
            validated_data.setdefault("modified_by", user)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None
        if user and user.is_authenticated and hasattr(instance, "modified_by_id"):
            validated_data["modified_by"] = user
        return super().update(instance, validated_data)
