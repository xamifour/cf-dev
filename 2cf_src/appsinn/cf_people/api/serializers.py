# cf-dev/cf_src/appsinn/cf_people/api/serializers.py

"""DRF serializers for cf_people (scale-oriented field sets)."""

from rest_framework import serializers

from cf_people.models import (
    Member,
    SubBranch,
    Visitor,
    Zone,
)

class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = ("id", "member_number", "branch", "membership_status")
        read_only_fields = ("id",)

class ZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Zone
        fields = ("id", "name", "code", "branch", "is_active")
        read_only_fields = ("id",)

class SubBranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubBranch
        fields = ("id", "name", "zone", "branch", "group_type", "is_active")
        read_only_fields = ("id",)

class VisitorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Visitor
        fields = (
            "id",
            "branch",
            "first_name",
            "last_name",
            "phone_number",
            "visit_date",
            "conversion_status",
        )
        read_only_fields = ("id",)

