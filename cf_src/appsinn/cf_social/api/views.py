# cf-dev/cf_src/appsinn/cf_social/api/views.py

"""DRF viewsets for cf_social.

List endpoints use visibility / audience filters so they remain efficient under
platform-scale user volumes.
"""

from cf_social import settings as app_settings
from cf_social.api.serializers import (
    DiscussionSerializer,
    PostSerializer,
    SocialProfileSerializer,
)
from cf_social.models import Discussion, Post, SocialProfile
from cf_utils.api.viewsets import CFModelViewSet, CFReadOnlyModelViewSet


class SocialProfileViewSet(CFReadOnlyModelViewSet):
    """API for SocialProfile."""

    queryset = SocialProfile.objects.all()
    serializer_class = SocialProfileSerializer
    tenant_scoped = False
    select_related_fields = ("user",)

    def get_queryset(self):
        if not getattr(app_settings, "CF_SOCIAL_API_ENABLED", True):
            return SocialProfile.objects.none()
        return super().get_queryset().filter(is_active=True)


class PostViewSet(CFModelViewSet):
    """API for Post — visibility filtered for the requesting user."""

    queryset = Post.objects.all()
    serializer_class = PostSerializer
    tenant_scoped = False
    select_related_fields = ("author",)

    def get_queryset(self):
        if not getattr(app_settings, "CF_SOCIAL_API_ENABLED", True):
            return Post.objects.none()
        from cf_social import services

        return services.posts_visible_to(self.request.user).select_related(
            *self.select_related_fields
        )


class DiscussionViewSet(CFModelViewSet):
    """API for Discussion (audience-scoped via ``for_user``)."""

    queryset = Discussion.objects.all()
    serializer_class = DiscussionSerializer
    tenant_scoped = True
    select_related_fields = ("branch", "organization", "zone", "created_by")

    def get_queryset(self):
        if not getattr(app_settings, "CF_SOCIAL_API_ENABLED", True):
            return Discussion.objects.none()
        qs = super().get_queryset()
        if hasattr(qs, "active"):
            qs = qs.active()
        return qs
