# cf-dev/cf_src/appsinn/cf_users/forms.py

"""Forms for users and organisations."""

from django import forms
from django.apps import apps
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import UserChangeForm as DjangoUserChangeForm
from django.contrib.auth.forms import UserCreationForm as DjangoUserCreationForm
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet
from django.utils.translation import gettext_lazy as _
from django_ckeditor_5.widgets import CKEditor5Widget
from phonenumber_field.formfields import PhoneNumberField
from PIL import Image

from .models import Organization, User
from .utils import sanitize_svg

MAX_IMAGE_SIZE_MB = 0.3
MAX_IMAGE_SIZE_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024
MAX_SVG_LENGTH = 50000


class PortalAuthenticationForm(AuthenticationForm):
    """
    Organisation portal login form.

    Accepts username, email, or phone number via the custom auth backend.
    Staff and superusers may use the portal as well as ``/admin/``.
    Non-staff users need organisation or branch membership.
    """

    username = forms.CharField(
        label=_("Username, email, or phone"),
        max_length=254,
        widget=forms.TextInput(
            attrs={
                "autocomplete": "username",
                "autocapitalize": "none",
                "spellcheck": "false",
                "placeholder": _("e.g. jane@church.org or +233201234567"),
                "class": "form-control",
            }
        ),
    )
    password = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "current-password",
                "placeholder": _("Enter your password"),
                "class": "form-control",
            }
        ),
    )
    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": _(
            "Please enter a correct username, email, or phone number and password. "
            "Note that both fields may be case-sensitive."
        ),
        "inactive": _("This account is inactive."),
        "no_org_access": _(
            "Your account is not linked to any organisation or branch. "
            "Contact your organisation administrator."
        ),
    }

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request=request, *args, **kwargs)
        self.fields["username"].widget.attrs["autofocus"] = True

    def clean(self):
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if username is not None and password:
            self.user_cache = authenticate(
                self.request, username=username.strip(), password=password
            )
            if self.user_cache is None:
                raise self.get_invalid_login_error()
            self.confirm_login_allowed(self.user_cache)
            self._confirm_portal_access(self.user_cache)

        return self.cleaned_data

    def _confirm_portal_access(self, user) -> None:
        """
        Allow portal entry for:

        - staff / superusers (they may also use ``/admin/``), or
        - users with organisation or branch membership.
        """
        if user.is_superuser or user.is_staff:
            return

        has_org = bool(getattr(user, "organizations_managed", None)) or user.org_roles.exists()
        has_branch = bool(getattr(user, "accessible_branches", None)) or user.branch_roles.exists()

        if has_org or has_branch:
            return

        raise ValidationError(
            self.error_messages["no_org_access"],
            code="no_org_access",
        )


class RequiredInlineFormSet(BaseInlineFormSet):
    def _construct_form(self, i, **kwargs):
        form = super()._construct_form(i, **kwargs)
        form.empty_permitted = getattr(self.instance, "is_superuser", False)
        return form


class UserFormMixin:
    email = forms.EmailField(label=_("Email"), max_length=254, required=True)

    def validate_user_groups(self, cleaned_data):
        """
        Staff users should belong to a permission group.

        Only enforced when the form actually includes a ``groups`` field
        (change form). The add form has no groups widget — requiring it there
        raised ValueError: 'UserForm' has no field named 'groups'.
        """
        if "groups" not in self.fields:
            return

        is_staff = cleaned_data.get("is_staff")
        is_superuser = cleaned_data.get("is_superuser")
        groups = cleaned_data.get("groups")

        # ModelMultipleChoiceField may return a queryset / list.
        has_groups = bool(groups) and (
            groups.exists() if hasattr(groups, "exists") else len(list(groups)) > 0
        )

        if is_staff and not is_superuser and not has_groups:
            raise ValidationError(
                {"groups": _("A staff user must belong to at least one group.")}
            )

    def clean(self):
        cleaned_data = super().clean()
        self.validate_user_groups(cleaned_data)
        return cleaned_data


class UserCreationForm(UserFormMixin, DjangoUserCreationForm):
    phone_number = PhoneNumberField(
        widget=forms.TextInput(),
        required=True,
        help_text=_(
            "Enter a valid international phone number (preferably WhatsApp), e.g. +233201234567."
        ),
    )

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "password1",
            "password2",
            "first_name",
            "last_name",
            "phone_number",
            "address",
            "city",
            "country",
            "is_staff",
            "is_active",
        )


class UserChangeForm(UserFormMixin, DjangoUserChangeForm):
    class Meta:
        model = User
        fields = "__all__"


class OrganizationForm(forms.ModelForm):
    """Handles both raster logo and inline SVG safely."""

    class Meta:
        model = Organization
        fields = "__all__"
        widgets = {
            "logo_svg": forms.Textarea(
                attrs={
                    "rows": 10,
                    "cols": 80,
                    "placeholder": "Paste your SVG XML code here...",
                }
            ),
            "description": forms.Textarea(attrs={"rows": 5}),
            "notes": CKEditor5Widget(config_name="default"),
        }

    def clean_logo(self):
        logo = self.cleaned_data.get("logo")
        if not logo:
            return logo

        if getattr(logo, "size", 0) > MAX_IMAGE_SIZE_BYTES:
            raise ValidationError(
                _("Image must be smaller than %(size)s MB.")
                % {"size": MAX_IMAGE_SIZE_MB}
            )

        name = logo.name.lower()
        if name.endswith(".svg"):
            raise ValidationError(
                _("Please use the 'SVG logo' field for SVG content.")
            )

        try:
            img = Image.open(logo)
            img.verify()
            logo.seek(0)
            img = Image.open(logo)
            fmt = (img.format or "").lower()
        except Exception as exc:
            raise ValidationError(
                _("Upload a valid image file (PNG, JPG, JPEG).")
            ) from exc

        if fmt not in {"jpeg", "jpg", "png"}:
            raise ValidationError(_("Only PNG, JPEG and JPG formats are allowed."))

        return logo

    def clean_logo_svg(self):
        svg = (self.cleaned_data.get("logo_svg") or "").strip()
        if not svg:
            return svg

        if len(svg) > MAX_SVG_LENGTH:
            raise ValidationError(_("SVG content is too large (max 50 KB)."))

        if not svg.lstrip().startswith("<svg"):
            raise ValidationError(_("Invalid SVG: must start with <svg ...> tag."))

        try:
            return sanitize_svg(svg)
        except Exception as exc:
            raise ValidationError(_("Invalid SVG: %(error)s") % {"error": exc}) from exc

    def clean_code(self):
        """Organisation codes are system-generated and immutable."""
        if self.instance.pk:
            return self.instance.code
        # On create, leave empty so AutoIncrementCodeMixin assigns ORG########.
        return self.cleaned_data.get("code") or None


class OrganizationUserForm(forms.ModelForm):
    class Meta:
        model = apps.get_model("cf_users", "OrganizationUser")
        fields = ["organization", "role", "is_org_manager", "is_admin"]


class OrganizationOwnerForm(forms.ModelForm):
    class Meta:
        model = apps.get_model("cf_users", "OrganizationOwner")
        fields = ["organization_user"]
