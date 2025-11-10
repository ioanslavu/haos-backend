"""
Campaign signals for Universal Task Automation System.

Handles automation for Campaign changes.
"""

import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Campaign

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Campaign)
def track_campaign_field_changes(sender, instance, **kwargs):
    """Track old field values for change detection."""
    if instance.pk:
        try:
            old_campaign = Campaign.objects.get(pk=instance.pk)
            instance._old_status = old_campaign.status
        except Campaign.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=Campaign)
def on_campaign_saved(sender, instance, created, **kwargs):
    """
    Handle Campaign save events.

    Actions:
    1. Handle status changes
    """
    try:
        # Handle status change
        if hasattr(instance, '_old_status') and instance._old_status:
            if instance._old_status != instance.status:
                logger.info(
                    f"Campaign {instance.id}: Status changed from '{instance._old_status}' "
                    f"to '{instance.status}'"
                )

    except Exception as e:
        logger.error(f"Error in campaign post_save signal for Campaign {instance.id}: {e}")
