# cf-dev/cf_src/appsinn/cf_social/base/models.py

"""
Abstract social network models.

Concrete implementations live in ``cf_social.models``. Keep all field
definitions and domain logic here so other apps / forks can subclass cleanly.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from cf_users.mixins import AuditMixin


class TimeStampedModel(models.Model):
    """Lightweight timestamps for social graph models (follows, likes, etc.)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True, db_index=True)
    modified_at = models.DateTimeField(_("modified at"), auto_now=True)

    class Meta:
        abstract = True
        ordering = ("-modified_at",)


class AbstractSocialProfile(TimeStampedModel):
    """Public social profile for a platform user."""

    VISIBILITY_PUBLIC = "PUBLIC"
    VISIBILITY_FOLLOWERS = "FOLLOWERS"
    VISIBILITY_PRIVATE = "PRIVATE"
    VISIBILITY_CHOICES = [
        (VISIBILITY_PUBLIC, _("Public")),
        (VISIBILITY_FOLLOWERS, _("Followers only")),
        (VISIBILITY_PRIVATE, _("Private")),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="social_profile",
        verbose_name=_("user"),
    )
    display_name = models.CharField(_("display name"), max_length=120, blank=True)
    bio = models.TextField(_("bio"), blank=True, max_length=1000)
    avatar = models.ImageField(
        _("avatar"), upload_to="social/avatars/%Y/%m/", blank=True, null=True
    )
    cover = models.ImageField(
        _("cover image"), upload_to="social/covers/%Y/%m/", blank=True, null=True
    )
    website = models.URLField(_("website"), blank=True)
    location = models.CharField(_("location"), max_length=120, blank=True)
    # Privacy
    profile_visibility = models.CharField(
        _("profile visibility"),
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default=VISIBILITY_PUBLIC,
        db_index=True,
    )
    default_post_visibility = models.CharField(
        _("default post visibility"),
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default=VISIBILITY_PUBLIC,
    )
    allow_direct_messages = models.BooleanField(
        _("allow direct messages"),
        default=True,
        help_text=_("When off, only people you follow can message you."),
    )
    show_online_status = models.BooleanField(_("show online status"), default=False)
    is_active = models.BooleanField(_("is active"), default=True, db_index=True)

    class Meta:
        abstract = True
        verbose_name = _("social profile")
        verbose_name_plural = _("social profiles")
        ordering = ("-modified_at",)

    def __str__(self) -> str:
        return self.get_display_name()

    def get_display_name(self) -> str:
        if self.display_name.strip():
            return self.display_name.strip()
        full = self.user.get_full_name()
        return full or self.user.username


