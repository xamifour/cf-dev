# cf-dev/cf_src/appsinn/cf_utils/api/urls.py

"""Utility app has no resource endpoints; reserved for future health checks."""

from django.urls import path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

app_name = "cf_utils_api"


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    return Response({"status": "ok", "service": "cf"})


urlpatterns = [
    path("health/", health, name="health"),
]
