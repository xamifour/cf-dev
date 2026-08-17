# cf-dev/cf_src/appsinn/cf_social/forms.py

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Comment, Discussion, DiscussionMessage, Post, Report, SocialProfile


class PostForm(forms.ModelForm):
    # Own ChoiceField so we control empty/invalid values before model validation.
    visibility = forms.ChoiceField(
        label=_("Who can see this?"),
        choices=Post.VISIBILITY_CHOICES,
        required=False,
        initial=Post.VISIBILITY_PUBLIC,
        widget=forms.Select(attrs={"class": "s-input"}),
    )

    class Meta:
        model = Post
        fields = ("body", "image", "video", "visibility")
        widgets = {
            "body": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": _("What's on your mind?"),
                    "class": "s-input s-textarea",
                }
            ),
            "image": forms.ClearableFileInput(attrs={"class": "s-input", "accept": "image/*"}),
            "video": forms.ClearableFileInput(
                attrs={"class": "s-input", "accept": "video/*"}
            ),
        }

    @staticmethod
    def _normalize_visibility(value) -> str:
        raw = (value or "").strip()
        if not raw:
            return Post.VISIBILITY_PUBLIC
        aliases = {
            "public": Post.VISIBILITY_PUBLIC,
            "followers": Post.VISIBILITY_FOLLOWERS,
            "followers only": Post.VISIBILITY_FOLLOWERS,
            "private": Post.VISIBILITY_PRIVATE,
            "PUBLIC": Post.VISIBILITY_PUBLIC,
            "FOLLOWERS": Post.VISIBILITY_FOLLOWERS,
            "PRIVATE": Post.VISIBILITY_PRIVATE,
        }
        if raw in aliases:
            return aliases[raw]
        key = raw.lower()
        if key in aliases:
            return aliases[key]
        upper = raw.upper()
        if upper in {
            Post.VISIBILITY_PUBLIC,
            Post.VISIBILITY_FOLLOWERS,
            Post.VISIBILITY_PRIVATE,
        }:
            return upper
        return Post.VISIBILITY_PUBLIC

    def __init__(self, *args, **kwargs):
        # Normalize audience before ChoiceField validates.
        data = kwargs.get("data")
        if data is not None:
            data = data.copy()
            data["visibility"] = self._normalize_visibility(data.get("visibility"))
            kwargs["data"] = data
        super().__init__(*args, **kwargs)
        self.fields["visibility"].choices = list(Post.VISIBILITY_CHOICES)
        if not self.is_bound and not self.initial.get("visibility"):
            self.initial["visibility"] = Post.VISIBILITY_PUBLIC
        self.fields["image"].required = False
        self.fields["video"].required = False

    def clean_visibility(self):
        return self._normalize_visibility(self.cleaned_data.get("visibility"))

    def clean(self):
        cleaned = super().clean()
        body = (cleaned.get("body") or "").strip()
        image = cleaned.get("image")
        video = cleaned.get("video")
        if not body and not image and not video:
            raise forms.ValidationError(
                _("Write something or attach an image/video.")
            )
        cleaned["visibility"] = self._normalize_visibility(
            cleaned.get("visibility")
        )
        return cleaned


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ("body",)
        widgets = {
            "body": forms.TextInput(
                attrs={
                    "placeholder": _("Write a comment…"),
                    "class": "s-input",
                }
            )
        }


class ProfileForm(forms.ModelForm):
    class Meta:
        model = SocialProfile
        fields = (
            "display_name",
            "bio",
            "avatar",
            "cover",
            "website",
            "location",
            "profile_visibility",
            "default_post_visibility",
            "allow_direct_messages",
        )
        widgets = {
            "display_name": forms.TextInput(attrs={"class": "s-input"}),
            "bio": forms.Textarea(attrs={"rows": 4, "class": "s-input s-textarea"}),
            "website": forms.URLInput(attrs={"class": "s-input"}),
            "location": forms.TextInput(attrs={"class": "s-input"}),
            "profile_visibility": forms.Select(attrs={"class": "s-input"}),
            "default_post_visibility": forms.Select(attrs={"class": "s-input"}),
        }


