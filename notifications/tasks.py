"""
Celery tasks for automated notification alerts.

These tasks run periodically to check for:
- Tasks due tomorrow
- Tasks due in a few hours (urgent)
- Tasks without updates for too long (inactivity)
- Campaigns ending soon
"""

from celery import shared_task
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
from .services import NotificationService


@shared_task(name='notifications.check_tasks_due_tomorrow')
def check_tasks_due_tomorrow():
    """
    Check for tasks due tomorrow and send notifications.
    Runs daily at 9:00 AM.
    """
    from crm_extensions.models import Task

    now = timezone.now()
    tomorrow_start = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_end = tomorrow_start + timedelta(days=1)

    # Find tasks due tomorrow that are not done/cancelled
    tasks_due_tomorrow = Task.objects.filter(
        due_date__gte=tomorrow_start,
        due_date__lt=tomorrow_end,
        status__in=['todo', 'in_progress', 'blocked', 'review']
    ).select_related('assigned_to')

    notifications_sent = 0

    for task in tasks_due_tomorrow:
        if task.assigned_to:
            # Check user preferences
            from .models import NotificationPreferences
            preferences = NotificationPreferences.get_or_create_for_user(task.assigned_to)

            # Skip if alert type disabled or all alerts muted
            if not preferences.deadline_tomorrow_enabled or preferences.mute_all_alerts:
                continue

            # Create notification
            NotificationService.create_notification(
                user=task.assigned_to,
                message=f"� Task due tomorrow: {task.title}",
                notification_type='system',
                related_object=task,
                action_url=f"/task-management?task={task.id}",
                metadata={
                    'alert_type': 'deadline_tomorrow',
                    'task_id': task.id,
                    'task_title': task.title,
                    'due_date': task.due_date.isoformat(),
                    'priority': task.priority,
                }
            )
            notifications_sent += 1

    return f"Sent {notifications_sent} tomorrow deadline notifications"


@shared_task(name='notifications.check_tasks_due_soon')
def check_tasks_due_soon(hours=None):
    """
    Check for tasks due in the next few hours and send urgent notifications.
    Runs every 2 hours during work hours.
    Uses each user's custom urgent_deadline_hours preference.

    Args:
        hours: Maximum hours to look ahead (uses largest user preference if None)
    """
    from crm_extensions.models import Task
    from .models import NotificationPreferences

    now = timezone.now()

    # Use max hours threshold from all users if not specified (default 24)
    max_hours = hours if hours is not None else 24
    deadline = now + timedelta(hours=max_hours)

    # Find tasks due soon that are not done/cancelled
    tasks_due_soon = Task.objects.filter(
        due_date__gte=now,
        due_date__lte=deadline,
        status__in=['todo', 'in_progress', 'blocked', 'review']
    ).select_related('assigned_to')

    notifications_sent = 0

    for task in tasks_due_soon:
        if task.assigned_to:
            # Check user preferences
            preferences = NotificationPreferences.get_or_create_for_user(task.assigned_to)

            # Skip if alert type disabled or all alerts muted
            if not preferences.deadline_urgent_enabled or preferences.mute_all_alerts:
                continue

            # Calculate hours remaining
            hours_remaining = (task.due_date - now).total_seconds() / 3600

            # Only send if within user's custom threshold
            if hours_remaining > preferences.urgent_deadline_hours:
                continue

            hours_text = f"{int(hours_remaining)} hour{'s' if hours_remaining != 1 else ''}"

            # Create urgent notification
            NotificationService.create_notification(
                user=task.assigned_to,
                message=f"=� URGENT: Task due in {hours_text}: {task.title}",
                notification_type='system',
                related_object=task,
                action_url=f"/task-management?task={task.id}",
                metadata={
                    'alert_type': 'deadline_urgent',
                    'task_id': task.id,
                    'task_title': task.title,
                    'due_date': task.due_date.isoformat(),
                    'hours_remaining': hours_remaining,
                    'priority': task.priority,
                }
            )
            notifications_sent += 1

    return f"Sent {notifications_sent} urgent deadline notifications"


@shared_task(name='notifications.check_inactive_tasks')
def check_inactive_tasks(days_threshold=7):
    """
    Check for tasks without updates for too long and send notifications.
    Runs daily at 10:00 AM.

    Args:
        days_threshold: Number of days without update to trigger alert (default: 7)
    """
    from crm_extensions.models import Task

    now = timezone.now()
    threshold_date = now - timedelta(days=days_threshold)

    # Find active tasks that haven't been updated in a while
    inactive_tasks = Task.objects.filter(
        status__in=['todo', 'in_progress', 'blocked', 'review'],
        updated_at__lt=threshold_date
    ).select_related('assigned_to')

    notifications_sent = 0

    for task in inactive_tasks:
        if task.assigned_to:
            # Check user preferences
            from .models import NotificationPreferences
            preferences = NotificationPreferences.get_or_create_for_user(task.assigned_to)

            # Skip if alert type disabled or all alerts muted
            if not preferences.task_inactivity_enabled or preferences.mute_all_alerts:
                continue

            # Calculate days since last update
            days_inactive = (now - task.updated_at).days

            # Only send if exceeds user's custom threshold
            if days_inactive < preferences.inactivity_days:
                continue

            # Create notification
            NotificationService.create_notification(
                user=task.assigned_to,
                message=f"� No updates for {days_inactive} days: {task.title}",
                notification_type='system',
                related_object=task,
                action_url=f"/task-management?task={task.id}",
                metadata={
                    'alert_type': 'task_inactive',
                    'task_id': task.id,
                    'task_title': task.title,
                    'days_inactive': days_inactive,
                    'last_updated': task.updated_at.isoformat(),
                    'status': task.status,
                }
            )
            notifications_sent += 1

    return f"Sent {notifications_sent} inactivity notifications"


