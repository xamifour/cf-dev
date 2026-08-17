# cf-dev/cf_src/appsinn/gmtisp_communications/routing.py

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'^ws/notifications/$', consumers.NotificationConsumer.as_asgi()),
]