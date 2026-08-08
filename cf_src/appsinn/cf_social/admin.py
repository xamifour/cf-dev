# cf-dev/cf_src/appsinn/cf_social/admin.py

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from cf_users.utils import BaseAdmin

from .models import (
    Block,
    Comment,
    Conversation,
    DirectMessage,
    Discussion,
    DiscussionMessage,
    Follow,
    Post,
    PostLike,
    Report,
    SocialNotification,
    SocialProfile,
)


@admin.register(SocialProfile)
class SocialProfileAdmin(BaseAdmin):
    list_display = (
        "user",
        "display_name",
        "profile_visibility",
        "allow_direct_messages",
        "is_active",
    )
    list_filter = ("profile_visibility", "is_active")
    search_fields = (
        "user__username",
        "user__email",
        "display_name",
        "bio",
    )
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at", "modified_at")


@admin.register(Follow)
class FollowAdmin(BaseAdmin):
    list_display = ("follower", "following", "created_at")
    search_fields = ("follower__username", "following__username")
    autocomplete_fields = ("follower", "following")


@admin.register(Post)
class PostAdmin(BaseAdmin):
    list_display = (
        "author",
        "short_body",
        "visibility",
        "likes_count",
        "comments_count",
        "is_hidden",
        "created_at",
    )
    list_filter = ("visibility", "is_hidden", "created_at")
    search_fields = ("body", "author__username")
    autocomplete_fields = ("author",)
    actions = ("hide_posts", "unhide_posts")

    @admin.display(description=_("body"))
    def short_body(self, obj):
        return (obj.body or "")[:60]

    @admin.action(description=_("Hide selected posts"))
    def hide_posts(self, request, queryset):
        queryset.update(is_hidden=True)

    @admin.action(description=_("Unhide selected posts"))
    def unhide_posts(self, request, queryset):
        queryset.update(is_hidden=False)


@admin.register(PostLike)
class PostLikeAdmin(BaseAdmin):
    list_display = ("user", "post", "created_at")
    autocomplete_fields = ("user", "post")


@admin.register(Comment)
class CommentAdmin(BaseAdmin):
    list_display = ("author", "post", "short_body", "is_hidden", "created_at")
    list_filter = ("is_hidden",)
    search_fields = ("body", "author__username")
    autocomplete_fields = ("author", "post", "parent")

    @admin.display(description=_("body"))
    def short_body(self, obj):
        return (obj.body or "")[:60]


class DirectMessageInline(admin.TabularInline):
    model = DirectMessage
    extra = 0
    readonly_fields = ("sender", "body", "is_read", "created_at")
    can_delete = False


@admin.register(Conversation)
class ConversationAdmin(BaseAdmin):
    list_display = ("id", "last_message_at", "created_at")
    search_fields = ("id", "participants__username")
    filter_horizontal = ("participants",)
    inlines = [DirectMessageInline]


@admin.register(DirectMessage)
class DirectMessageAdmin(BaseAdmin):
    list_display = ("sender", "conversation", "short_body", "is_read", "created_at")
    list_filter = ("is_read",)
    search_fields = ("body", "sender__username")
    autocomplete_fields = ("sender", "conversation")

    @admin.display(description=_("body"))
    def short_body(self, obj):
        return (obj.body or "")[:60]


@admin.register(Block)
class BlockAdmin(BaseAdmin):
    list_display = ("blocker", "blocked", "created_at")
    search_fields = ("blocker__username", "blocked__username")
    autocomplete_fields = ("blocker", "blocked")


@admin.register(Report)
class ReportAdmin(BaseAdmin):
    list_display = (
        "reporter",
        "target_type",
        "status",
        "created_at",
    )
    list_filter = ("target_type", "status")
    search_fields = ("reason", "reporter__username")
    autocomplete_fields = (
        "reporter",
        "target_post",
        "target_comment",
        "target_user",
    )
    readonly_fields = ("created_at", "modified_at")


@admin.register(SocialNotification)
class SocialNotificationAdmin(BaseAdmin):
    list_display = (
        "recipient",
        "notification_type",
        "message",
        "is_read",
        "created_at",
    )
    list_filter = ("notification_type", "is_read")
    search_fields = ("message", "recipient__username")
    autocomplete_fields = ("recipient", "actor", "post")


class DiscussionMessageInline(admin.TabularInline):
    model = DiscussionMessage
    extra = 0
    fields = ("author", "body", "is_hidden", "created_at", "created_by")
    readonly_fields = ("created_at", "created_by")
    autocomplete_fields = ("author",)
    show_change_link = True


@admin.register(Discussion)
class DiscussionAdmin(BaseAdmin):
    list_display = (
        "title",
        "audience",
        "organization",
        "branch",
        "zone",
        "messages_count",
        "is_active",
        "is_locked",
        "created_by",
        "created_at",
    )
    list_filter = ("audience", "is_active", "is_locked")
    search_fields = (
        "title",
        "body",
        "organization__name",
        "branch__name",
        "zone__name",
    )
    autocomplete_fields = ("organization", "branch", "zone", "created_by", "modified_by")
    readonly_fields = (
        "messages_count",
        "last_message_at",
        "created_at",
        "modified_at",
        "created_by",
        "modified_by",
    )
    inlines = [DiscussionMessageInline]
    fieldsets = (
        (
            None,
            {"fields": ("title", "body", "is_active", "is_locked")},
        ),
        (
            _("Audience"),
            {
                "fields": ("audience", "organization", "branch", "zone"),
                "description": _(
                    "Open to all platform users, or limit to an organisation, "
                    "branch, or zone."
                ),
            },
        ),
        (
            _("Activity"),
            {"fields": ("messages_count", "last_message_at")},
        ),
        (
            _("Audit"),
            {
                "classes": ("collapse",),
                "fields": (
                    "created_by",
                    "modified_by",
                    "created_at",
                    "modified_at",
                ),
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.modified_by = request.user
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for obj in formset.deleted_objects:
            obj.delete()
        for instance in instances:
            if isinstance(instance, DiscussionMessage):
                if not instance.pk:
                    instance.created_by = request.user
                    if not instance.author_id:
                        instance.author = request.user
                instance.modified_by = request.user
            instance.save()
        formset.save_m2m()


@admin.register(DiscussionMessage)
class DiscussionMessageAdmin(BaseAdmin):
    list_display = (
        "author",
        "discussion",
        "short_body",
        "is_hidden",
        "created_at",
    )
    list_filter = ("is_hidden",)
    search_fields = ("body", "author__username", "discussion__title")
    autocomplete_fields = ("discussion", "author", "parent", "created_by", "modified_by")
    readonly_fields = ("created_at", "modified_at", "created_by", "modified_by")

    @admin.display(description=_("body"))
    def short_body(self, obj):
        return (obj.body or "")[:60]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
            if not obj.author_id:
                obj.author = request.user
        obj.modified_by = request.user
        super().save_model(request, obj, form, change)
