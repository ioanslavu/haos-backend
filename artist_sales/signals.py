"""
Artist Sales signals for Universal Task Automation System.

Handles automation for Opportunity and OpportunityDeliverable changes.
"""

import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Opportunity, OpportunityDeliverable

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Opportunity)
def track_opportunity_field_changes(sender, instance, **kwargs):
    """Track old field values for change detection."""
    if instance.pk:
        try:
            old_opportunity = Opportunity.objects.get(pk=instance.pk)
            instance._old_stage = old_opportunity.stage
            instance._old_status = getattr(old_opportunity, 'status', None)
        except Opportunity.DoesNotExist:
            instance._old_stage = None
            instance._old_status = None
    else:
        instance._old_stage = None
        instance._old_status = None


@receiver(post_save, sender=Opportunity)
def on_opportunity_saved(sender, instance, created, **kwargs):
    """
    Handle Opportunity save events.

    Actions:
    1. Handle stage transitions
    """
    try:
        # Handle stage change
        if hasattr(instance, '_old_stage') and instance._old_stage:
            if instance._old_stage != instance.stage:
                logger.info(
                    f"Opportunity {instance.id}: Stage changed from '{instance._old_stage}' "
                    f"to '{instance.stage}'"
                )

                # Update tasks from previous stages
                from crm_extensions.models import Task
                old_tasks = Task.objects.filter(
                    opportunity=instance,
                    source_stage=instance._old_stage,
                    status__in=['todo', 'in_progress', 'blocked']
                )

                for task in old_tasks:
                    if not task.title.startswith(f'[Previous: {instance._old_stage}]'):
                        task.title = f'[Previous: {instance._old_stage}] {task.title}'
                        task.save(update_fields=['title'])

                if old_tasks.count() > 0:
                    logger.info(
                        f"Opportunity {instance.id}: Updated {old_tasks.count()} task(s) "
                        f"from previous stage"
                    )

    except Exception as e:
        logger.error(f"Error in opportunity post_save signal for Opportunity {instance.id}: {e}")


@receiver(pre_save, sender=OpportunityDeliverable)
def track_deliverable_field_changes(sender, instance, **kwargs):
    """Track old field values for change detection."""
    if instance.pk:
        try:
            old_deliverable = OpportunityDeliverable.objects.get(pk=instance.pk)
            instance._old_status = old_deliverable.status
            instance._old_asset_url = old_deliverable.asset_url
        except OpportunityDeliverable.DoesNotExist:
            instance._old_status = None
            instance._old_asset_url = None
    else:
        instance._old_status = None
        instance._old_asset_url = None


@receiver(post_save, sender=OpportunityDeliverable)
def on_deliverable_saved(sender, instance, created, **kwargs):
    """
    Handle OpportunityDeliverable save events.

    Actions:
    1. Mark related task as done when asset_url is added
    2. Reopen task when status changes to 'revision_requested'
    3. Track full history of task status changes
    4. Send notifications to Sales department when asset is uploaded
    """
    from crm_extensions.models import Task
    from django.utils import timezone
    from django.contrib.auth import get_user_model
    from api.models import Department
    from notifications.services import NotificationService

    User = get_user_model()

    try:
        # Find tasks linked to this deliverable using explicit FK
        deliverable_tasks = Task.objects.filter(deliverable=instance)

        for task in deliverable_tasks:
            # 1. Mark task as done when asset_url is added
            if instance.asset_url and not instance._old_asset_url:
                if task.status != 'done':
                    task.status = 'done'
                    # Track in history
                    if not task.notes:
                        task.notes = ''
                    task.notes += f"\n[{timezone.now().isoformat()}] Completed: Asset uploaded at {instance.asset_url}"
                    task.save(update_fields=['status', 'notes'])
                    logger.info(
                        f"Deliverable {instance.id}: Marked task {task.id} as done (asset uploaded)"
                    )

                    # 4. Send notifications to Sales department
                    try:
                        # Get deliverable type display name
                        deliverable_type = instance.get_deliverable_type_display()
                        opportunity = instance.opportunity

                        # Notification message
                        message = f"Marketing completed: {deliverable_type} for {opportunity.title}"
                        action_url = f"/opportunities/{opportunity.id}?tab=deliverables"

                        # Get Sales Department
                        try:
                            sales_dept = Department.objects.get(name='Sales Department')

                            # Notify Sales managers
                            sales_managers = User.objects.filter(
                                profile__department=sales_dept,
                                profile__role__level__gte=300  # Manager level
                            )

                            for manager in sales_managers:
                                NotificationService.create_notification(
                                    user=manager,
                                    message=message,
                                    notification_type='system',
                                    action_url=action_url,
                                    metadata={
                                        'task_id': task.id,
                                        'deliverable_id': instance.id,
                                        'opportunity_id': opportunity.id,
                                        'deliverable_type': instance.deliverable_type,
                                        'asset_url': instance.asset_url
                                    }
                                )

                            logger.info(
                                f"Deliverable {instance.id}: Sent notifications to {sales_managers.count()} Sales managers"
                            )

                        except Department.DoesNotExist:
                            logger.warning("Sales Department not found for notifications")

                        # Notify opportunity owner
                        if opportunity.owner:
                            NotificationService.create_notification(
                                user=opportunity.owner,
                                message=message,
                                notification_type='system',
                                action_url=action_url,
                                metadata={
                                    'task_id': task.id,
                                    'deliverable_id': instance.id,
                                    'opportunity_id': opportunity.id,
                                    'deliverable_type': instance.deliverable_type,
                                    'asset_url': instance.asset_url
                                }
                            )
                            logger.info(
                                f"Deliverable {instance.id}: Notified opportunity owner {opportunity.owner.username}"
                            )

                    except Exception as notification_error:
                        logger.error(
                            f"Error sending notifications for deliverable {instance.id}: {notification_error}"
                        )

            # 2. Reopen task when status changes to 'revision_requested'
            if hasattr(instance, '_old_status') and instance._old_status:
                if instance._old_status != 'revision_requested' and instance.status == 'revision_requested':
                    if task.status == 'done':
                        task.status = 'in_progress'
                        # Track in history
                        if not task.notes:
                            task.notes = ''
                        task.notes += f"\n[{timezone.now().isoformat()}] Reopened: Revision requested"
                        task.save(update_fields=['status', 'notes'])
                        logger.info(
                            f"Deliverable {instance.id}: Reopened task {task.id} (revision requested)"
                        )

    except Exception as e:
        logger.error(f"Error in deliverable post_save signal for OpportunityDeliverable {instance.id}: {e}")
