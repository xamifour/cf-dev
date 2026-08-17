# cf-dev/cf_src/appsinn/cf_operations/api/urls.py

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from cf_operations.api import views

app_name = "cf_operations_api"

router = DefaultRouter()
router.register(r"events", views.EventViewSet, basename="events")
router.register(r"event-sessions", views.EventSessionViewSet, basename="event-sessions")
router.register(r"sermons", views.SermonViewSet, basename="sermons")
router.register(r"attendance-records", views.AttendanceRecordViewSet, basename="attendance-records")

urlpatterns = [
    path("", include(router.urls)),
]