@shared_task(name='notifications.check_campaigns_ending_soon')
def check_campaigns_ending_soon(days_ahead=7):
    """
    Check for campaigns ending soon and send notifications.
    Runs daily at 9:00 AM.

    Args:
        days_ahead: Number of days to look ahead for ending campaigns (default: 7)
    """
    from campaigns.models import Campaign

    now = timezone.now()
    end_date_threshold = (now + timedelta(days=days_ahead)).date()
    today = now.date()

    # Find active campaigns ending soon
    campaigns_ending = Campaign.objects.filter(
        end_date__gte=today,
        end_date__lte=end_date_threshold,
        status__in=['confirmed', 'active']
    ).select_related('department')

    notifications_sent = 0

    for campaign in campaigns_ending:
        # Calculate days remaining
        days_remaining = (campaign.end_date - today).days

        # Get department users to notify
        if campaign.department:
            # Notify department manager
            if hasattr(campaign.department, 'manager') and campaign.department.manager:
                # Check manager preferences
                from .models import NotificationPreferences
                manager_prefs = NotificationPreferences.get_or_create_for_user(campaign.department.manager)

                # Only send if enabled and within threshold
                if (manager_prefs.campaign_ending_enabled and
                    not manager_prefs.mute_all_alerts and
                    days_remaining <= manager_prefs.campaign_ending_days):

                    NotificationService.create_notification(
                        user=campaign.department.manager,
                        message=f"=� Campaign ending in {days_remaining} day{'s' if days_remaining != 1 else ''}: {campaign.campaign_name}",
                        notification_type='system',
                        related_object=campaign,
                        action_url=f"/crm?campaign={campaign.id}",
                        metadata={
                            'alert_type': 'campaign_ending',
                            'campaign_id': campaign.id,
                            'campaign_name': campaign.campaign_name,
                            'end_date': campaign.end_date.isoformat(),
                            'days_remaining': days_remaining,
                            'client': str(campaign.client),
                        }
                    )
                    notifications_sent += 1

            # Notify all department employees with tasks on this campaign
            from crm_extensions.models import Task
            from django.contrib.auth import get_user_model
            User = get_user_model()

            assigned_users = Task.objects.filter(
                campaign=campaign,
                status__in=['todo', 'in_progress', 'blocked', 'review']
            ).values_list('assigned_to', flat=True).distinct()

            for user_id in assigned_users:
                if user_id and user_id != campaign.department.manager.id:
                    try:
                        user = User.objects.get(id=user_id)

                        # Check user preferences
                        from .models import NotificationPreferences
                        user_prefs = NotificationPreferences.get_or_create_for_user(user)

                        # Only send if enabled and within threshold
                        if (user_prefs.campaign_ending_enabled and
                            not user_prefs.mute_all_alerts and
                            days_remaining <= user_prefs.campaign_ending_days):

                            NotificationService.create_notification(
                                user=user,
                                message=f"=� Campaign ending in {days_remaining} day{'s' if days_remaining != 1 else ''}: {campaign.campaign_name}",
                                notification_type='system',
                                related_object=campaign,
                                action_url=f"/crm?campaign={campaign.id}",
                                metadata={
                                    'alert_type': 'campaign_ending',
                                    'campaign_id': campaign.id,
                                    'campaign_name': campaign.campaign_name,
                                    'end_date': campaign.end_date.isoformat(),
                                    'days_remaining': days_remaining,
                                }
                            )
                            notifications_sent += 1
                    except User.DoesNotExist:
                        pass

    return f"Sent {notifications_sent} campaign ending notifications"


@shared_task(name='notifications.check_overdue_tasks')
def check_overdue_tasks():
    """
    Check for overdue tasks and send notifications.
    Runs every 4 hours during work hours.
    """
    from crm_extensions.models import Task

    now = timezone.now()

    # Find overdue tasks
    overdue_tasks = Task.objects.filter(
        due_date__lt=now,
        status__in=['todo', 'in_progress', 'blocked', 'review']
    ).select_related('assigned_to')

    notifications_sent = 0

    for task in overdue_tasks:
        if task.assigned_to:
            # Check user preferences
            from .models import NotificationPreferences
            preferences = NotificationPreferences.get_or_create_for_user(task.assigned_to)

            # Skip if alert type disabled or all alerts muted
            if not preferences.task_overdue_enabled or preferences.mute_all_alerts:
                continue

            # Calculate how overdue
            days_overdue = (now - task.due_date).days

            # Create notification
            NotificationService.create_notification(
                user=task.assigned_to,
                message=f"=4 OVERDUE by {days_overdue} day{'s' if days_overdue != 1 else ''}: {task.title}",
                notification_type='system',
                related_object=task,
                action_url=f"/task-management?task={task.id}",
                metadata={
                    'alert_type': 'task_overdue',
                    'task_id': task.id,
                    'task_title': task.title,
                    'due_date': task.due_date.isoformat(),
                    'days_overdue': days_overdue,
                    'priority': task.priority,
                }
            )
            notifications_sent += 1

    return f"Sent {notifications_sent} overdue task notifications"
