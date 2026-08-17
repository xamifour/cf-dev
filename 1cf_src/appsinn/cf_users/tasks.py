# cf-dev/cf_src/cf_users/tasks.py

import logging
import random
from time import sleep

from celery import shared_task
from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import UNUSABLE_PASSWORD_PREFIX
from django.contrib.sites.models import Site
from django.db.models import Q
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import translation
from django.utils.timezone import now, timedelta
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)

User = get_user_model()


# ---------------------------------------------------------------------------
# Password Expiration Notifications
# ---------------------------------------------------------------------------
@shared_task
def password_expiration_email():
    """
    Notify users whose password will expire in exactly 7 days.
    """
    from . import settings as app_settings

    if (
        not app_settings.USER_PASSWORD_EXPIRATION
        and not app_settings.STAFF_USER_PASSWORD_EXPIRATION
    ):
        return

    expiry_date = now().date() + timedelta(days=7)

    query = Q()
    if app_settings.USER_PASSWORD_EXPIRATION:
        query |= Q(
            is_staff=False,
            password_updated=expiry_date - timedelta(days=app_settings.USER_PASSWORD_EXPIRATION),
        )
    if app_settings.STAFF_USER_PASSWORD_EXPIRATION:
        query |= Q(
            is_staff=True,
            password_updated=expiry_date - timedelta(days=app_settings.STAFF_USER_PASSWORD_EXPIRATION),
        )

    qs = User.objects.exclude(
        password__startswith=UNUSABLE_PASSWORD_PREFIX
    ).filter(
        emailaddress__verified=True,
    ).filter(query)

    current_site = Site.objects.get_current()
    email_count = 0

    for user in qs.iterator():
        with translation.override(user.language):
            # Import here to avoid circular imports
            from cf_communications.utils import send_email

            send_email(
                subject=_("Action Required: Password Expiry Notice"),
                body_text=render_to_string(
                    "account/email/password_expiration_message.txt",
                    context={"username": user.username, "expiry_date": expiry_date},
                ).strip(),
                body_html=render_to_string(
                    "account/email/password_expiration_message.html",
                    context={"username": user.username, "expiry_date": expiry_date},
                ).strip(),
                recipients=[user.email],
                extra_context={
                    "call_to_action_url": f"https://{current_site.domain}{reverse('account_change_password')}",
                    "call_to_action_text": _("Change password"),
                },
            )

        email_count += 1
        if email_count >= 10:
            sleep(random.randint(1, 3))
            email_count = 0


# ---------------------------------------------------------------------------
# Cache Invalidation Tasks
# ---------------------------------------------------------------------------
@shared_task
def invalidate_user_access_cache(user_pk):
    """Invalidate a single user's access cache (organizations & branches)."""
    try:
        user = User.objects.get(pk=user_pk)
        user._invalidate_access_cache()
    except User.DoesNotExist:
        logger.warning("User with pk=%s does not exist. Skipping cache invalidation.", user_pk)
    except Exception as e:  # noqa: BLE001
        logger.error("Failed to invalidate access cache for user %s: %s", user_pk, e)


@shared_task
def invalidate_org_membership_cache(organization_pk):
    """
    Invalidate access cache for all users belonging to an organization.
    Used when organization.is_active changes.
    """
    try:
        OrganizationUser = apps.get_model("cf_users", "OrganizationUser")
        org_users = OrganizationUser.objects.filter(
            organization_id=organization_pk
        ).select_related("user").only("user_id")

        for ou in org_users.iterator():
            invalidate_user_access_cache.delay(ou.user_id)

    except Exception as e:  # noqa: BLE001
        logger.error("Failed to invalidate org membership cache for org %s: %s", organization_pk, e)


@shared_task
def invalidate_all_user_access_caches():
    """
    Emergency task: invalidate access cache for ALL users.
    Use sparingly (e.g. after major permission changes).
    """
    try:
        for user in User.objects.only("pk").iterator():
            invalidate_user_access_cache.delay(user.pk)
    except Exception as e:  # noqa: BLE001
        logger.error("Failed to invalidate all user caches: %s", e)


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------
def trigger_user_cache_invalidation(user):
    """Convenience helper to call from signals or views."""
    if user and hasattr(user, "pk"):
        invalidate_user_access_cache.delay(user.pk)
        