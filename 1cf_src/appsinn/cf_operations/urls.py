# cf-dev/cf_src/appsinn/cf_operations/urls.py

"""Portal explore routes for events, sermons, and outreaches."""

from django.urls import path

from . import views

app_name = "cf_operations"

urlpatterns = [
    path("events/", views.EventListView.as_view(), name="event_list"),
    path("events/<uuid:pk>/", views.EventDetailView.as_view(), name="event_detail"),
    path("sermons/", views.SermonListView.as_view(), name="sermon_list"),
    path("sermons/<uuid:pk>/", views.SermonDetailView.as_view(), name="sermon_detail"),
    path("outreaches/", views.OutreachListView.as_view(), name="outreach_list"),
]
