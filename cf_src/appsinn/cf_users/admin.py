# cf-dev/cf_src/appsinn/cf_users/admin.py

"""Admin registrations for users and multitenant organisation models."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.translation import gettext_lazy as _

from .forms import OrganizationForm, UserChangeForm, UserCreationForm
from .models import (
    Branch,
    BranchUser,
    Organization,
    OrganizationGroup,
    OrganizationGroupMembership,
    OrganizationOwner,
    OrganizationUser,
    User,
)
from .multitenancy import MultitenantAdminMixin, MultitenantBranchFilter, MultitenantOrgFilter
from .utils import BaseAdmin


class UserOrganizationUserInline(admin.TabularInline):
    """Organisation membership for this user."""

    model = OrganizationUser
    fk_name = "user"
    extra = 0
    autocomplete_fields = ("organization",)
    verbose_name = _("organisation membership")
    verbose_name_plural = _("organisation memberships")
    fields = ("organization", "role", "is_org_manager", "is_admin")


class UserBranchUserInline(admin.TabularInline):
    """Branch membership for this user."""

    model = BranchUser
    fk_name = "user"
    extra = 0
    autocomplete_fields = ("branch",)
    verbose_name = _("branch membership")
    verbose_name_plural = _("branch memberships")
    fields = ("branch", "role", "is_org_manager")
    show_change_link = True


class UserOrganizationGroupMembershipInline(admin.TabularInline):
    """Organisation-group privileges for this user."""

    model = OrganizationGroupMembership
    fk_name = "user"
    extra = 0
    autocomplete_fields = ("group",)
    verbose_name = _("organisation group")
    verbose_name_plural = _("organisation groups (permissions)")
    fields = ("group",)


@admin.register(User)
class UserAdmin(MultitenantAdminMixin, DjangoUserAdmin):
    add_form = UserCreationForm
    form = UserChangeForm
    model = User
    ordering = ("-modified_at", "last_name", "first_name")
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "phone_number",
        "is_staff",
        "is_active",
        "is_church_staff",
    )
    list_filter = ("is_staff", "is_superuser", "is_active", "is_church_staff")
    search_fields = ("username", "email", "first_name", "last_name", "phone_number")
    readonly_fields = (
        "password_updated",
        "created_at",
        "modified_at",
        "last_login",
        "date_joined",
    )
    inlines = (
        UserOrganizationUserInline,
        UserBranchUserInline,
        UserOrganizationGroupMembershipInline,
    )

    fieldsets = (
        (None, {"classes": ("collapse",), "fields": ("username", "password")}),
        (
            _("Personal info"),
            {
                "classes": ("collapse",),
                "fields": (
                    "first_name",
                    "middle_name",
                    "last_name",
                    "email",
                    "phone_number",
                    "phone_number2",
                    "birth_date",
                    "gender",
                    "address",
                    "city",
                    "country",
                    "geo_address",
                    "language",
                    "bio",
                    "notes",
                ),
            },
        ),
        (
            _("Platform permissions (Django)"),
            {
                "classes": ("collapse",),
                "description": _(
                    "Platform flags and global Django groups. "
                    "Organisation / branch access is managed in the inlines below "
                    "(organisation memberships, branch memberships, organisation groups)."
                ),
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "is_church_staff",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (
            _("Notifications"),
            {
                "classes": ("collapse",),
                "fields": (
                    "notify_via_inapp",
                    "notify_via_email",
                    "notify_via_sms",
                    "notify_via_whatsapp",
                ),
            },
        ),
        (
            _("Important dates"),
            {
                "classes": ("collapse",),
                "fields": ("last_login", "date_joined", "password_updated"),
            },
        ),
        (
            _("Audit"),
            {
                "classes": ("collapse",),
                "fields": ("created_at", "modified_at", "created_by", "modified_by"),
            },
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "email",
                    "phone_number",
                    "first_name",
                    "last_name",
                    "address",
                    "city",
                    "country",
                    "password1",
                    "password2",
                    "is_staff",
                    "is_active",
                ),
                "description": _(
                    "After creating the user, open them and assign organisation / "
                    "branch memberships and groups as needed."
                ),
            },
        ),
    )


class OrganizationUserInline(admin.TabularInline):
    model = OrganizationUser
    extra = 0
    autocomplete_fields = ("user",)


class BranchInline(admin.TabularInline):
    model = Branch
    extra = 0
    show_change_link = True
    fields = ("name", "branch_type", "active", "is_default", "city", "country")


@admin.register(Organization)
class OrganizationAdmin(MultitenantAdminMixin, BaseAdmin):
    form = OrganizationForm
    list_display = ("name", "trade_name", "code", "city", "country", "is_active")
    list_filter = ("is_active", "country")
    search_fields = ("name", "trade_name", "code", "email")
    prepopulated_fields = {}
    readonly_fields = ("code", "slug", "created_at", "modified_at")
    inlines = [BranchInline, OrganizationUserInline]
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "trade_name",
                    "code",
                    "email",
                    "phone_number",
                    "url",
                    "description",
                    "is_active",
                )
            },
        ),
        (
            _("Location"),
            {"fields": ("address", "city", "country", "geo_address")},
        ),
        (
            _("Branding"),
            {
                "classes": ("collapse",),
                "fields": ("logo", "logo_svg", "theme_color"),
            },
        ),
        (
            _("Birthday messages"),
            {
                "description": _(
                    "Type the automatic birthday greeting for people in this "
                    "organisation. Branches may override. Placeholders: "
                    "{name}, {org}, {branch}, {year}."
                ),
                "fields": (
                    "birthday_greetings_enabled",
                    "birthday_subject",
                    "birthday_message",
                    "notifications_enabled",
                ),
            },
        ),
        (
            _("Notes & audit"),
            {
                "classes": ("collapse",),
                "fields": ("notes", "slug", "created_at", "modified_at"),
            },
        ),
    )


@admin.register(OrganizationUser)
class OrganizationUserAdmin(MultitenantAdminMixin, BaseAdmin):
    list_display = ("user", "organization", "role", "is_org_manager", "is_admin")
    list_filter = (MultitenantOrgFilter, "role", "is_org_manager")
    search_fields = ("user__username", "user__email", "organization__name")
    autocomplete_fields = ("user", "organization")


@admin.register(OrganizationOwner)
class OrganizationOwnerAdmin(MultitenantAdminMixin, BaseAdmin):
    list_display = ("organization", "organization_user")
    search_fields = ("organization__name", "organization_user__user__username")
    autocomplete_fields = ("organization", "organization_user")


class BranchUserInline(admin.TabularInline):
    model = BranchUser
    extra = 0
    autocomplete_fields = ("user",)


@admin.register(Branch)
class BranchAdmin(MultitenantAdminMixin, BaseAdmin):
    list_display = ("name", "organization", "branch_type", "active", "is_default", "city")
    list_filter = (MultitenantOrgFilter, "branch_type", "active", "is_default")
    search_fields = ("name", "organization__name", "city")
    readonly_fields = ("slug", "created_at", "modified_at")
    autocomplete_fields = ("organization",)
    inlines = [BranchUserInline]
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "organization",
                    "name",
                    "branch_type",
                    "active",
                    "is_default",
                    "description",
                )
            },
        ),
        (
            _("Location"),
            {"fields": ("address", "city", "country", "geo_address")},
        ),
        (
            _("Birthday messages"),
            {
                "description": _(
                    "Optional override of the organisation birthday text for this "
                    "branch only. Leave blank to inherit. Placeholders: "
                    "{name}, {org}, {branch}, {year}."
                ),
                "fields": (
                    "birthday_greetings_enabled",
                    "birthday_subject",
                    "birthday_message",
                    "notifications_enabled",
                ),
            },
        ),
        (
            _("Audit"),
            {
                "classes": ("collapse",),
                "fields": ("slug", "created_at", "modified_at"),
            },
        ),
    )


@admin.register(BranchUser)
class BranchUserAdmin(MultitenantAdminMixin, BaseAdmin):
    list_display = ("user", "branch", "role", "is_org_manager")
    list_filter = (MultitenantBranchFilter, "role", "is_org_manager")
    search_fields = ("user__username", "branch__name")
    autocomplete_fields = ("user", "branch")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # BranchUser.save already ensures org membership; re-run for safety.
        obj.ensure_organization_membership()


class OrganizationGroupMembershipInline(admin.TabularInline):
    model = OrganizationGroupMembership
    extra = 0
    autocomplete_fields = ("user",)
    show_change_link = True


@admin.register(OrganizationGroup)
class OrganizationGroupAdmin(MultitenantAdminMixin, BaseAdmin):
    list_display = (
        "name",
        "organization",
        "is_default",
        "is_active",
        "permission_count",
        "member_count",
    )
    list_filter = (MultitenantOrgFilter, "is_default", "is_active")
    search_fields = ("name", "description", "organization__name")
    autocomplete_fields = ("organization",)
    filter_horizontal = ("permissions",)
    inlines = [OrganizationGroupMembershipInline]
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "organization",
                    "name",
                    "description",
                    "is_default",
                    "is_active",
                ),
                "description": _(
                    "Organisation-specific groups control privileges for that "
                    "organisation only. Mark a group as default so new branch "
                    "users are added automatically."
                ),
            },
        ),
        (
            _("Privileges"),
            {"fields": ("permissions",)},
        ),
    )

    @admin.display(description=_("permissions"))
    def permission_count(self, obj):
        return obj.permissions.count()

    @admin.display(description=_("members"))
    def member_count(self, obj):
        return obj.memberships.count()


@admin.register(OrganizationGroupMembership)
class OrganizationGroupMembershipAdmin(MultitenantAdminMixin, BaseAdmin):
    multitenant_parent = "group"
    multitenant_shared_relations = ["group"]
    list_display = ("user", "group", "organization_name", "created_at")
    list_filter = ("group__organization",)
    search_fields = (
        "user__username",
        "user__email",
        "group__name",
        "group__organization__name",
    )
    autocomplete_fields = ("user", "group")

    @admin.display(description=_("organisation"))
    def organization_name(self, obj):
        return obj.group.organization
