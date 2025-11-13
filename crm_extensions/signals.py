"""
CRM Extensions signals for task notifications.

Handles automatic notification creation when tasks are created or assigned.
"""

import logging
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from .models import Task, TaskAssignment

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Task)
def on_task_created(sender, instance, created, **kwargs):
    """
    Create notifications when a task is created.

    Notifications are sent to:
    - All assigned users (if any exist at creation time)
    - Department manager (if task has a department but no specific assignments)
    """
    if not created:
        return

    from notifications.models import Notification

    try:
        # Get assigned users
        assigned_users = instance.assigned_users.all()

        # Build notification message
        task_title = instance.title[:100]  # Truncate if too long
        entity_info = ""
        action_url = None

        # Add entity context to message
        if instance.song:
            entity_info = f" for song '{instance.song.title}'"
            action_url = f"/songs/{instance.song.id}"
        elif instance.opportunity:
            entity_info = f" for opportunity '{instance.opportunity.title}'"
            action_url = f"/opportunities/{instance.opportunity.id}"
        elif instance.deliverable:
            if instance.deliverable.opportunity:
                entity_info = f" for opportunity '{instance.deliverable.opportunity.title}'"
                action_url = f"/opportunities/{instance.deliverable.opportunity.id}"
            else:
                entity_info = f" for deliverable"
                action_url = None
        elif instance.contract:
            entity_info = f" for contract"
            action_url = f"/contracts/{instance.contract.id}"

        message = f'New task assigned to you: "{task_title}"{entity_info}'

        # Create notifications for assigned users
        notifications_created = 0
        for user in assigned_users:
            Notification.objects.create(
                user=user,
                message=message,
                notification_type='task_assigned',
                action_url=action_url,
                metadata={
                    'task_id': instance.id,
                    'task_title': instance.title,
                    'priority': instance.priority,
                    'department': instance.department.name if instance.department else None,
                }
            )
            notifications_created += 1

        # If no specific assignments but has department, notify department manager
        if not assigned_users and instance.department:
            from api.models import Department
            from django.contrib.auth import get_user_model
            User = get_user_model()

            # Get department managers
            managers = User.objects.filter(
                profile__department=instance.department,
                profile__role__code__in=['manager', 'department_manager']
            )

            for manager in managers:
                Notification.objects.create(
                    user=manager,
                    message=f'New task for {instance.department.name}: "{task_title}"{entity_info}',
                    notification_type='task_assigned',
                    action_url=action_url,
                    metadata={
                        'task_id': instance.id,
                        'task_title': instance.title,
                        'priority': instance.priority,
                        'department': instance.department.name,
                    }
                )
                notifications_created += 1

        if notifications_created > 0:
            logger.info(
                f"Task {instance.id}: Created {notifications_created} notification(s) "
                f"for '{instance.title}'"
            )

    except Exception as e:
        logger.error(f"Error creating notifications for task {instance.id}: {e}")


@receiver(m2m_changed, sender=Task.assigned_users.through)
def on_task_assignment_changed(sender, instance, action, pk_set, **kwargs):
    """
    Create notifications when users are assigned to an existing task.

    This handles the case where a task already exists and someone adds
    new assignees to it.
    """
    if action != 'post_add':
        return

    from notifications.models import Notification
    from django.contrib.auth import get_user_model
    User = get_user_model()

    try:
        # Get the newly assigned users
        newly_assigned_users = User.objects.filter(pk__in=pk_set)

        # Build notification message
        task_title = instance.title[:100]
        entity_info = ""
        action_url = None

        if instance.song:
            entity_info = f" for song '{instance.song.title}'"
            action_url = f"/songs/{instance.song.id}"
        elif instance.opportunity:
            entity_info = f" for opportunity '{instance.opportunity.title}'"
            action_url = f"/opportunities/{instance.opportunity.id}"
        elif instance.deliverable:
            if instance.deliverable.opportunity:
                entity_info = f" for opportunity '{instance.deliverable.opportunity.title}'"
                action_url = f"/opportunities/{instance.deliverable.opportunity.id}"
            else:
                entity_info = f" for deliverable"
                action_url = None
        elif instance.contract:
            entity_info = f" for contract"
            action_url = f"/contracts/{instance.contract.id}"

        message = f'You have been assigned to: "{task_title}"{entity_info}'

        # Create notifications
        notifications_created = 0
        for user in newly_assigned_users:
            Notification.objects.create(
                user=user,
                message=message,
                notification_type='task_assigned',
                action_url=action_url,
                metadata={
                    'task_id': instance.id,
                    'task_title': instance.title,
                    'priority': instance.priority,
                    'department': instance.department.name if instance.department else None,
                }
            )
            notifications_created += 1

        if notifications_created > 0:
            logger.info(
                f"Task {instance.id}: Created {notifications_created} notification(s) "
                f"for newly assigned users"
            )

    except Exception as e:
        logger.error(f"Error creating assignment notifications for task {instance.id}: {e}")
