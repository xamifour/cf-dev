# cf-dev/cf_src/appsinn/cf_users/api/urls.py

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from cf_users.api import views

app_name = "cf_users_api"

router = DefaultRouter()
router.register(r"organizations", views.OrganizationViewSet, basename="organizations")
router.register(r"branches", views.BranchViewSet, basename="branches")

urlpatterns = [
    path("", include(router.urls)),
]