class MessageForm(forms.Form):
    body = forms.CharField(
        max_length=4000,
        widget=forms.Textarea(
            attrs={
                "rows": 2,
                "placeholder": _("Type a message…"),
                "class": "s-input s-textarea",
            }
        ),
    )


class SearchForm(forms.Form):
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": _("Search people and posts…"),
                "class": "s-input",
            }
        ),
    )


class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ("reason",)
        widgets = {
            "reason": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": _("Why are you reporting this?"),
                    "class": "s-input s-textarea",
                }
            )
        }


class DiscussionForm(forms.ModelForm):
    class Meta:
        model = Discussion
        fields = (
            "title",
            "body",
            "audience",
            "organization",
            "branch",
            "zone",
        )
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "s-input",
                    "placeholder": _("Discussion title"),
                }
            ),
            "body": forms.Textarea(
                attrs={
                    "rows": 4,
                    "class": "s-input s-textarea",
                    "placeholder": _("What would you like to discuss? (optional)"),
                }
            ),
            "audience": forms.Select(attrs={"class": "s-input", "id": "id_audience"}),
            "organization": forms.Select(attrs={"class": "s-input"}),
            "branch": forms.Select(attrs={"class": "s-input"}),
            "zone": forms.Select(attrs={"class": "s-input"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["body"].required = False
        self.fields["organization"].required = False
        self.fields["branch"].required = False
        self.fields["zone"].required = False
        self.fields["organization"].empty_label = _("— Select organisation —")
        self.fields["branch"].empty_label = _("— Select branch —")
        self.fields["zone"].empty_label = _("— Select zone —")

        from django.apps import apps

        from cf_users.tenancy import accessible_branch_ids_qs, organizations_for_user_qs

        Organization = apps.get_model("cf_users", "Organization")
        Branch = apps.get_model("cf_users", "Branch")
        Zone = apps.get_model("cf_people", "Zone")

        if user is not None and getattr(user, "is_authenticated", False):
            org_qs = organizations_for_user_qs(user)
            if user.is_superuser:
                branch_qs = Branch.objects.all()
                zone_qs = Zone.objects.all()
            else:
                branch_qs = Branch.objects.filter(id__in=accessible_branch_ids_qs(user))
                zone_qs = Zone.objects.filter(branch_id__in=accessible_branch_ids_qs(user))
        else:
            org_qs = Organization.objects.none()
            branch_qs = Branch.objects.none()
            zone_qs = Zone.objects.none()

        self.fields["organization"].queryset = org_qs.order_by("name")
        self.fields["branch"].queryset = branch_qs.select_related("organization").order_by(
            "name"
        )
        self.fields["zone"].queryset = zone_qs.select_related("branch").order_by("name")

    def clean(self):
        cleaned = super().clean()
        audience = cleaned.get("audience") or Discussion.AUDIENCE_PLATFORM
        if audience == Discussion.AUDIENCE_PLATFORM:
            cleaned["organization"] = None
            cleaned["branch"] = None
            cleaned["zone"] = None
        elif audience == Discussion.AUDIENCE_ORGANIZATION:
            if not cleaned.get("organization"):
                self.add_error(
                    "organization",
                    _("Select an organisation for this audience."),
                )
            cleaned["branch"] = None
            cleaned["zone"] = None
        elif audience == Discussion.AUDIENCE_BRANCH:
            if not cleaned.get("branch"):
                self.add_error("branch", _("Select a branch for this audience."))
            cleaned["zone"] = None
        elif audience == Discussion.AUDIENCE_ZONE:
            if not cleaned.get("zone"):
                self.add_error("zone", _("Select a zone for this audience."))
        title = (cleaned.get("title") or "").strip()
        if not title:
            self.add_error("title", _("Title is required."))
        cleaned["title"] = title
        return cleaned


class DiscussionMessageForm(forms.ModelForm):
    class Meta:
        model = DiscussionMessage
        fields = ("body",)
        widgets = {
            "body": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": _("Write a reply…"),
                    "class": "s-input s-textarea",
                }
            )
        }

    def clean_body(self):
        body = (self.cleaned_data.get("body") or "").strip()
        if not body:
            raise forms.ValidationError(_("Message cannot be empty."))
        return body
