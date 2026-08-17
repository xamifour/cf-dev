# cf-dev/cf_src/cf_users/validators.py

import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_username(username: str):
    """
    Shared username validator.
    Supports:
        - Original username rules
        - Phone style usernames starting with '+'
    """

    if not username:
        raise ValidationError(_("Username is required."))

    # No spaces allowed
    if " " in username:
        raise ValidationError(_("Username cannot contain spaces."))

    # ───────────────────────────────────────────────
    # PHONE NUMBER USERNAME FORMAT (starts with '+')
    # ───────────────────────────────────────────────
    if username.startswith("+"):
        digits = username[1:]

        if not digits:
            raise ValidationError(_("A '+' must be followed by digits."))

        if not digits.isdigit():
            raise ValidationError(_("After '+', only digits 0–9 are allowed (international phone format)."))

        if not (9 <= len(digits) <= 16):
            raise ValidationError(_("Phone-format username must be 9–16 digits long (excluding '+')."))

        return  # VALID — stop here

    # ───────────────────────────────────────────────
    # ORIGINAL USERNAME RULES
    # ───────────────────────────────────────────────

    # Must start with a letter or zero
    if not re.match(r'^[A-Za-z0]', username):
        raise ValidationError(_("Username must start with a letter or zero."))

    underscore_count = username.count("_")
    at_count = username.count("@")
    total_special = underscore_count + at_count

    # Only one special char allowed
    if total_special > 1:
        raise ValidationError(_("Username can contain only one underscore (_) or one @ symbol."))

    # Special char cannot be first
    if "_" in username and username.index("_") == 0:
        raise ValidationError(_("Underscore cannot be at the start."))

    if "@" in username and username.index("@") == 0:
        raise ValidationError(_("@ cannot be at the start."))

    # Valid characters only
    if not re.match(r'^[A-Za-z0-9_@]+$', username):
        raise ValidationError(_("Username contains invalid characters."))

    # Length 9–64 chars
    if not (9 <= len(username) <= 64):
        raise ValidationError(_("Username must be between 9 and 64 characters."))


class PasswordReuseValidator:
    """
    Django password validator class that does not allow re-using
    user's current password.
    """

    def validate(self, password, user=None):
        if user is None:
            return
        if user.check_password(password):
            # The new password is same as the current password
            raise ValidationError(
                _('You cannot re-use your current password. Enter a new password.')
            )

    def get_help_text(self):
        return _('Your password cannot be the same as your current password.')
