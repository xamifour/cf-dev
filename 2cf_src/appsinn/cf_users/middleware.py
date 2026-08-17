# cf-dev/cf_src/appsinn/cf_users/middleware.py

"""Request middleware for password policy, tenant context, and host routing."""

from django.contrib import messages
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.http import HttpResponseNotFound, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import resolve, reverse_lazy
from django.utils.translation import gettext_lazy as _

from .audit import clear_current_user, set_current_user
from .tenancy import bind_tenant_from_session, clear_active_tenant_ids


class AuditUserMiddleware:
    """
    Bind the authenticated request user for AuditMixin stamps.

    Must run after AuthenticationMiddleware. Ensures ``created_by`` /
    ``modified_by`` are set on every model save during the request.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and getattr(user, "is_authenticated", False):
            set_current_user(user)
        else:
            clear_current_user()
        try:
            return self.get_response(request)
        finally:
            clear_current_user()


class TenantContextMiddleware:
    """
    Bind active organisation/branch onto the request and contextvars.

    Must run after AuthenticationMiddleware. Enables scale-safe default scoping
    without loading every tenant key into memory.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        bind_tenant_from_session(request)
        try:
            return self.get_response(request)
        finally:
            clear_active_tenant_ids()


class PasswordExpirationMiddleware:
    """Force authenticated users with expired passwords to change them."""

    exempted_url_names = [
        "account_change_password",
        "admin:logout",
        "admin:login",
        "account_logout",
        "account_reset_password",
        "account_reset_password_done",
        "account_reset_password_from_key",
        "account_reset_password_from_key_done",
        "account_login",
        "portal_login",
        "portal_login_alt",
        "portal_logout",
    ]
    admin_login_path = reverse_lazy("admin:login")
    admin_index_path = reverse_lazy("admin:index")
    account_change_password_path = reverse_lazy("account_change_password")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            getattr(request, "user", None) is not None
            and request.user.is_authenticated
            and hasattr(request.user, "has_password_expired")
            and request.user.has_password_expired()
        ):
            try:
                url_name = resolve(request.path).url_name
            except Exception:  # noqa: BLE001
                url_name = None

            if url_name not in self.exempted_url_names:
                messages.warning(
                    request,
                    _("Your password has expired, please update your password."),
                )
                redirect_path = str(self.account_change_password_path)
                if request.user.is_staff:
                    next_path = (
                        request.path
                        if request.path != str(self.admin_login_path)
                        else str(self.admin_index_path)
                    )
                    redirect_path = f"{redirect_path}?{REDIRECT_FIELD_NAME}={next_path}"
                return redirect(redirect_path)

        return self.get_response(request)


class DomainBasedRoutingMiddleware:
    """
    Optional host-based surface routing for multi-hostname deployments.

    Disabled by default (not registered in settings). Enable only when the
    deployment hostnames match the configured product surfaces.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(":")[0]
        path = request.path

        if host == "ops.example.com" and path == "/":
            return HttpResponseRedirect("/admin/")

        if host == "portal.example.com" and path.startswith("/admin"):
            return HttpResponseNotFound("Not Found")

        if host == "ops.example.com" and not path.startswith("/admin"):
            return HttpResponseNotFound("Not Found")

        if host in {"example.com", "www.example.com"} and path == "/":
            return HttpResponseRedirect("/admin/")

        return self.get_response(request)
