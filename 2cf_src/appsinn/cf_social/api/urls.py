# cf-dev/cf_src/appsinn/cf_social/api/urls.py

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from cf_social.api import views

app_name = "cf_social_api"

router = DefaultRouter()
router.register(r"profiles", views.SocialProfileViewSet, basename="profiles")
router.register(r"posts", views.PostViewSet, basename="posts")
router.register(r"discussions", views.DiscussionViewSet, basename="discussions")

urlpatterns = [
    path("", include(router.urls)),
]