class AbstractFollow(TimeStampedModel):
    """A follows B (directed follow graph)."""

    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="following_set",
        verbose_name=_("follower"),
    )
    following = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="follower_set",
        verbose_name=_("following"),
    )

    class Meta:
        abstract = True
        verbose_name = _("follow")
        verbose_name_plural = _("follows")
        constraints = [
            models.UniqueConstraint(
                fields=["follower", "following"],
                name="cf_social_follow_unique_pair",
            ),
            models.CheckConstraint(
                condition=~Q(follower=models.F("following")),
                name="cf_social_follow_no_self",
            ),
        ]
        indexes = [
            models.Index(fields=["follower", "-created_at"]),
            models.Index(fields=["following", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.follower} → {self.following}"

    def clean(self) -> None:
        if self.follower_id and self.following_id and self.follower_id == self.following_id:
            raise ValidationError(_("You cannot follow yourself."))


class AbstractPost(TimeStampedModel):
    """A feed post: text with optional image/video."""

    VISIBILITY_PUBLIC = "PUBLIC"
    VISIBILITY_FOLLOWERS = "FOLLOWERS"
    VISIBILITY_PRIVATE = "PRIVATE"
    VISIBILITY_CHOICES = AbstractSocialProfile.VISIBILITY_CHOICES

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="social_posts",
        verbose_name=_("author"),
    )
    body = models.TextField(_("body"), blank=True, max_length=5000)
    image = models.ImageField(
        _("image"), upload_to="social/posts/images/%Y/%m/", blank=True, null=True
    )
    video = models.FileField(
        _("video"), upload_to="social/posts/videos/%Y/%m/", blank=True, null=True
    )
    visibility = models.CharField(
        _("visibility"),
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default=VISIBILITY_PUBLIC,
        db_index=True,
    )
    likes_count = models.PositiveIntegerField(_("likes"), default=0)
    comments_count = models.PositiveIntegerField(_("comments"), default=0)
    is_hidden = models.BooleanField(
        _("hidden by moderation"),
        default=False,
        db_index=True,
        help_text=_("Staff can hide posts without deleting them."),
    )

    class Meta:
        abstract = True
        verbose_name = _("post")
        verbose_name_plural = _("posts")
        ordering = ("-modified_at",)
        indexes = [
            models.Index(fields=["author", "-created_at"]),
            models.Index(fields=["visibility", "-created_at"]),
        ]

    def __str__(self) -> str:
        snippet = (self.body or "")[:40]
        return f"{self.author}: {snippet}"

    def clean(self) -> None:
        if not (self.body or "").strip() and not self.image and not self.video:
            raise ValidationError(_("A post needs text, an image, or a video."))


class AbstractPostLike(TimeStampedModel):
    post = models.ForeignKey(
        "cf_social.Post", on_delete=models.CASCADE, related_name="likes", verbose_name=_("post")
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="social_likes",
        verbose_name=_("user"),
    )

    class Meta:
        abstract = True
        verbose_name = _("like")
        verbose_name_plural = _("likes")
        constraints = [
            models.UniqueConstraint(
                fields=["post", "user"], name="cf_social_like_unique_post_user"
            )
        ]

    def __str__(self) -> str:
        return f"{self.user} ♥ {self.post_id}"


class AbstractComment(TimeStampedModel):
    post = models.ForeignKey(
        "cf_social.Post",
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name=_("post"),
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="social_comments",
        verbose_name=_("author"),
    )
    body = models.TextField(_("body"), max_length=2000)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies",
        verbose_name=_("parent comment"),
    )
    is_hidden = models.BooleanField(_("hidden"), default=False)

    class Meta:
        abstract = True
        verbose_name = _("comment")
        verbose_name_plural = _("comments")
        ordering = ("-modified_at", "created_at")

    def __str__(self) -> str:
        return f"{self.author}: {(self.body or '')[:40]}"


class AbstractConversation(TimeStampedModel):
    """Direct message thread between exactly two users (MVP)."""

    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="social_conversations",
        verbose_name=_("participants"),
    )
    last_message_at = models.DateTimeField(
        _("last message at"), null=True, blank=True, db_index=True
    )

    class Meta:
        abstract = True
        verbose_name = _("conversation")
        verbose_name_plural = _("conversations")
        ordering = ("-last_message_at", "-modified_at")

    def __str__(self) -> str:
        return f"Conversation {self.pk}"


class AbstractDirectMessage(TimeStampedModel):
    conversation = models.ForeignKey(
        "cf_social.Conversation",
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name=_("conversation"),
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="social_messages_sent",
        verbose_name=_("sender"),
    )
    body = models.TextField(_("body"), max_length=4000)
    is_read = models.BooleanField(_("is read"), default=False, db_index=True)

    class Meta:
        abstract = True
        verbose_name = _("direct message")
        verbose_name_plural = _("direct messages")
        ordering = ("-modified_at", "created_at")

    def __str__(self) -> str:
        return f"{self.sender}: {(self.body or '')[:40]}"


