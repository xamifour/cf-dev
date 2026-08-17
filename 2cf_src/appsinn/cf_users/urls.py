# cf-dev/cf_src/appsinn/cf_users/urls.py

"""URL routes for the organisation portal."""

from django.urls import path

from .views import (
    PortalDashboardView,
    PortalLoginView,
    PortalLogoutView,
    SwitchBranchView,
    SwitchOrganizationView,
)

urlpatterns = [
    path("", PortalLoginView.as_view(), name="portal_login"),
    path("login/", PortalLoginView.as_view(), name="portal_login_alt"),
    path("logout/", PortalLogoutView.as_view(), name="portal_logout"),
    path("dashboard/", PortalDashboardView.as_view(), name="portal_dashboard"),
    path(
        "tenant/organization/",
        SwitchOrganizationView.as_view(),
        name="portal_switch_organization",
    ),
    path(
        "tenant/branch/",
        SwitchBranchView.as_view(),
        name="portal_switch_branch",
    ),
]
