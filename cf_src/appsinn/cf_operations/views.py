# cf-dev/cf_src/appsinn/cf_operations/views.py

"""Portal views: platform-visible events, sermons, and outreaches."""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, ListView

from .models import Event, Sermon


class VisibleContentMixin:
    """Scope querysets with TenantQuerySet.visible_to (public + org access)."""

    model = None

    def get_queryset(self):
        qs = self.model.objects.visible_to(self.request.user)
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(self._search_q(q))
        return qs.select_related("branch", "branch__organization")

    def _search_q(self, q: str) -> Q:
        return Q(title__icontains=q) | Q(description__icontains=q)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("product_name", _("CF Organisation Portal"))
        context["search_q"] = (self.request.GET.get("q") or "").strip()
        context["is_staff_user"] = (
            self.request.user.is_staff or self.request.user.is_superuser
        )
        return context


@method_decorator(login_required, name="dispatch")
class EventListView(VisibleContentMixin, ListView):
    model = Event
    template_name = "cf_operations/portal/event_list.html"
    context_object_name = "events"
    paginate_by = 24

    def get_queryset(self):
        qs = super().get_queryset().order_by("-modified_at", "-start_time")
        event_type = (self.request.GET.get("type") or "").strip().upper()
        if event_type:
            qs = qs.filter(event_type=event_type)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = _("Events")
        context["explore_nav"] = "events"
        context["active_type"] = (self.request.GET.get("type") or "").strip().upper()
        context["event_type_choices"] = Event.EVENT_TYPE_CHOICES
        return context


@method_decorator(login_required, name="dispatch")
class EventDetailView(VisibleContentMixin, DetailView):
    model = Event
    template_name = "cf_operations/portal/event_detail.html"
    context_object_name = "event"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = self.object.title
        context["explore_nav"] = "events"
        context["related_sermons"] = (
            Sermon.objects.visible_to(self.request.user)
            .filter(event=self.object)
            .select_related("speaker", "speaker__user")[:20]
        )
        return context


@method_decorator(login_required, name="dispatch")
class SermonListView(VisibleContentMixin, ListView):
    model = Sermon
    template_name = "cf_operations/portal/sermon_list.html"
    context_object_name = "sermons"
    paginate_by = 24

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("event", "speaker", "speaker__user")
            .order_by("-modified_at")
        )

    def _search_q(self, q: str) -> Q:
        return (
            Q(title__icontains=q)
            | Q(scripture_reference__icontains=q)
            | Q(guest_speaker_name__icontains=q)
            | Q(notes__icontains=q)
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = _("Sermons")
        context["explore_nav"] = "sermons"
        return context


@method_decorator(login_required, name="dispatch")
class SermonDetailView(VisibleContentMixin, DetailView):
    model = Sermon
    template_name = "cf_operations/portal/sermon_detail.html"
    context_object_name = "sermon"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("event", "speaker", "speaker__user", "branch")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = self.object.title
        context["explore_nav"] = "sermons"
        return context


@method_decorator(login_required, name="dispatch")
class OutreachListView(VisibleContentMixin, ListView):
    """Outreaches are Events with event_type=OUTREACH (public unless org-only)."""

    model = Event
    template_name = "cf_operations/portal/outreach_list.html"
    context_object_name = "outreaches"
    paginate_by = 24

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(event_type="OUTREACH")
            .order_by("-modified_at", "-start_time")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = _("Outreaches")
        context["explore_nav"] = "outreaches"
        return context
