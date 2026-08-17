# cf-dev/cf_src/appsinn/cf_people/admin.py

"""Admin registrations for people domain models."""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from cf_users.multitenancy import MultitenantAdminMixin, MultitenantBranchFilter
from cf_users.utils import BaseAdmin

from .forms import SubBranchAdminForm, SubBranchInlineForm
from .models import (
    ChildProfile,
    Department,
    DepartmentMember,
    Family,
    FollowUp,
    Guardian,
    Member,
    SubBranch,
    Visitor,
    Zone,
)


@admin.register(Family)
class FamilyAdmin(MultitenantAdminMixin, BaseAdmin):
    list_display = ("family_name", "branch", "primary_phone")
    list_filter = (MultitenantBranchFilter,)
    search_fields = ("family_name", "primary_phone")
    autocomplete_fields = ("branch",)


@admin.register(Member)
class MemberAdmin(MultitenantAdminMixin, BaseAdmin):
    list_display = (
        "member_number",
        "display_name",
        "branch",
        "membership_status",
        "user_gender",
        "user",
    )
    list_filter = (MultitenantBranchFilter, "membership_status", "user__gender")
    search_fields = (
        "member_number",
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
        "user__phone_number",
    )
    autocomplete_fields = ("branch", "user", "family")
    readonly_fields = (
        "organization",
        "member_number",
        "created_at",
        "modified_at",
    )
    fieldsets = (
        (
            _("Membership"),
            {
                "fields": (
                    "branch",
                    "organization",
                    "user",
                    "member_number",
                    "membership_status",
                    "family",
                ),
                "description": _(
                    "Member number is unique within the organisation and is "
                    "auto-generated if left blank."
                ),
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

    @admin.display(description=_("Gender"), ordering="user__gender")
    def user_gender(self, obj: Member) -> str:
        return getattr(obj.user, "get_gender_display", lambda: "")() or (
            getattr(obj.user, "gender", None) or "—"
        )

    @admin.display(description=_("Name"), ordering="user__last_name")
    def display_name(self, obj: Member) -> str:
        return obj.get_full_name()


@admin.register(ChildProfile)
class ChildProfileAdmin(MultitenantAdminMixin, BaseAdmin):
    multitenant_parent = "member"
    list_display = ("member",)
    search_fields = (
        "member__user__first_name",
        "member__user__last_name",
        "member__member_number",
    )
    autocomplete_fields = ("member",)


@admin.register(Guardian)
class GuardianAdmin(MultitenantAdminMixin, BaseAdmin):
    multitenant_parent = "child"
    list_display = ("child", "guardian", "relationship_type")
    search_fields = (
        "child__user__first_name",
        "guardian__user__first_name",
        "relationship_type",
    )
    autocomplete_fields = ("child", "guardian")


@admin.register(Visitor)
class VisitorAdmin(MultitenantAdminMixin, BaseAdmin):
    list_display = (
        "first_name",
        "last_name",
        "branch",
        "visit_date",
        "conversion_status",
    )
    list_filter = (MultitenantBranchFilter, "conversion_status")
    search_fields = ("first_name", "last_name", "phone_number", "email")
    autocomplete_fields = ("branch", "invited_by")


@admin.register(FollowUp)
class FollowUpAdmin(MultitenantAdminMixin, BaseAdmin):
    multitenant_shared_relations = ["visitor", "assigned_to"]
    list_display = ("visitor", "assigned_to", "branch", "scheduled_date", "completed_date")
    list_filter = (MultitenantBranchFilter,)
    search_fields = (
        "visitor__first_name",
        "assigned_to__user__first_name",
        "assigned_to__user__last_name",
    )
    autocomplete_fields = ("branch", "visitor", "assigned_to")


@admin.register(Department)
class DepartmentAdmin(MultitenantAdminMixin, BaseAdmin):
    list_display = ("name", "branch", "is_active")
    list_filter = (MultitenantBranchFilter, "is_active")
    search_fields = ("name",)
    autocomplete_fields = ("branch",)


@admin.register(DepartmentMember)
class DepartmentMemberAdmin(MultitenantAdminMixin, BaseAdmin):
    multitenant_parent = "department"
    multitenant_shared_relations = ["department", "member"]
    list_display = ("department", "member", "role")
    search_fields = (
        "department__name",
        "member__user__first_name",
        "member__user__last_name",
    )
    autocomplete_fields = ("department", "member")


class SubBranchInline(admin.TabularInline):
    """
    Sub groups under a zone.

    Branch is not shown: it is always the parent zone's branch (set on save).
    """

    model = SubBranch
    form = SubBranchInlineForm
    extra = 1
    fields = ("name", "code", "group_type", "leader", "address", "location_provider", "is_active")
    autocomplete_fields = ("leader",)
    show_change_link = True
    ordering = ("-modified_at", "name")

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        # Limit leaders to members of this zone's branch (avoids invalid FK choice).
        leader_field = formset.form.base_fields.get("leader")
        if leader_field is not None and obj is not None and obj.branch_id:
            leader_field.queryset = Member.objects.filter(
                branch_id=obj.branch_id
            ).select_related("user")
        return formset

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "leader":
            parent_id = request.resolver_match.kwargs.get("object_id")
            if parent_id:
                zone = Zone.objects.filter(pk=parent_id).only("branch_id").first()
                if zone is not None:
                    kwargs["queryset"] = Member.objects.filter(
                        branch_id=zone.branch_id
                    ).select_related("user")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Zone)
class ZoneAdmin(MultitenantAdminMixin, BaseAdmin):
    list_display = ("name", "code", "branch", "leader", "is_active")
    list_filter = (MultitenantBranchFilter, "is_active")
    search_fields = ("name", "code", "address", "description")
    autocomplete_fields = ("branch", "leader")
    inlines = [SubBranchInline]
    fieldsets = (
        (
            None,
            {"fields": ("branch", "name", "code", "address", "is_active")},
        ),
        (
            _("Leadership"),
            {"fields": ("leader", "description")},
        ),
    )

    def save_formset(self, request, form, formset, change):
        """Ensure every sub group gets branch from this zone before insert."""
        instances = formset.save(commit=False)
        for obj in formset.deleted_objects:
            obj.delete()
        zone = form.instance
        for obj in instances:
            if isinstance(obj, SubBranch):
                obj.zone = zone
                obj.branch = zone.branch
            obj.save()
        formset.save_m2m()


@admin.register(SubBranch)
class SubBranchAdmin(MultitenantAdminMixin, BaseAdmin):
    form = SubBranchAdminForm
    multitenant_shared_relations = ["zone", "leader"]
    list_display = (
        "name",
        "code",
        "group_type",
        "zone",
        "branch",
        "leader",
        "is_active",
    )
    list_filter = (MultitenantBranchFilter, "group_type", "is_active")
    search_fields = ("name", "code", "zone__name", "address", "description")
    # Branch is derived from zone — do not show it as an editable choice field.
    autocomplete_fields = ("zone", "leader")
    readonly_fields = ("branch",)
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "zone",
                    "branch",
                    "name",
                    "code",
                    "group_type",
                    "leader",
                    "address",
                    "location_provider",
                    "is_active",
                    "description",
                ),
                "description": _(
                    "Hierarchy: Organisation → Branch → Zone → Sub group. "
                    "Pick a zone; branch is set automatically from that zone."
                ),
            },
        ),
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Ensure the currently selected zone stays in the queryset (tenant filter).
        zone_field = form.base_fields.get("zone")
        if zone_field is not None and obj is not None and obj.zone_id:
            zone_field.queryset = (
                zone_field.queryset | Zone.objects.filter(pk=obj.zone_id)
            ).distinct()
        return form

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "leader":
            # Prefer members of the zone's branch when zone is known from object.
            object_id = request.resolver_match.kwargs.get("object_id")
            if object_id:
                sg = (
                    SubBranch.objects.filter(pk=object_id)
                    .select_related("zone")
                    .first()
                )
                if sg is not None and sg.zone_id:
                    kwargs["queryset"] = Member.objects.filter(
                        branch_id=sg.zone.branch_id
                    ).select_related("user")
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        # Keep current leader in queryset so edit pages don't fail validation.
        if db_field.name == "leader" and field is not None:
            object_id = request.resolver_match.kwargs.get("object_id")
            if object_id:
                sg = SubBranch.objects.filter(pk=object_id).only("leader_id").first()
                if sg is not None and sg.leader_id:
                    field.queryset = (
                        field.queryset | Member.objects.filter(pk=sg.leader_id)
                    ).distinct()
        return field

    def save_model(self, request, obj, form, change):
        if obj.zone_id:
            obj.branch = obj.zone.branch
        super().save_model(request, obj, form, change)
