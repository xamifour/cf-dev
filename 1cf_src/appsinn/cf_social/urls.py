# cf-dev/cf_src/appsinn/cf_social/urls.py

from django.urls import path

from . import views

app_name = "cf_social"

urlpatterns = [
    path("", views.FeedView.as_view(), name="feed"),
    path("posts/<uuid:pk>/", views.PostDetailView.as_view(), name="post_detail"),
    path("posts/<uuid:pk>/like/", views.LikeToggleView.as_view(), name="like_toggle"),
    path("posts/<uuid:pk>/delete/", views.PostDeleteView.as_view(), name="post_delete"),
    path("discussions/", views.DiscussionListView.as_view(), name="discussion_list"),
    path(
        "discussions/new/",
        views.DiscussionCreateView.as_view(),
        name="discussion_create",
    ),
    path(
        "discussions/<uuid:pk>/",
        views.DiscussionDetailView.as_view(),
        name="discussion_detail",
    ),
    path("u/<str:username>/", views.ProfileView.as_view(), name="profile"),
    path("u/<str:username>/follow/", views.FollowToggleView.as_view(), name="follow_toggle"),
    path("u/<str:username>/message/", views.StartMessageView.as_view(), name="start_message"),
    path("u/<str:username>/block/", views.BlockToggleView.as_view(), name="block_toggle"),
    path("settings/profile/", views.ProfileEditView.as_view(), name="profile_edit"),
    path("search/", views.SearchView.as_view(), name="search"),
    path("notifications/", views.NotificationsView.as_view(), name="notifications"),
    path("messages/", views.InboxView.as_view(), name="inbox"),
    path("messages/<uuid:pk>/", views.ConversationView.as_view(), name="conversation"),
    path("report/", views.ReportCreateView.as_view(), name="report"),
]