class AbstractBlock(TimeStampedModel):
    blocker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="blocks_initiated",
        verbose_name=_("blocker"),
    )
    blocked = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="blocks_received",
        verbose_name=_("blocked user"),
    )

    class Meta:
        abstract = True
        verbose_name = _("block")
        verbose_name_plural = _("blocks")
        constraints = [
            models.UniqueConstraint(
                fields=["blocker", "blocked"], name="cf_social_block_unique_pair"
            ),
            models.CheckConstraint(
                condition=~Q(blocker=models.F("blocked")),
                name="cf_social_block_no_self",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.blocker} blocked {self.blocked}"


class AbstractReport(TimeStampedModel):
    """User report of a post, comment, or profile for moderation."""

    TARGET_POST = "POST"
    TARGET_COMMENT = "COMMENT"
    TARGET_USER = "USER"
    TARGET_CHOICES = [
        (TARGET_POST, _("Post")),
        (TARGET_COMMENT, _("Comment")),
        (TARGET_USER, _("User / profile")),
    ]
    STATUS_OPEN = "OPEN"
    STATUS_REVIEWING = "REVIEWING"
    STATUS_RESOLVED = "RESOLVED"
    STATUS_DISMISSED = "DISMISSED"
    STATUS_CHOICES = [
        (STATUS_OPEN, _("Open")),
        (STATUS_REVIEWING, _("Reviewing")),
        (STATUS_RESOLVED, _("Resolved")),
        (STATUS_DISMISSED, _("Dismissed")),
    ]

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="social_reports_filed",
        verbose_name=_("reporter"),
    )
    target_type = models.CharField(
        _("target type"), max_length=20, choices=TARGET_CHOICES
    )
    target_post = models.ForeignKey(
        "cf_social.Post",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="reports",
        verbose_name=_("post"),
    )
    target_comment = models.ForeignKey(
        "cf_social.Comment",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="reports",
        verbose_name=_("comment"),
    )
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="social_reports_against",
        verbose_name=_("reported user"),
    )
    reason = models.TextField(_("reason"), max_length=2000)
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_OPEN,
        db_index=True,
    )
    staff_notes = models.TextField(_("staff notes"), blank=True)

    class Meta:
        abstract = True
        verbose_name = _("report")
        verbose_name_plural = _("reports")
        ordering = ("-modified_at",)

    def __str__(self) -> str:
        return f"{self.get_target_type_display()} report by {self.reporter}"


