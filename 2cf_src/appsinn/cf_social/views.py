# cf-dev/cf_src/appsinn/cf_social/views.py

"""Portal social UI views."""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Prefetch, Q
from django.http import Http404, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import ListView, TemplateView

from .forms import (
    CommentForm,
    DiscussionForm,
    DiscussionMessageForm,
    MessageForm,
    PostForm,
    ProfileForm,
    ReportForm,
    SearchForm,
)
from .models import (
    Block,
    Comment,
    Conversation,
    DirectMessage,
    Discussion,
    Follow,
    Post,
    Report,
    SocialNotification,
    SocialProfile,
)

# Post used for visibility constants in FeedView
from . import services

User = get_user_model()


def _social_ctx(**extra):
    base = {
        "product_name": _("CF Social"),
        "page_title": extra.pop("page_title", _("Social")),
    }
    base.update(extra)
    return base


@method_decorator(login_required, name="dispatch")
class FeedView(ListView):
    template_name = "cf_social/feed.html"
    context_object_name = "posts"
    paginate_by = 20

    def get_queryset(self):
        following_only = self.request.GET.get("tab") == "following"
        qs = services.feed_for(self.request.user, following_only=following_only)
        return services.annotate_liked_by(qs, self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = services.get_or_create_profile(self.request.user)
        default_vis = profile.default_post_visibility or Post.VISIBILITY_PUBLIC
        if default_vis not in {
            Post.VISIBILITY_PUBLIC,
            Post.VISIBILITY_FOLLOWERS,
            Post.VISIBILITY_PRIVATE,
        }:
            default_vis = Post.VISIBILITY_PUBLIC
        form = PostForm(initial={"visibility": default_vis})
        unread = SocialNotification.objects.filter(
            recipient=self.request.user, is_read=False
        ).count()
        ctx.update(
            _social_ctx(
                page_title=_("Home"),
                post_form=form,
                comment_form=CommentForm(),
                active_tab=self.request.GET.get("tab") or "for_you",
                unread_notifications=unread,
            )
        )
        return ctx

    def post(self, request, *args, **kwargs):
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            messages.success(request, _("Post published."))
            return redirect("cf_social:feed")
        self.object_list = self.get_queryset()
        ctx = self.get_context_data()
        ctx["post_form"] = form
        return render(request, self.template_name, ctx)


@method_decorator(login_required, name="dispatch")
class PostDetailView(View):
    def get(self, request, pk):
        post = get_object_or_404(
            Post.objects.select_related("author", "author__social_profile"),
            pk=pk,
        )
        if not services.can_view_post(request.user, post):
            raise Http404
        comments = (
            post.comments.filter(is_hidden=False, parent__isnull=True)
            .select_related("author", "author__social_profile")
            .prefetch_related(
                Prefetch(
                    "replies",
                    queryset=Comment.objects.filter(is_hidden=False).select_related(
                        "author"
                    ),
                )
            )
        )
        post.liked_by_me = post.likes.filter(user=request.user).exists()
        return render(
            request,
            "cf_social/post_detail.html",
            _social_ctx(
                page_title=_("Post"),
                post=post,
                comments=comments,
                comment_form=CommentForm(),
            ),
        )

    def post(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        if not services.can_view_post(request.user, post):
            raise Http404
        form = CommentForm(request.POST)
        if form.is_valid():
            services.add_comment(request.user, post, form.cleaned_data["body"])
            messages.success(request, _("Comment added."))
        return redirect("cf_social:post_detail", pk=pk)


@method_decorator(login_required, name="dispatch")
class LikeToggleView(View):
    def post(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        liked = services.toggle_like(request.user, post)
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            post.refresh_from_db()
            return JsonResponse({"liked": liked, "likes_count": post.likes_count})
        return redirect(request.META.get("HTTP_REFERER") or reverse("cf_social:feed"))


@method_decorator(login_required, name="dispatch")
class ProfileView(View):
    def get(self, request, username):
        profile_user = get_object_or_404(User, username=username, is_active=True)
        if not services.can_view_profile(request.user, profile_user):
            return render(
                request,
                "cf_social/profile_private.html",
                _social_ctx(page_title=username, profile_user=profile_user),
            )
        profile = services.get_or_create_profile(profile_user)
        posts = services.annotate_liked_by(
            services.posts_visible_to(request.user).filter(author=profile_user),
            request.user,
        )[:50]
        following = services.is_following(request.user, profile_user)
        followers_count = Follow.objects.filter(following=profile_user).count()
        following_count = Follow.objects.filter(follower=profile_user).count()
        blocked = services.is_blocked_between(request.user, profile_user)
        return render(
            request,
            "cf_social/profile.html",
            _social_ctx(
                page_title=profile.get_display_name(),
                profile_user=profile_user,
                profile=profile,
                posts=posts,
                is_own=request.user.pk == profile_user.pk,
                is_following=following,
                followers_count=followers_count,
                following_count=following_count,
                is_blocked=blocked,
                comment_form=CommentForm(),
            ),
        )


@method_decorator(login_required, name="dispatch")
class ProfileEditView(View):
    def get(self, request):
        profile = services.get_or_create_profile(request.user)
        return render(
            request,
            "cf_social/profile_edit.html",
            _social_ctx(
                page_title=_("Edit profile"),
                form=ProfileForm(instance=profile),
                profile=profile,
            ),
        )

    def post(self, request):
        profile = services.get_or_create_profile(request.user)
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, _("Profile updated."))
            return redirect("cf_social:profile", username=request.user.username)
        return render(
            request,
            "cf_social/profile_edit.html",
            _social_ctx(page_title=_("Edit profile"), form=form, profile=profile),
        )


@method_decorator(login_required, name="dispatch")
class FollowToggleView(View):
    """Follow or unfollow another user.

    Accepts ``action=follow`` / ``action=unfollow``. If ``action`` is omitted,
    toggles based on the current relationship (follow ↔ unfollow).
    """

    def post(self, request, username):
        target = get_object_or_404(User, username=username, is_active=True)
        if target.pk == request.user.pk:
            messages.error(request, _("You cannot follow yourself."))
            return redirect("cf_social:profile", username=username)

        action = (request.POST.get("action") or "").strip().lower()
        currently_following = services.is_following(request.user, target)

        if action in {"unfollow", "unwatch", "stop"}:
            do_unfollow = True
        elif action in {"follow", "start"}:
            do_unfollow = False
        else:
            # True toggle when action is blank / unknown.
            do_unfollow = currently_following

        if do_unfollow:
            services.unfollow_user(request.user, target)
            messages.info(
                request, _("Unfollowed @%(u)s.") % {"u": target.username}
            )
        else:
            services.follow_user(request.user, target)
            messages.success(
                request, _("You are now following @%(u)s.") % {"u": target.username}
            )
        return redirect(
            request.META.get("HTTP_REFERER")
            or reverse("cf_social:profile", kwargs={"username": username})
        )


@method_decorator(login_required, name="dispatch")
class SearchView(View):
    def get(self, request):
        form = SearchForm(request.GET or None)
        q = form.data.get("q", "") if form.is_bound else ""
        people = list(services.search_users(request.user, q)) if q else []
        following_ids: set = set()
        if people:
            following_ids = set(
                Follow.objects.filter(
                    follower=request.user,
                    following_id__in=[u.pk for u in people],
                ).values_list("following_id", flat=True)
            )
        posts = (
            services.annotate_liked_by(
                services.search_posts(request.user, q), request.user
            )
            if q
            else []
        )
        return render(
            request,
            "cf_social/search.html",
            _social_ctx(
                page_title=_("Search"),
                form=form,
                q=q,
                people=people,
                following_ids=following_ids,
                posts=posts,
            ),
        )


@method_decorator(login_required, name="dispatch")
class NotificationsView(ListView):
    template_name = "cf_social/notifications.html"
    context_object_name = "notifications"
    paginate_by = 40

    def get_queryset(self):
        qs = SocialNotification.objects.filter(
            recipient=self.request.user
        ).select_related("actor", "actor__social_profile", "post")
        SocialNotification.objects.filter(
            recipient=self.request.user, is_read=False
        ).update(is_read=True)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(_social_ctx(page_title=_("Notifications")))
        return ctx


@method_decorator(login_required, name="dispatch")
class InboxView(ListView):
    template_name = "cf_social/inbox.html"
    context_object_name = "conversations"

    def get_queryset(self):
        return (
            Conversation.objects.filter(participants=self.request.user)
            .prefetch_related("participants", "participants__social_profile")
            .annotate(msg_count=Count("messages"))
            .order_by("-last_message_at", "-created_at")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(_social_ctx(page_title=_("Messages")))
        # Attach other participant for display
        items = []
        for conv in ctx["conversations"]:
            other = next(
                (p for p in conv.participants.all() if p.pk != self.request.user.pk),
                None,
            )
            items.append({"conversation": conv, "other": other})
        ctx["conversation_items"] = items
        return ctx


@method_decorator(login_required, name="dispatch")
class ConversationView(View):
    def get(self, request, pk):
        conv = get_object_or_404(
            Conversation.objects.prefetch_related("participants"),
            pk=pk,
            participants=request.user,
        )
        other = next(
            (p for p in conv.participants.all() if p.pk != request.user.pk), None
        )
        msgs = conv.messages.select_related("sender").order_by("created_at")
        conv.messages.filter(is_read=False).exclude(sender=request.user).update(
            is_read=True
        )
        return render(
            request,
            "cf_social/conversation.html",
            _social_ctx(
                page_title=_("Chat"),
                conversation=conv,
                other=other,
                messages_list=msgs,
                form=MessageForm(),
            ),
        )

    def post(self, request, pk):
        conv = get_object_or_404(
            Conversation, pk=pk, participants=request.user
        )
        other = next(
            (p for p in conv.participants.all() if p.pk != request.user.pk), None
        )
        form = MessageForm(request.POST)
        if form.is_valid() and other:
            services.send_direct_message(
                request.user, other, form.cleaned_data["body"]
            )
        return redirect("cf_social:conversation", pk=pk)


@method_decorator(login_required, name="dispatch")
class StartMessageView(View):
    def post(self, request, username):
        other = get_object_or_404(User, username=username, is_active=True)
        conv = services.get_or_create_conversation(request.user, other)
        if conv is None:
            messages.error(request, _("You cannot message this user."))
            return redirect("cf_social:profile", username=username)
        return redirect("cf_social:conversation", pk=conv.pk)


@method_decorator(login_required, name="dispatch")
class BlockToggleView(View):
    def post(self, request, username):
        target = get_object_or_404(User, username=username, is_active=True)
        if target.pk == request.user.pk:
            return HttpResponseForbidden()
        action = request.POST.get("action")
        if action == "unblock":
            Block.objects.filter(blocker=request.user, blocked=target).delete()
            messages.info(request, _("Unblocked %(u)s.") % {"u": target.username})
        else:
            Block.objects.get_or_create(blocker=request.user, blocked=target)
            Follow.objects.filter(
                Q(follower=request.user, following=target)
                | Q(follower=target, following=request.user)
            ).delete()
            messages.warning(request, _("Blocked %(u)s.") % {"u": target.username})
        return redirect("cf_social:profile", username=username)


@method_decorator(login_required, name="dispatch")
class ReportCreateView(View):
    def get(self, request):
        return render(
            request,
            "cf_social/report.html",
            _social_ctx(
                page_title=_("Report"),
                form=ReportForm(),
                target_type=request.GET.get("type", "USER"),
                target_id=request.GET.get("id", ""),
            ),
        )

    def post(self, request):
        form = ReportForm(request.POST)
        target_type = request.POST.get("target_type", Report.TARGET_USER)
        target_id = request.POST.get("target_id")
        if form.is_valid():
            report = form.save(commit=False)
            report.reporter = request.user
            report.target_type = target_type
            if target_type == Report.TARGET_POST:
                report.target_post = get_object_or_404(Post, pk=target_id)
            elif target_type == Report.TARGET_COMMENT:
                report.target_comment = get_object_or_404(Comment, pk=target_id)
            else:
                report.target_user = get_object_or_404(User, pk=target_id)
            report.save()
            messages.success(request, _("Report submitted. Thank you."))
            return redirect("cf_social:feed")
        return render(
            request,
            "cf_social/report.html",
            _social_ctx(
                page_title=_("Report"),
                form=form,
                target_type=target_type,
                target_id=target_id,
            ),
        )


@method_decorator(login_required, name="dispatch")
class PostDeleteView(View):
    def post(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        if post.author_id != request.user.pk and not request.user.is_staff:
            return HttpResponseForbidden()
        post.delete()
        messages.info(request, _("Post deleted."))
        return redirect("cf_social:feed")


# ---------------------------------------------------------------------------
# Discussions
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class DiscussionListView(ListView):
    template_name = "cf_social/discussion_list.html"
    context_object_name = "discussions"
    paginate_by = 20

    def get_queryset(self):
        return services.discussions_for(self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        unread = SocialNotification.objects.filter(
            recipient=self.request.user, is_read=False
        ).count()
        ctx.update(
            _social_ctx(
                page_title=_("Discussions"),
                unread_notifications=unread,
            )
        )
        return ctx


@method_decorator(login_required, name="dispatch")
class DiscussionCreateView(View):
    template_name = "cf_social/discussion_form.html"

    def get(self, request):
        form = DiscussionForm(user=request.user)
        return render(
            request,
            self.template_name,
            _social_ctx(page_title=_("New discussion"), form=form),
        )

    def post(self, request):
        form = DiscussionForm(request.POST, user=request.user)
        if form.is_valid():
            discussion = services.create_discussion(
                request.user,
                title=form.cleaned_data["title"],
                body=form.cleaned_data.get("body") or "",
                audience=form.cleaned_data["audience"],
                organization=form.cleaned_data.get("organization"),
                branch=form.cleaned_data.get("branch"),
                zone=form.cleaned_data.get("zone"),
            )
            messages.success(request, _("Discussion opened."))
            return redirect("cf_social:discussion_detail", pk=discussion.pk)
        return render(
            request,
            self.template_name,
            _social_ctx(page_title=_("New discussion"), form=form),
        )


@method_decorator(login_required, name="dispatch")
class DiscussionDetailView(View):
    def get(self, request, pk):
        discussion = get_object_or_404(
            Discussion.objects.select_related(
                "organization",
                "branch",
                "zone",
                "created_by",
                "created_by__social_profile",
            ),
            pk=pk,
        )
        if not services.can_view_discussion(request.user, discussion):
            raise Http404
        message_list = (
            discussion.messages.filter(is_hidden=False)
            .select_related("author", "author__social_profile")
            .order_by("created_at")
        )
        can_post = services.can_post_to_discussion(request.user, discussion)
        return render(
            request,
            "cf_social/discussion_detail.html",
            _social_ctx(
                page_title=discussion.title,
                discussion=discussion,
                message_list=message_list,
                form=DiscussionMessageForm() if can_post else None,
                can_post=can_post,
            ),
        )

    def post(self, request, pk):
        discussion = get_object_or_404(Discussion, pk=pk)
        if not services.can_view_discussion(request.user, discussion):
            raise Http404
        if not services.can_post_to_discussion(request.user, discussion):
            messages.error(request, _("This discussion is locked or not writable."))
            return redirect("cf_social:discussion_detail", pk=pk)
        form = DiscussionMessageForm(request.POST)
        if form.is_valid():
            services.add_discussion_message(
                request.user, discussion, form.cleaned_data["body"]
            )
            messages.success(request, _("Reply posted."))
        else:
            messages.error(request, _("Could not post reply."))
        return redirect("cf_social:discussion_detail", pk=pk)
