# cf-dev/cf_src/appsinn/cf_communications/api/urls.py

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from cf_communications.api import views

app_name = "cf_communications_api"

router = DefaultRouter()
router.register(r"notifications", views.NotificationViewSet, basename="notifications")
router.register(r"broadcasts", views.BroadcastMessageViewSet, basename="broadcasts")

urlpatterns = [
    path("", include(router.urls)),
]
