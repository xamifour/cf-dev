# cf-dev/cf_src/appsinn/cf_users/views.py

"""Portal authentication and organisation dashboard views."""

from __future__ import annotations

from django.apps import apps
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import TemplateView

from .forms import PortalAuthenticationForm


class PortalLoginView(LoginView):
    """
    Custom organisation portal login.

    Serves as the public landing page at ``/``. Authenticated users (including
    staff) are sent to the portal dashboard. Staff may also use ``/admin/``.
    """

    template_name = "cf_users/portal/login.html"
    authentication_form = PortalAuthenticationForm
    redirect_authenticated_user = True
    extra_context = {
        "page_title": _("Sign in"),
        "product_name": _("CF Organisation Portal"),
    }

    def get_success_url(self) -> str:
        redirect_to = self.get_redirect_url()
        if redirect_to:
            return redirect_to
        return reverse("portal_dashboard")

    def get_redirect_url(self) -> str:
        """Only allow safe same-host redirects for ``next``."""
        redirect_to = self.request.POST.get(
            self.redirect_field_name,
            self.request.GET.get(self.redirect_field_name, ""),
        )
        # Never bounce portal logins into the staff admin by default.
        if redirect_to.startswith("/admin"):
            return ""
        url_is_safe = url_has_allowed_host_and_scheme(
            url=redirect_to,
            allowed_hosts={self.request.get_host()},
            require_https=self.request.is_secure(),
        )
        return redirect_to if url_is_safe else ""

    def form_valid(self, form):
        """Log the user in and land on the organisation dashboard."""
        user = form.get_user()
        login(self.request, user)
        messages.success(
            self.request,
            _("Welcome back, %(name)s.")
            % {"name": user.get_full_name() or user.username},
        )
        return redirect(self.get_success_url())


class PortalLogoutView(LogoutView):
    """Log out of the organisation portal and return to the login page."""

    next_page = reverse_lazy("portal_login")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            messages.info(request, _("You have been signed out."))
        return super().dispatch(request, *args, **kwargs)


@method_decorator(login_required, name="dispatch")
class PortalDashboardView(TemplateView):
    """
    Organisation-scoped landing page after portal authentication.

    Lists and counts default to the **active** organisation/branch so dashboards
    stay bounded at multi-tenant scale.
    """

    template_name = "cf_users/portal/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        from .tenancy import (  # noqa: PLC0415
            branches_for_user_qs,
            organizations_for_user_qs,
        )

        # Switcher + cards: bounded querysets only.
        organizations = list(organizations_for_user_qs(user)[:50])
        active_org = getattr(self.request, "organization", None)
        branches = list(
            branches_for_user_qs(
                user, organization_id=getattr(active_org, "pk", None)
            )[:50]
        )

        member_count = 0
        event_count = 0
        sermon_count = 0
        outreach_count = 0
        recent_events = []
        recent_sermons = []
        try:
            Member = apps.get_model("cf_people", "Member")
            Event = apps.get_model("cf_operations", "Event")
            Sermon = apps.get_model("cf_operations", "Sermon")
            member_qs = Member.objects.for_active_tenant(user)
            # Fallback when no tenant context yet: user-scoped subquery filter.
            if not getattr(self.request, "branch", None) and not getattr(
                self.request, "organization", None
            ):
                member_qs = Member.objects.for_user(user)
            member_count = member_qs.count()

            # Platform explore: public content + org-private the user can access.
            event_qs = Event.objects.visible_to(user)
            sermon_qs = Sermon.objects.visible_to(user)
            event_count = event_qs.count()
            sermon_count = sermon_qs.count()
            outreach_count = event_qs.filter(event_type="OUTREACH").count()
            recent_events = list(
                event_qs.select_related("branch", "branch__organization").order_by(
                    "-start_time", "-created_at"
                )[:6]
            )
            recent_sermons = list(
                sermon_qs.select_related(
                    "branch", "speaker", "speaker__user"
                ).order_by("-modified_at", "-created_at")[:6]
            )
        except Exception:  # noqa: BLE001
            member_count = 0
            event_count = 0
            sermon_count = 0
            outreach_count = 0
            recent_events = []
            recent_sermons = []

        context.update(
            {
                "page_title": _("Dashboard"),
                "product_name": _("CF Organisation Portal"),
                "organizations": organizations,
                "branches": branches,
                "member_count": member_count,
                "event_count": event_count,
                "sermon_count": sermon_count,
                "outreach_count": outreach_count,
                "recent_events": recent_events,
                "recent_sermons": recent_sermons,
                "is_staff_user": user.is_staff or user.is_superuser,
                "active_organization": active_org,
                "active_branch": getattr(self.request, "branch", None),
            }
        )
        return context


@method_decorator(login_required, name="dispatch")
class SwitchOrganizationView(View):
    """POST: switch active organisation (scale-safe tenant context)."""

    def post(self, request, *args, **kwargs):
        from .tenancy import switch_organization  # noqa: PLC0415

        org_id = request.POST.get("organization_id")
        try:
            org = switch_organization(request, org_id)
            messages.success(
                request,
                _("Switched organisation to %(name)s.") % {"name": org},
            )
        except Exception as exc:  # noqa: BLE001
            messages.error(request, str(exc) or _("Unable to switch organisation."))
        next_url = request.POST.get("next") or reverse("portal_dashboard")
        return redirect(next_url)


@method_decorator(login_required, name="dispatch")
class SwitchBranchView(View):
    """POST: switch active branch (and its organisation)."""

    def post(self, request, *args, **kwargs):
        from .tenancy import switch_branch  # noqa: PLC0415

        branch_id = request.POST.get("branch_id")
        try:
            branch = switch_branch(request, branch_id)
            messages.success(
                request,
                _("Switched branch to %(name)s.") % {"name": branch},
            )
        except Exception as exc:  # noqa: BLE001
            messages.error(request, str(exc) or _("Unable to switch branch."))
        next_url = request.POST.get("next") or reverse("portal_dashboard")
        return redirect(next_url)
