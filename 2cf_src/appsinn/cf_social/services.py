# cf-dev/cf_src/appsinn/cf_social/services.py

"""Business rules: privacy, blocks, feed, follows, DMs."""

from __future__ import annotations

from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Prefetch, Q, QuerySet
from django.utils import timezone

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
    SocialNotification,
    SocialProfile,
)


def get_or_create_profile(user) -> SocialProfile:
    profile, _ = SocialProfile.objects.get_or_create(user=user)
    return profile


def blocked_user_ids(user) -> set:
    """Users this person has blocked or been blocked by."""
    if user is None or not user.is_authenticated:
        return set()
    a = set(
        Block.objects.filter(blocker=user).values_list("blocked_id", flat=True)
    )
    b = set(
        Block.objects.filter(blocked=user).values_list("blocker_id", flat=True)
    )
    return a | b


def is_blocked_between(a, b) -> bool:
    if not a or not b:
        return False
    return Block.objects.filter(
        Q(blocker=a, blocked=b) | Q(blocker=b, blocked=a)
    ).exists()


def is_following(follower, following) -> bool:
    if not follower or not following:
        return False
    return Follow.objects.filter(follower=follower, following=following).exists()


def can_view_profile(viewer, profile_user) -> bool:
    if profile_user is None:
        return False
    if viewer is not None and viewer.is_authenticated and viewer.pk == profile_user.pk:
        return True
    if viewer and is_blocked_between(viewer, profile_user):
        return False
    profile = getattr(profile_user, "social_profile", None)
    if profile is None:
        try:
            profile = SocialProfile.objects.get(user=profile_user)
        except SocialProfile.DoesNotExist:
            return True  # default public until profile exists
    vis = profile.profile_visibility
    if vis == SocialProfile.VISIBILITY_PUBLIC:
        return True
    if not viewer or not viewer.is_authenticated:
        return False
    if vis == SocialProfile.VISIBILITY_FOLLOWERS:
        return is_following(viewer, profile_user)
    return False  # PRIVATE


def can_view_post(viewer, post: Post) -> bool:
    if post.is_hidden and not (
        viewer and viewer.is_authenticated and (viewer.pk == post.author_id or viewer.is_staff)
    ):
        return False
    if viewer and is_blocked_between(viewer, post.author):
        return False
    if viewer and viewer.is_authenticated and viewer.pk == post.author_id:
        return True
    if post.visibility == Post.VISIBILITY_PUBLIC:
        return True
    if not viewer or not viewer.is_authenticated:
        return False
    if post.visibility == Post.VISIBILITY_FOLLOWERS:
        return is_following(viewer, post.author)
    return False


def posts_visible_to(viewer) -> QuerySet:
    """Feed-ready queryset of posts the viewer may see."""
    qs = (
        Post.objects.filter(is_hidden=False)
        .select_related("author", "author__social_profile")
        .annotate(
            _likes=Count("likes", distinct=True),
            _comments=Count("comments", distinct=True),
        )
    )
    blocked = blocked_user_ids(viewer) if viewer and viewer.is_authenticated else set()
    if blocked:
        qs = qs.exclude(author_id__in=blocked)

    if viewer is None or not viewer.is_authenticated:
        return qs.filter(visibility=Post.VISIBILITY_PUBLIC)

    following_ids = list(
        Follow.objects.filter(follower=viewer).values_list("following_id", flat=True)
    )
    return qs.filter(
        Q(author=viewer)
        | Q(visibility=Post.VISIBILITY_PUBLIC)
        | Q(visibility=Post.VISIBILITY_FOLLOWERS, author_id__in=following_ids)
    )


def feed_for(viewer, *, following_only: bool = False) -> QuerySet:
    qs = posts_visible_to(viewer).order_by("-modified_at", "-created_at")
    if following_only and viewer and viewer.is_authenticated:
        following_ids = Follow.objects.filter(follower=viewer).values_list(
            "following_id", flat=True
        )
        qs = qs.filter(Q(author=viewer) | Q(author_id__in=following_ids))
    return qs


