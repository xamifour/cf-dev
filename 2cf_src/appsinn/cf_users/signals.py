# cf-dev/cf_src/cf_users/signals.py

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .permissions import seed_default_organization_groups
from .tasks import (
    invalidate_org_membership_cache,
    invalidate_user_access_cache,
)


# ---------------------------------------------------------------------------
# Organization & OrganizationUser signals
# ---------------------------------------------------------------------------
@receiver(post_save, sender="cf_users.Organization")
def seed_groups_on_organization_create(sender, instance, created, **kwargs):
    """Seed default permission groups for each new organisation."""
    if created:
        seed_default_organization_groups(instance)


@receiver([post_save, post_delete], sender="cf_users.OrganizationUser")
def invalidate_on_org_user_change(sender, instance, **kwargs):
    """Invalidate user access cache when OrganizationUser is created/updated/deleted."""
    user = getattr(instance, "user", None)
    if user and hasattr(user, "pk"):
        invalidate_user_access_cache.delay(user.pk)


@receiver([post_save, post_delete], sender="cf_users.OrganizationOwner")
def invalidate_on_org_owner_change(sender, instance, **kwargs):
    """Invalidate cache when OrganizationOwner changes."""
    user = getattr(instance.organization_user, "user", None) if hasattr(instance, "organization_user") else None
    if user and hasattr(user, "pk"):
        invalidate_user_access_cache.delay(user.pk)


@receiver(pre_save, sender="cf_users.Organization")
def trigger_cache_invalidation_on_org_status_change(sender, instance, **kwargs):
    """Invalidate all members' cache when organization active status changes."""
    if not instance.pk or instance._state.adding:
        return

    try:
        old = sender.objects.only("is_active").get(pk=instance.pk)
        if old.is_active != instance.is_active:
            invalidate_org_membership_cache.delay(instance.pk)
    except sender.DoesNotExist:
        pass


# ---------------------------------------------------------------------------
# Branch signals (for future expansion)
# ---------------------------------------------------------------------------
@receiver([post_save, post_delete], sender="cf_users.BranchUser")
def invalidate_on_branch_user_change(sender, instance, **kwargs):
    """Invalidate user access cache when BranchUser changes."""
    user = getattr(instance, "user", None)
    if user and hasattr(user, "pk"):
        invalidate_user_access_cache.delay(user.pk)


@receiver([post_save, post_delete], sender="cf_users.OrganizationGroupMembership")
def invalidate_on_org_group_membership_change(sender, instance, **kwargs):
    """Permissions depend on group membership — clear auth caches."""
    user = getattr(instance, "user", None)
    if user and hasattr(user, "pk"):
        if hasattr(user, "_org_group_perm_cache"):
            delattr(user, "_org_group_perm_cache")
        invalidate_user_access_cache.delay(user.pk)


# Optional: Invalidate when Branch active status changes
@receiver(pre_save, sender="cf_users.Branch")
def trigger_cache_invalidation_on_branch_status_change(sender, instance, **kwargs):
    if not instance.pk or instance._state.adding:
        return
    try:
        old = sender.objects.only("active").get(pk=instance.pk)
        if old.active != instance.active:
            # You can create a similar task for branch-wide invalidation if needed
            # For now we invalidate per user via BranchUser signals
            pass
    except sender.DoesNotExist:
        pass
        