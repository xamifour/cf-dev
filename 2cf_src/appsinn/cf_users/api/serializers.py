# cf-dev/cf_src/appsinn/cf_users/api/serializers.py

"""DRF serializers for cf_users (scale-oriented field sets)."""

from rest_framework import serializers

from cf_users.models import (
    Branch,
    Organization,
)

class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ("id", "name", "code", "is_active")
        read_only_fields = ("id",)

class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ("id", "name", "organization", "is_active")
        read_only_fields = ("id",)