class AbstractSocialNotification(TimeStampedModel):
    """In-app social activity notification (follow, like, comment, message)."""

    TYPE_FOLLOW = "FOLLOW"
    TYPE_LIKE = "LIKE"
    TYPE_COMMENT = "COMMENT"
    TYPE_MESSAGE = "MESSAGE"
    TYPE_MENTION = "MENTION"
    TYPE_SYSTEM = "SYSTEM"
    TYPE_CHOICES = [
        (TYPE_FOLLOW, _("New follower")),
        (TYPE_LIKE, _("Like")),
        (TYPE_COMMENT, _("Comment")),
        (TYPE_MESSAGE, _("Direct message")),
        (TYPE_MENTION, _("Mention")),
        (TYPE_SYSTEM, _("System")),
    ]

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="social_notifications",
        verbose_name=_("recipient"),
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="social_notifications_acted",
        verbose_name=_("actor"),
    )
    notification_type = models.CharField(
        _("type"), max_length=20, choices=TYPE_CHOICES, db_index=True
    )
    message = models.CharField(_("message"), max_length=255)
    post = models.ForeignKey(
        "cf_social.Post",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
        verbose_name=_("post"),
    )
    is_read = models.BooleanField(_("is read"), default=False, db_index=True)
    link = models.CharField(_("link"), max_length=500, blank=True)

    class Meta:
        abstract = True
        verbose_name = _("social notification")
        verbose_name_plural = _("social notifications")
        ordering = ("-modified_at",)
        indexes = [
            models.Index(fields=["recipient", "is_read", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.recipient}: {self.message[:50]}"


# ---------------------------------------------------------------------------
# Discussions (scoped audience: platform / org / branch / zone)
# ---------------------------------------------------------------------------
class DiscussionQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def for_user(self, user):
        """Discussions the user may open (by audience scope)."""
        if user is None or not getattr(user, "is_authenticated", False):
            return self.none()
        if getattr(user, "is_superuser", False):
            return self.all()

        from django.apps import apps

        from cf_users.tenancy import (
            accessible_branch_ids_qs,
            managed_organization_ids_qs,
        )

        OrganizationUser = apps.get_model("cf_users", "OrganizationUser")
        Zone = apps.get_model("cf_people", "Zone")

        org_ids = OrganizationUser.objects.filter(user_id=user.pk).values(
            "organization_id"
        )
        managed_org_ids = managed_organization_ids_qs(user)
        branch_ids = accessible_branch_ids_qs(user)
        zone_ids = Zone.objects.filter(branch_id__in=branch_ids).values("id")

        return self.filter(
            Q(audience=AbstractDiscussion.AUDIENCE_PLATFORM)
            | Q(
                audience=AbstractDiscussion.AUDIENCE_ORGANIZATION,
                organization_id__in=org_ids,
            )
            | Q(
                audience=AbstractDiscussion.AUDIENCE_ORGANIZATION,
                organization_id__in=managed_org_ids,
            )
            | Q(
                audience=AbstractDiscussion.AUDIENCE_BRANCH,
                branch_id__in=branch_ids,
            )
            | Q(
                audience=AbstractDiscussion.AUDIENCE_ZONE,
                zone_id__in=zone_ids,
            )
            | Q(created_by_id=user.pk)
        ).distinct()


class DiscussionManager(models.Manager.from_queryset(DiscussionQuerySet)):
    pass


class AbstractDiscussion(AuditMixin):
    """
    A discussion thread open to a chosen audience.

    Audience:
    - PLATFORM — all authenticated platform users
    - ORGANIZATION — users with access to a specific organisation
    - BRANCH — users with access to a specific branch
    - ZONE — users with access to the branch of a specific zone
    """

    AUDIENCE_PLATFORM = "PLATFORM"
    AUDIENCE_ORGANIZATION = "ORGANIZATION"
    AUDIENCE_BRANCH = "BRANCH"
    AUDIENCE_ZONE = "ZONE"
    AUDIENCE_CHOICES = [
        (AUDIENCE_PLATFORM, _("All platform users")),
        (AUDIENCE_ORGANIZATION, _("Organisation")),
        (AUDIENCE_BRANCH, _("Branch")),
        (AUDIENCE_ZONE, _("Zone")),
    ]

    title = models.CharField(_("title"), max_length=255)
    body = models.TextField(
        _("opening message"),
        blank=True,
        max_length=10000,
        help_text=_("Optional description or first post for this discussion."),
    )
    audience = models.CharField(
        _("audience"),
        max_length=20,
        choices=AUDIENCE_CHOICES,
        default=AUDIENCE_PLATFORM,
        db_index=True,
        help_text=_(
            "Who can view and participate: entire platform, one organisation, "
            "one branch, or one zone."
        ),
    )
    organization = models.ForeignKey(
        "cf_users.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="discussions",
        verbose_name=_("organisation"),
        help_text=_("Required when audience is Organisation."),
    )
    branch = models.ForeignKey(
        "cf_users.Branch",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="discussions",
        verbose_name=_("branch"),
        help_text=_("Required when audience is Branch (also set from Zone)."),
    )
    zone = models.ForeignKey(
        "cf_people.Zone",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="discussions",
        verbose_name=_("zone"),
        help_text=_("Required when audience is Zone."),
    )
    is_active = models.BooleanField(_("is active"), default=True, db_index=True)
    is_locked = models.BooleanField(
        _("locked"),
        default=False,
        help_text=_("When locked, no new messages can be posted."),
    )
    messages_count = models.PositiveIntegerField(_("messages"), default=0)
    last_message_at = models.DateTimeField(
        _("last message at"), null=True, blank=True, db_index=True
    )

    objects = DiscussionManager()

    class Meta:
        abstract = True
        verbose_name = _("discussion")
        verbose_name_plural = _("discussions")
        ordering = ("-last_message_at", "-modified_at")
        indexes = [
            models.Index(fields=["audience", "-created_at"]),
            models.Index(fields=["organization", "-created_at"]),
            models.Index(fields=["branch", "-created_at"]),
            models.Index(fields=["zone", "-created_at"]),
        ]

    def __str__(self) -> str:
        return self.title

    def _sync_scope_from_zone(self) -> None:
        if self.zone_id:
            zone = self.zone
            if zone is not None:
                self.branch_id = zone.branch_id
                if zone.branch_id and zone.branch is not None:
                    self.organization_id = zone.branch.organization_id

    def _sync_scope_from_branch(self) -> None:
        if self.branch_id and not self.organization_id:
            branch = self.branch
            if branch is not None:
                self.organization_id = branch.organization_id

    def clean(self) -> None:
        # Align denormalised FKs before validating audience requirements.
        if self.audience == self.AUDIENCE_ZONE and self.zone_id:
            self._sync_scope_from_zone()
        elif self.audience == self.AUDIENCE_BRANCH and self.branch_id:
            self._sync_scope_from_branch()

        errors = {}
        if self.audience == self.AUDIENCE_PLATFORM:
            if self.organization_id or self.branch_id or self.zone_id:
                # Clear scope FKs for platform-wide discussions.
                self.organization = None
                self.branch = None
                self.zone = None
        elif self.audience == self.AUDIENCE_ORGANIZATION:
            if not self.organization_id:
                errors["organization"] = _(
                    "Select an organisation for organisation-scoped discussions."
                )
            self.branch = None
            self.zone = None
        elif self.audience == self.AUDIENCE_BRANCH:
            if not self.branch_id:
                errors["branch"] = _(
                    "Select a branch for branch-scoped discussions."
                )
            else:
                self._sync_scope_from_branch()
                if (
                    self.organization_id
                    and self.branch.organization_id
                    and self.organization_id != self.branch.organization_id
                ):
                    errors["organization"] = _(
                        "Organisation must match the selected branch."
                    )
            self.zone = None
        elif self.audience == self.AUDIENCE_ZONE:
            if not self.zone_id:
                errors["zone"] = _("Select a zone for zone-scoped discussions.")
            else:
                self._sync_scope_from_zone()
                if (
                    self.branch_id
                    and self.zone.branch_id
                    and self.branch_id != self.zone.branch_id
                ):
                    errors["branch"] = _("Branch must match the selected zone.")
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        from django.apps import apps

        if self.audience == self.AUDIENCE_ZONE and self.zone_id:
            Zone = apps.get_model("cf_people", "Zone")
            row = (
                Zone.objects.filter(pk=self.zone_id)
                .values_list("branch_id", "branch__organization_id")
                .first()
            )
            if row:
                self.branch_id, self.organization_id = row
        elif self.audience == self.AUDIENCE_BRANCH and self.branch_id:
            Branch = apps.get_model("cf_users", "Branch")
            org_id = (
                Branch.objects.filter(pk=self.branch_id)
                .values_list("organization_id", flat=True)
                .first()
            )
            if org_id:
                self.organization_id = org_id
            self.zone_id = None
        elif self.audience == self.AUDIENCE_PLATFORM:
            self.organization_id = None
            self.branch_id = None
            self.zone_id = None
        elif self.audience == self.AUDIENCE_ORGANIZATION:
            self.branch_id = None
            self.zone_id = None
        super().save(*args, **kwargs)

    def audience_label(self) -> str:
        if self.audience == self.AUDIENCE_PLATFORM:
            return str(_("All platform users"))
        if self.audience == self.AUDIENCE_ORGANIZATION and self.organization_id:
            return str(self.organization)
        if self.audience == self.AUDIENCE_BRANCH and self.branch_id:
            return str(self.branch)
        if self.audience == self.AUDIENCE_ZONE and self.zone_id:
            return str(self.zone)
        return self.get_audience_display()


class AbstractDiscussionMessage(AuditMixin):
    """A message / reply within a discussion."""

    discussion = models.ForeignKey(
        "cf_social.Discussion",
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name=_("discussion"),
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="discussion_messages",
        verbose_name=_("author"),
    )
    body = models.TextField(_("body"), max_length=10000)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies",
        verbose_name=_("parent message"),
    )
    is_hidden = models.BooleanField(_("hidden"), default=False, db_index=True)

    class Meta:
        abstract = True
        verbose_name = _("discussion message")
        verbose_name_plural = _("discussion messages")
        ordering = ("-modified_at", "created_at")
        indexes = [
            models.Index(fields=["discussion", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.author}: {(self.body or '')[:40]}"

    def clean(self) -> None:
        if not (self.body or "").strip():
            raise ValidationError({"body": _("Message cannot be empty.")})
        if self.parent_id and self.parent and self.parent.discussion_id != self.discussion_id:
            raise ValidationError(
                {"parent": _("Parent message must belong to the same discussion.")}
            )
        if self.discussion_id and self.discussion.is_locked:
            raise ValidationError(_("This discussion is locked."))
