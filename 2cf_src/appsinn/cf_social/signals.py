# cf-dev/cf_src/appsinn/cf_social/signals.py

"""Ensure every user has a SocialProfile."""

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import SocialProfile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_social_profile(sender, instance, created, **kwargs):
    if created:
        SocialProfile.objects.get_or_create(user=instance)