@transaction.atomic
def follow_user(follower, following) -> Follow | None:
    if follower.pk == following.pk or is_blocked_between(follower, following):
        return None
    obj, created = Follow.objects.get_or_create(follower=follower, following=following)
    if created:
        notify(
            recipient=following,
            actor=follower,
            notification_type=SocialNotification.TYPE_FOLLOW,
            message=f"{_name(follower)} started following you",
            link=f"/social/u/{follower.username}/",
        )
    return obj


def unfollow_user(follower, following) -> None:
    Follow.objects.filter(follower=follower, following=following).delete()


@transaction.atomic
def toggle_like(user, post: Post) -> bool:
    """Returns True if now liked, False if unliked."""
    if not can_view_post(user, post):
        return False
    existing = PostLike.objects.filter(post=post, user=user).first()
    if existing:
        existing.delete()
        post.likes_count = post.likes.count()
        post.save(update_fields=["likes_count"])
        return False
    PostLike.objects.create(post=post, user=user)
    post.likes_count = post.likes.count()
    post.save(update_fields=["likes_count"])
    if post.author_id != user.pk:
        notify(
            recipient=post.author,
            actor=user,
            notification_type=SocialNotification.TYPE_LIKE,
            message=f"{_name(user)} liked your post",
            post=post,
            link=f"/social/posts/{post.pk}/",
        )
    return True


@transaction.atomic
def add_comment(user, post: Post, body: str, parent=None) -> Comment | None:
    if not can_view_post(user, post):
        return None
    body = (body or "").strip()
    if not body:
        return None
    comment = Comment.objects.create(
        post=post, author=user, body=body, parent=parent
    )
    post.comments_count = post.comments.count()
    post.save(update_fields=["comments_count"])
    if post.author_id != user.pk:
        notify(
            recipient=post.author,
            actor=user,
            notification_type=SocialNotification.TYPE_COMMENT,
            message=f"{_name(user)} commented on your post",
            post=post,
            link=f"/social/posts/{post.pk}/",
        )
    return comment


def can_message(sender, recipient) -> bool:
    if sender.pk == recipient.pk:
        return False
    if is_blocked_between(sender, recipient):
        return False
    profile = get_or_create_profile(recipient)
    if not profile.allow_direct_messages:
        # Only if recipient follows sender or sender follows? Spec: only people you follow
        # When off, only people recipient follows can message.
        return is_following(recipient, sender)
    return True


@transaction.atomic
def get_or_create_conversation(user_a, user_b) -> Conversation | None:
    if not can_message(user_a, user_b):
        return None
    # Find existing 2-person conversation
    qs = (
        Conversation.objects.annotate(n=Count("participants"))
        .filter(n=2, participants=user_a)
        .filter(participants=user_b)
    )
    conv = qs.first()
    if conv:
        return conv
    conv = Conversation.objects.create()
    conv.participants.add(user_a, user_b)
    return conv


@transaction.atomic
def send_direct_message(sender, recipient, body: str) -> DirectMessage | None:
    body = (body or "").strip()
    if not body:
        return None
    conv = get_or_create_conversation(sender, recipient)
    if conv is None:
        return None
    msg = DirectMessage.objects.create(
        conversation=conv, sender=sender, body=body
    )
    Conversation.objects.filter(pk=conv.pk).update(last_message_at=timezone.now())
    notify(
        recipient=recipient,
        actor=sender,
        notification_type=SocialNotification.TYPE_MESSAGE,
        message=f"{_name(sender)} sent you a message",
        link=f"/social/messages/{conv.pk}/",
    )
    return msg


def notify(
    *,
    recipient,
    actor=None,
    notification_type: str,
    message: str,
    post=None,
    link: str = "",
) -> SocialNotification:
    return SocialNotification.objects.create(
        recipient=recipient,
        actor=actor,
        notification_type=notification_type,
        message=message[:255],
        post=post,
        link=link[:500],
    )


