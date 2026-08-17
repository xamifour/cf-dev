# cf-dev/cf_src/appsinn/cf_social/models.py

"""Concrete social network models."""

from django.utils.translation import gettext_lazy as _

from .base.models import (
    AbstractBlock,
    AbstractComment,
    AbstractConversation,
    AbstractDirectMessage,
    AbstractDiscussion,
    AbstractDiscussionMessage,
    AbstractFollow,
    AbstractPost,
    AbstractPostLike,
    AbstractReport,
    AbstractSocialNotification,
    AbstractSocialProfile,
    DiscussionManager,
    TimeStampedModel,
)

__all__ = [
    "TimeStampedModel",
    "SocialProfile",
    "Follow",
    "Post",
    "PostLike",
    "Comment",
    "Conversation",
    "DirectMessage",
    "Block",
    "Report",
    "SocialNotification",
    "Discussion",
    "DiscussionMessage",
]


class SocialProfile(AbstractSocialProfile):
    class Meta(AbstractSocialProfile.Meta):
        abstract = False


class Follow(AbstractFollow):
    class Meta(AbstractFollow.Meta):
        abstract = False


class Post(AbstractPost):
    class Meta(AbstractPost.Meta):
        abstract = False


class PostLike(AbstractPostLike):
    class Meta(AbstractPostLike.Meta):
        abstract = False


class Comment(AbstractComment):
    class Meta(AbstractComment.Meta):
        abstract = False


class Conversation(AbstractConversation):
    class Meta(AbstractConversation.Meta):
        abstract = False


class DirectMessage(AbstractDirectMessage):
    class Meta(AbstractDirectMessage.Meta):
        abstract = False


class Block(AbstractBlock):
    class Meta(AbstractBlock.Meta):
        abstract = False


class Report(AbstractReport):
    class Meta(AbstractReport.Meta):
        abstract = False


class SocialNotification(AbstractSocialNotification):
    class Meta(AbstractSocialNotification.Meta):
        abstract = False


class Discussion(AbstractDiscussion):
    objects = DiscussionManager()

    class Meta(AbstractDiscussion.Meta):
        abstract = False


class DiscussionMessage(AbstractDiscussionMessage):
    class Meta(AbstractDiscussionMessage.Meta):
        abstract = False
