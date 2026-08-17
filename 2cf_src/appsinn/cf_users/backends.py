# cf-dev/cf_src/cf_users/backends.py

import phonenumbers
from django.contrib.auth.backends import BaseBackend, ModelBackend
from django.contrib.auth.models import Permission
from django.db.models import Q
from phonenumbers.phonenumberutil import NumberParseException

from . import settings as app_settings


class OrganizationGroupBackend(BaseBackend):
    """
    Grant Django permissions based on organisation-scoped groups.

    Complements ModelBackend: platform staff still use global groups; organisation
    users receive privileges from ``OrganizationGroup`` memberships.
    """

    def authenticate(self, request, **kwargs):
        return None  # authentication is handled by UsersAuthenticationBackend

    def _org_group_permissions(self, user_obj):
        if not user_obj or not user_obj.is_active or user_obj.is_anonymous:
            return set()
        if not hasattr(user_obj, "_org_group_perm_cache"):
            perms = Permission.objects.filter(
                organization_groups__memberships__user=user_obj,
                organization_groups__is_active=True,
            ).values_list("content_type__app_label", "codename")
            user_obj._org_group_perm_cache = {f"{a}.{c}" for a, c in perms}
        return user_obj._org_group_perm_cache

    def get_user_permissions(self, user_obj, obj=None):
        return set()

    def get_group_permissions(self, user_obj, obj=None):
        return self._org_group_permissions(user_obj)

    def get_all_permissions(self, user_obj, obj=None):
        return self._org_group_permissions(user_obj)

    def has_perm(self, user_obj, perm, obj=None):
        if not user_obj or not user_obj.is_active or user_obj.is_anonymous:
            return False
        if user_obj.is_superuser:
            return True
        return perm in self._org_group_permissions(user_obj)

    def has_module_perms(self, user_obj, app_label):
        if not user_obj or not user_obj.is_active or user_obj.is_anonymous:
            return False
        if user_obj.is_superuser:
            return True
        return any(
            p.startswith(f"{app_label}.") for p in self._org_group_permissions(user_obj)
        )


class UsersAuthenticationBackend(ModelBackend):
    """
    Custom authentication backend that allows users to log in using:
        - Username
        - Email address
        - Phone number (with flexible international/local formats)

    Superusers receive all permissions via ModelBackend (Django default).
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None

        for user in self.get_users(username):
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        return None

    def has_perm(self, user_obj, perm, obj=None):
        if user_obj and getattr(user_obj, "is_active", False) and user_obj.is_superuser:
            return True
        return super().has_perm(user_obj, perm, obj=obj)

    def has_module_perms(self, user_obj, app_label):
        if user_obj and getattr(user_obj, "is_active", False) and user_obj.is_superuser:
            return True
        return super().has_module_perms(user_obj, app_label)

    def get_users(self, identifier):
        """Return all users matching the identifier (username, email, or phone)."""
        if not identifier:
            return self.get_model().objects.none()

        conditions = Q(username=identifier) | Q(email__iexact=identifier)

        # Support phone number login
        for phone_number in self._get_phone_number_variations(identifier):
            conditions |= Q(phone_number=phone_number)

        return self.get_model().objects.filter(conditions)

    def _get_phone_number_variations(self, identifier):
        """Generate possible phone number formats with common prefixes."""
        if not identifier:
            return []

        prefixes = [""] + list(getattr(app_settings, "AUTH_BACKEND_AUTO_PREFIXES", []))
        candidates = [str(identifier)]

        # Handle numbers starting with 0 (common local format)
        if str(identifier).startswith("0"):
            candidates.append(str(identifier)[1:])

        valid_numbers = []
        for prefix in prefixes:
            for number in candidates:
                value = f"{prefix}{number}".strip()
                try:
                    phonenumbers.parse(value)
                    valid_numbers.append(value)
                except NumberParseException:
                    continue

        return valid_numbers

    def get_model(self):
        """Return the active User model."""
        from django.contrib.auth import get_user_model
        return get_user_model()
        