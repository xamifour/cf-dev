# cf-dev/cf_src/appsinn/cf_social/api/serializers.py

"""DRF serializers for cf_social (scale-oriented field sets)."""

from rest_framework import serializers

from cf_social.models import (
    Discussion,
    Post,
    SocialProfile,
)

class SocialProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialProfile
        fields = ("id", "user", "display_name", "profile_visibility", "is_active")
        read_only_fields = ("id",)

class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ("id", "author", "body", "visibility", "likes_count", "comments_count", "created_at")
        read_only_fields = ("id",)

class DiscussionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Discussion
        fields = ("id", "title", "audience", "organization", "branch", "zone", "is_active", "is_locked", "messages_count")
        read_only_fields = ("id",)

