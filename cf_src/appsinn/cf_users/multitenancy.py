# cf-dev/cf_src/appsinn/cf_users/multitenancy.py

"""Admin multitenancy helpers for organisation/branch isolation."""

from __future__ import annotations

from django import forms
from django.apps import apps
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import FieldDoesNotExist
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class MultitenantAdminMixin:
    """
    Makes ModelAdmin branch/organisation-aware.

    Non-superusers can only see objects belonging to their accessible branches
    or managed organisations. Prefer model managers' ``for_user`` when available.

    Permission checks honour Django permissions including those granted via
    organisation groups (``OrganizationGroupBackend``).
    """

    multitenant_shared_relations: list[str] = []
    multitenant_parent: str | None = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if (
            self.multitenant_parent
            and self.multitenant_parent not in self.multitenant_shared_relations
        ):
            self.multitenant_shared_relations = list(self.multitenant_shared_relations)
            self.multitenant_shared_relations.append(self.multitenant_parent)

    def _opts_perm(self, action: str) -> str:
        opts = self.model._meta
        return f"{opts.app_label}.{action}_{opts.model_name}"

    def _has_model_perm(self, request, action: str) -> bool:
        """Django model perm (global groups or organisation groups)."""
        user = request.user
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return user.has_perm(self._opts_perm(action))

    def _object_in_tenant_scope(self, request, obj) -> bool:
        if obj is None:
            return True
        return self.get_queryset(request).filter(pk=obj.pk).exists()

    def has_module_permission(self, request):
        if request.user.is_superuser:
            return True
        # Staff + any model perm on this app, or org-group module perms.
        if request.user.is_staff and super().has_module_permission(request):
            return True
        return request.user.has_module_perms(self.opts.app_label)

    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if not (
            self._has_model_perm(request, "view")
            or self._has_model_perm(request, "change")
            or super().has_view_permission(request, obj)
        ):
            return False
        return self._object_in_tenant_scope(request, obj)

    def has_add_permission(self, request):
        if request.user.is_superuser:
            return True
        return self._has_model_perm(request, "add") or super().has_add_permission(
            request
        )

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if not (
            self._has_model_perm(request, "change")
            or super().has_change_permission(request, obj)
        ):
            return False
        return self._object_in_tenant_scope(request, obj)

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if not (
            self._has_model_perm(request, "delete")
            or super().has_delete_permission(request, obj)
        ):
            return False
        return self._object_in_tenant_scope(request, obj)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        user = request.user

        if user.is_superuser:
            return qs

        manager = getattr(self.model, "objects", None)
        if manager is not None and hasattr(manager, "for_user"):
            return manager.for_user(user)

        if self.model == User:
            return self._queryset_for_user_admin(request, qs)

        if hasattr(self.model, "branch"):
            return self._filter_by_branch(qs, user)

        if hasattr(self.model, "organization"):
            from .tenancy import organizations_for_user_qs  # noqa: PLC0415

            return qs.filter(
                organization_id__in=organizations_for_user_qs(user).values("id")
            )

        if self.model.__name__ == "Organization":
            from .tenancy import organizations_for_user_qs  # noqa: PLC0415

            return organizations_for_user_qs(user)

        if self.multitenant_parent:
            return self._filter_via_parent(qs, user)

        return qs.none()

    def _filter_by_branch(self, qs, user):
        from .tenancy import accessible_branch_ids_qs  # noqa: PLC0415

        return qs.filter(branch_id__in=accessible_branch_ids_qs(user))

    def _filter_via_parent(self, qs, user):
        from .tenancy import (  # noqa: PLC0415
            accessible_branch_ids_qs,
            managed_organization_ids_qs,
        )

        try:
            parent_field = self.model._meta.get_field(self.multitenant_parent)
        except FieldDoesNotExist:
            return qs.none()

        parent_model = parent_field.remote_field.model

        if hasattr(parent_model, "branch") or self._model_has_field(
            parent_model, "branch"
        ):
            return qs.filter(
                **{
                    f"{self.multitenant_parent}__branch_id__in": accessible_branch_ids_qs(
                        user
                    )
                }
            )

        return qs.filter(
            **{
                f"{self.multitenant_parent}__organization_id__in": managed_organization_ids_qs(
                    user
                )
            }
        )

    @staticmethod
    def _model_has_field(model, name: str) -> bool:
        try:
            model._meta.get_field(name)
            return True
        except Exception:
            return False

    def _queryset_for_user_admin(self, request, qs):
        """Users in shared orgs/branches — not only managed-org peers."""
        from .tenancy import users_visible_to_user_qs  # noqa: PLC0415

        return users_visible_to_user_qs(request.user)

    def _restrict_form_fields(self, request, form):
        if not hasattr(form, "base_fields"):
            return
        if request.user.is_superuser:
            return
        fields = form.base_fields
        user = request.user
        from .tenancy import (  # noqa: PLC0415
            accessible_branch_ids_qs,
            organizations_for_user_qs,
            users_visible_to_user_qs,
        )

        org_field = fields.get("organization")
        if org_field and isinstance(org_field, forms.ModelChoiceField):
            org_field.queryset = organizations_for_user_qs(user)
            org_field.required = True

        branch_field = fields.get("branch")
        if branch_field and isinstance(branch_field, forms.ModelChoiceField):
            branch_field.queryset = branch_field.queryset.filter(
                id__in=accessible_branch_ids_qs(user)
            )

        user_field = fields.get("user")
        if user_field and isinstance(user_field, forms.ModelChoiceField):
            user_field.queryset = users_visible_to_user_qs(user)

        for rel_name in self.multitenant_shared_relations:
            field = fields.get(rel_name)
            if not field or not isinstance(field, forms.ModelChoiceField):
                continue
            rel_model = field.queryset.model
            rel_manager = getattr(rel_model, "objects", None)
            if rel_manager is not None and hasattr(rel_manager, "for_user"):
                field.queryset = rel_manager.for_user(user)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        self._restrict_form_fields(request, form)
        return form

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        self._restrict_form_fields(request, formset.form)
        return formset

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        user = request.user
        from .tenancy import (  # noqa: PLC0415
            accessible_branch_ids_qs,
            organizations_for_user_qs,
            users_visible_to_user_qs,
        )

        # Superuser: never restrict FK choices (fixes invalid choice on memberships).
        if user.is_superuser:
            return super().formfield_for_foreignkey(db_field, request, **kwargs)

        if db_field.name == "organization":
            kwargs["queryset"] = organizations_for_user_qs(user)
            return super().formfield_for_foreignkey(db_field, request, **kwargs)

        if db_field.name == "branch":
            Branch = apps.get_model("cf_users", "Branch")
            kwargs["queryset"] = Branch.objects.filter(
                id__in=accessible_branch_ids_qs(user)
            )
            return super().formfield_for_foreignkey(db_field, request, **kwargs)

        related = getattr(db_field, "remote_field", None)
        related_model = getattr(related, "model", None) if related else None
        if related_model is not None and (
            related_model is User
            or getattr(related_model._meta, "model_name", "") == "user"
        ):
            kwargs["queryset"] = users_visible_to_user_qs(user)
            return super().formfield_for_foreignkey(db_field, request, **kwargs)

        if db_field.name in self.multitenant_shared_relations:
            related_model = db_field.remote_field.model
            manager = getattr(related_model, "objects", None)
            if manager is not None and hasattr(manager, "for_user"):
                kwargs["queryset"] = manager.for_user(user)
                return super().formfield_for_foreignkey(db_field, request, **kwargs)

        # OrganizationGroup FK (membership forms)
        if (
            related_model is not None
            and getattr(related_model._meta, "model_name", "") == "organizationgroup"
        ):
            OrganizationGroup = apps.get_model("cf_users", "OrganizationGroup")
            kwargs["queryset"] = OrganizationGroup.objects.for_user(user)
            return super().formfield_for_foreignkey(db_field, request, **kwargs)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class MultitenantOrgFilter(admin.SimpleListFilter):
    """Filter by Organisation — shows only organisations the user can access."""

    title = _("organisation")
    parameter_name = "organization"

    def lookups(self, request, model_admin):
        user = request.user
        Organization = apps.get_model("cf_users", "Organization")
        if user.is_superuser:
            orgs = Organization.objects.all()
        else:
            from .tenancy import organizations_for_user_qs  # noqa: PLC0415

            orgs = organizations_for_user_qs(user)
        return [(org.pk, str(org)) for org in orgs]

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(organization_id=value)
        return queryset


class MultitenantBranchFilter(admin.SimpleListFilter):
    """Filter by Branch — shows only branches the user can access."""

    title = _("branch")
    parameter_name = "branch"

    def lookups(self, request, model_admin):
        user = request.user
        Branch = apps.get_model("cf_users", "Branch")
        if user.is_superuser:
            branches = Branch.objects.all()
        else:
            branches = Branch.objects.filter(pk__in=user.accessible_branches)
        return [(b.pk, str(b)) for b in branches]

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(branch_id=value)
        return queryset
