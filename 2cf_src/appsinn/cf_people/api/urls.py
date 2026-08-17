# cf-dev/cf_src/appsinn/cf_people/api/urls.py

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from cf_people.api import views

app_name = "cf_people_api"

router = DefaultRouter()
router.register(r"members", views.MemberViewSet, basename="members")
router.register(r"zones", views.ZoneViewSet, basename="zones")
router.register(r"subgroups", views.SubBranchViewSet, basename="subgroups")
router.register(r"visitors", views.VisitorViewSet, basename="visitors")

urlpatterns = [
    path("", include(router.urls)),
]