def _name(user) -> str:
    profile = getattr(user, "social_profile", None)
    if profile:
        return profile.get_display_name()
    return user.get_full_name() or user.username


def search_users(viewer, query: str, limit: int = 30) -> QuerySet:
    q = (query or "").strip()
    User = type(viewer) if viewer and viewer.is_authenticated else None
    from django.contrib.auth import get_user_model

    UserModel = get_user_model()
    qs = UserModel.objects.filter(is_active=True)
    blocked = blocked_user_ids(viewer)
    if blocked:
        qs = qs.exclude(pk__in=blocked)
    if q:
        qs = qs.filter(
            Q(username__icontains=q)
            | Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(social_profile__display_name__icontains=q)
        )
    return qs.select_related("social_profile")[:limit]


def search_posts(viewer, query: str, limit: int = 30) -> QuerySet:
    q = (query or "").strip()
    qs = posts_visible_to(viewer)
    if q:
        qs = qs.filter(body__icontains=q)
    return qs[:limit]


def annotate_liked_by(qs: QuerySet, user) -> QuerySet:
    if not user or not user.is_authenticated:
        return qs
    return qs.annotate(
        liked_by_me=Exists(
            PostLike.objects.filter(post_id=OuterRef("pk"), user=user)
        )
    )


# ---------------------------------------------------------------------------
# Discussions
# ---------------------------------------------------------------------------
def discussions_for(user) -> QuerySet:
    """Active discussions visible to the user, newest activity first."""
    return (
        Discussion.objects.active()
        .for_user(user)
        .select_related(
            "organization",
            "branch",
            "zone",
            "created_by",
            "created_by__social_profile",
        )
        .order_by("-last_message_at", "-created_at")
    )


def can_view_discussion(user, discussion: Discussion) -> bool:
    if discussion is None:
        return False
    if not discussion.is_active and not (
        user and user.is_authenticated and (user.is_staff or user.pk == discussion.created_by_id)
    ):
        return False
    if user is None or not user.is_authenticated:
        return False
    if user.is_superuser or user.pk == discussion.created_by_id:
        return True
    return Discussion.objects.for_user(user).filter(pk=discussion.pk).exists()


def can_post_to_discussion(user, discussion: Discussion) -> bool:
    if not can_view_discussion(user, discussion):
        return False
    if discussion.is_locked:
        return False
    return True


@transaction.atomic
def create_discussion(
    user,
    *,
    title: str,
    body: str = "",
    audience: str = Discussion.AUDIENCE_PLATFORM,
    organization=None,
    branch=None,
    zone=None,
) -> Discussion:
    discussion = Discussion(
        title=(title or "").strip(),
        body=(body or "").strip(),
        audience=audience or Discussion.AUDIENCE_PLATFORM,
        organization=organization,
        branch=branch,
        zone=zone,
        created_by=user,
        modified_by=user,
        last_message_at=timezone.now(),
    )
    discussion.full_clean()
    discussion.save()
    return discussion


@transaction.atomic
def add_discussion_message(
    user, discussion: Discussion, body: str, parent=None
) -> DiscussionMessage | None:
    if not can_post_to_discussion(user, discussion):
        return None
    body = (body or "").strip()
    if not body:
        return None
    msg = DiscussionMessage(
        discussion=discussion,
        author=user,
        body=body,
        parent=parent,
        created_by=user,
        modified_by=user,
    )
    msg.full_clean()
    msg.save()
    Discussion.objects.filter(pk=discussion.pk).update(
        messages_count=discussion.messages.filter(is_hidden=False).count(),
        last_message_at=timezone.now(),
        modified_by=user,
        modified_at=timezone.now(),
    )
    if discussion.created_by_id and discussion.created_by_id != user.pk:
        notify(
            recipient=discussion.created_by,
            actor=user,
            notification_type=SocialNotification.TYPE_COMMENT,
            message=f"{_name(user)} replied in “{discussion.title[:80]}”",
            link=f"/social/discussions/{discussion.pk}/",
        )
    return msg
