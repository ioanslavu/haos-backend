"""
Alert generation service for Song Workflow system.

Creates in-app notifications when workflow events occur.
"""

from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


class SongAlertService:
    """
    Service for creating workflow alerts/notifications.

    All methods are static and create SongAlert instances based on events.
    """

    @staticmethod
    def create_stage_transition_alert(song, from_stage, to_stage, user):
        """
        Creates alert when song transitions to new stage.

        Notifies the target department that a new song has arrived in their queue.

        Args:
            song: Song instance
            from_stage: Previous stage string
            to_stage: New stage string
            user: User who triggered the transition

        Returns:
            SongAlert instance (or None if model doesn't exist yet)
        """
        from catalog.models import SongAlert
        from catalog.permissions import get_department_for_stage
        from api.models import Department

        target_dept_code = get_department_for_stage(to_stage)
        if not target_dept_code:
            return None

        try:
            target_dept = Department.objects.get(code=target_dept_code)
        except Department.DoesNotExist:
            return None

        alert = SongAlert.objects.create(
            song=song,
            alert_type='stage_transition',
            target_department=target_dept,
            title=f'New Song: {song.title}',
            message=f'{user.get_full_name()} moved "{song.title}" from {from_stage} to {to_stage}. Please review and take action.',
            action_url=f'/songs/{song.id}/',
            action_label='View Song',
            priority='important'
        )

        # Also notify assigned user if exists
        if song.assigned_user:
            SongAlert.objects.create(
                song=song,
                alert_type='assignment',
                target_user=song.assigned_user,
                title=f'Assigned: {song.title}',
                message=f'You have been assigned to work on "{song.title}" in {to_stage} stage.',
                action_url=f'/songs/{song.id}/',
                action_label='View Song',
                priority='important'
            )

        return alert

    @staticmethod
    def create_overdue_alert(song):
        """
        Creates alert for overdue songs.

        Should be called by a daily cron job to check for overdue songs.

        Args:
            song: Song instance

        Returns:
            List of SongAlert instances created
        """
        # This requires SongAlert model
        # Placeholder implementation:

        # from catalog.models import SongAlert
        # from api.models import User
        #
        # alerts = []
        #
        # if not song.stage_deadline:
        #     return alerts
        #
        # if song.stage_deadline >= timezone.now().date():
        #     return alerts  # Not overdue yet
        #
        # # Alert assigned user
        # if song.assigned_user:
        #     alert = SongAlert.objects.create(
        #         song=song,
        #         alert_type='overdue',
        #         target_user=song.assigned_user,
        #         title=f'OVERDUE: {song.title}',
        #         message=f'"{song.title}" is overdue in {song.stage} stage. Deadline was {song.stage_deadline}.',
        #         action_url=f'/songs/{song.id}/',
        #         action_label='View Song',
        #         priority='urgent'
        #     )
        #     alerts.append(alert)
        #
        # # Also alert department managers
        # if song.assigned_department:
        #     dept_managers = User.objects.filter(
        #         profile__department=song.assigned_department,
        #         profile__role__level__gte=300  # Manager level
        #     )
        #
        #     for manager in dept_managers:
        #         alert = SongAlert.objects.create(
        #             song=song,
        #             alert_type='overdue',
        #             target_user=manager,
        #             title=f'Team Song Overdue: {song.title}',
        #             message=f'"{song.title}" assigned to {song.assigned_user.get_full_name() if song.assigned_user else "unassigned"} is overdue.',
        #             action_url=f'/songs/{song.id}/',
        #             action_label='View Song',
        #             priority='urgent'
        #         )
        #         alerts.append(alert)
        #
        # return alerts

        return []

    @staticmethod
    def create_send_to_digital_alert(song, user):
        """
        Special alert for "Send to Digital" action.

        This is a high-priority alert that creates an urgent notification
        for the Digital department.

        Args:
            song: Song instance
            user: User who clicked "Send to Digital"

        Returns:
            SongAlert instance
        """
        from catalog.models import SongAlert
        from api.models import Department

        try:
            digital_dept = Department.objects.get(code='digital')
        except Department.DoesNotExist:
            return None

        alert = SongAlert.objects.create(
            song=song,
            alert_type='sent_to_digital',
            target_department=digital_dept,
            title=f'Ready for Distribution: {song.title}',
            message=f'{user.get_full_name()} from Label has sent "{song.title}" to Digital. All assets and metadata are ready.',
            action_url=f'/songs/{song.id}/',
            action_label='Create Release',
            priority='urgent'
        )

        return alert

    @staticmethod
    def create_asset_submitted_alert(song, user):
        """
        Alert when Marketing submits assets to Label for review.

        Args:
            song: Song instance
            user: Marketing user who submitted

        Returns:
            SongAlert instance
        """
        from catalog.models import SongAlert
        from api.models import Department

        try:
            label_dept = Department.objects.get(code='label')
        except Department.DoesNotExist:
            return None

        alert = SongAlert.objects.create(
            song=song,
            alert_type='asset_submitted',
            target_department=label_dept,
            title=f'Assets Ready for Review: {song.title}',
            message=f'{user.get_full_name()} from Marketing has submitted assets for "{song.title}". Please review and approve or reject.',
            action_url=f'/songs/{song.id}/',
            action_label='Review Assets',
            priority='important'
        )

        return alert

    @staticmethod
    def create_asset_reviewed_alert(song, asset, action, user):
        """
        Alert when Label reviews (approves/rejects) marketing assets.

        Args:
            song: Song instance
            asset: SongAsset instance that was reviewed
            action: 'approved' | 'rejected' | 'revision_requested'
            user: Label user who reviewed

        Returns:
            SongAlert instance
        """
        from catalog.models import SongAlert
        from api.models import Department

        try:
            marketing_dept = Department.objects.get(code='marketing')
        except Department.DoesNotExist:
            return None

        action_text = {
            'approved': 'approved',
            'rejected': 'rejected',
            'revision_requested': 'requested revisions for'
        }.get(action, 'reviewed')

        alert_type = {
            'approved': 'asset_approved',
            'rejected': 'asset_rejected',
            'revision_requested': 'asset_rejected'
        }.get(action, 'asset_approved')

        priority = 'info' if action == 'approved' else 'important'

        alert = SongAlert.objects.create(
            song=song,
            alert_type=alert_type,
            target_department=marketing_dept,
            title=f'Asset {action_text.title()}: {song.title}',
            message=f'{user.get_full_name()} from Label has {action_text} your asset "{asset.title or asset.asset_type}" for "{song.title}".',
            action_url=f'/songs/{song.id}/',
            action_label='View Song',
            priority=priority
        )

        return alert

    @staticmethod
    def create_deadline_approaching_alert(song):
        """
        Alert when song deadline is approaching (2 days before).

        Should be called by daily cron job.

        Args:
            song: Song instance

        Returns:
            List of SongAlert instances created
        """
        # Placeholder implementation:

        # from catalog.models import SongAlert
        # from datetime import timedelta
        # from api.models import User
        #
        # alerts = []
        #
        # if not song.stage_deadline:
        #     return alerts
        #
        # days_until_deadline = (song.stage_deadline - timezone.now().date()).days
        #
        # if days_until_deadline != 2:
        #     return alerts  # Only alert 2 days before
        #
        # # Alert assigned user
        # if song.assigned_user:
        #     alert = SongAlert.objects.create(
        #         song=song,
        #         alert_type='deadline_approaching',
        #         target_user=song.assigned_user,
        #         title=f'Deadline Approaching: {song.title}',
        #         message=f'"{song.title}" is due in 2 days ({song.stage_deadline}). Please complete checklist items.',
        #         action_url=f'/songs/{song.id}/',
        #         action_label='View Song',
        #         priority='important'
        #     )
        #     alerts.append(alert)
        #
        # # Also alert department managers
        # if song.assigned_department:
        #     dept_managers = User.objects.filter(
        #         profile__department=song.assigned_department,
        #         profile__role__level__gte=300  # Manager level
        #     )
        #
        #     for manager in dept_managers:
        #         alert = SongAlert.objects.create(
        #             song=song,
        #             alert_type='deadline_approaching',
        #             target_user=manager,
        #             title=f'Team Song Deadline: {song.title}',
        #             message=f'"{song.title}" assigned to {song.assigned_user.get_full_name() if song.assigned_user else "unassigned"} is due in 2 days.',
        #             action_url=f'/songs/{song.id}/',
        #             action_label='View Song',
        #             priority='important'
        #         )
        #         alerts.append(alert)
        #
        # return alerts

        return []

    @staticmethod
    def create_checklist_incomplete_alert(song, item):
        """
        Alert when a required checklist item is incomplete for 3+ days.

        Args:
            song: Song instance
            item: SongChecklistItem instance

        Returns:
            SongAlert instance
        """
        # Placeholder implementation:

        # from catalog.models import SongAlert
        #
        # if not item.assigned_to:
        #     return None
        #
        # alert = SongAlert.objects.create(
        #     song=song,
        #     alert_type='checklist_incomplete',
        #     target_user=item.assigned_to,
        #     title=f'Incomplete Checklist Item: {song.title}',
        #     message=f'The checklist item "{item.item_name}" for "{song.title}" has been incomplete for 3+ days. Please complete it.',
        #     action_url=f'/songs/{song.id}/',
        #     action_label='View Song',
        #     priority='important'
        # )
        #
        # return alert

        return None

    @staticmethod
    def create_blocking_issue_alert(song, user, reason):
        """
        Alert when user manually flags song as blocked.

        Args:
            song: Song instance
            user: User who flagged it
            reason: Blocking reason text

        Returns:
            List of SongAlert instances created
        """
        # Placeholder implementation:

        # from catalog.models import SongAlert
        # from api.models import User
        #
        # alerts = []
        #
        # # Alert department managers
        # if song.assigned_department:
        #     dept_managers = User.objects.filter(
        #         profile__department=song.assigned_department,
        #         profile__role__level__gte=300  # Manager level
        #     )
        #
        #     for manager in dept_managers:
        #         alert = SongAlert.objects.create(
        #             song=song,
        #             alert_type='blocking_issue',
        #             target_user=manager,
        #             title=f'BLOCKED: {song.title}',
        #             message=f'{user.get_full_name()} flagged "{song.title}" as blocked. Reason: {reason}',
        #             action_url=f'/songs/{song.id}/',
        #             action_label='View Song',
        #             priority='urgent'
        #         )
        #         alerts.append(alert)
        #
        # # Alert song creator
        # if song.created_by and song.created_by != user:
        #     alert = SongAlert.objects.create(
        #         song=song,
        #         alert_type='blocking_issue',
        #         target_user=song.created_by,
        #         title=f'Song Blocked: {song.title}',
        #         message=f'Your song "{song.title}" has been flagged as blocked. Reason: {reason}',
        #         action_url=f'/songs/{song.id}/',
        #         action_label='View Song',
        #         priority='urgent'
        #     )
        #     alerts.append(alert)
        #
        # return alerts

        return []

    @staticmethod
    def create_sales_pitch_alert(song, user, pitched_to):
        """
        Alert when Sales adds a pitch note.

        Notifies the song creator that their work has been pitched.

        Args:
            song: Song instance
            user: Sales user who pitched
            pitched_to: Artist/entity name pitched to

        Returns:
            SongAlert instance
        """
        from catalog.models import SongAlert

        if not song.created_by:
            return None

        alert = SongAlert.objects.create(
            song=song,
            alert_type='status_update',
            target_user=song.created_by,
            title=f'Work Pitched: {song.title}',
            message=f'{user.get_full_name()} from Sales pitched "{song.title}" to {pitched_to}.',
            action_url=f'/songs/{song.id}/',
            action_label='View Details',
            priority='info'
        )

        return alert

    @staticmethod
    def create_release_approaching_alert(song):
        """
        Alert when target release date is 7 days away.

        Should be called by daily cron job.

        Args:
            song: Song instance

        Returns:
            List of SongAlert instances created
        """
        # Placeholder implementation:

        # from catalog.models import SongAlert
        # from api.models import Department, User
        #
        # alerts = []
        #
        # if not song.target_release_date:
        #     return alerts
        #
        # days_until_release = (song.target_release_date - timezone.now().date()).days
        #
        # if days_until_release != 7:
        #     return alerts  # Only alert 7 days before
        #
        # # Alert Digital department
        # try:
        #     digital_dept = Department.objects.get(code='digital')
        #     alert = SongAlert.objects.create(
        #         song=song,
        #         alert_type='release_approaching',
        #         target_department=digital_dept,
        #         title=f'Release in 7 Days: {song.title}',
        #         message=f'"{song.title}" is scheduled for release in 7 days ({song.target_release_date}). Ensure all distribution is complete.',
        #         action_url=f'/songs/{song.id}/',
        #         action_label='View Song',
        #         priority='important'
        #     )
        #     alerts.append(alert)
        # except Department.DoesNotExist:
        #     pass
        #
        # # Alert Label department
        # try:
        #     label_dept = Department.objects.get(code='label')
        #     alert = SongAlert.objects.create(
        #         song=song,
        #         alert_type='release_approaching',
        #         target_department=label_dept,
        #         title=f'Release in 7 Days: {song.title}',
        #         message=f'"{song.title}" is scheduled for release in 7 days ({song.target_release_date}).',
        #         action_url=f'/songs/{song.id}/',
        #         action_label='View Song',
        #         priority='important'
        #     )
        #     alerts.append(alert)
        # except Department.DoesNotExist:
        #     pass
        #
        # return alerts

        return []


# Convenience function for bulk operations
def create_daily_alerts():
    """
    Creates all daily alerts (overdue, approaching deadlines, etc.).

    This should be called by a daily cron job or Celery task.

    Returns:
        Dictionary with summary of alerts created
    """
    # Placeholder implementation:

    # from catalog.models import Song
    # from datetime import timedelta
    #
    # summary = {
    #     'overdue_alerts': 0,
    #     'deadline_approaching_alerts': 0,
    #     'release_approaching_alerts': 0,
    #     'total_alerts': 0
    # }
    #
    # # Find overdue songs
    # overdue_songs = Song.objects.filter(
    #     stage_deadline__lt=timezone.now().date(),
    #     stage__in=['publishing', 'label_recording', 'marketing_assets', 'label_review', 'ready_for_digital', 'digital_distribution']
    # )
    #
    # for song in overdue_songs:
    #     alerts = SongAlertService.create_overdue_alert(song)
    #     summary['overdue_alerts'] += len(alerts)
    #     summary['total_alerts'] += len(alerts)
    #
    # # Find songs with approaching deadlines (2 days)
    # approaching_deadline = timezone.now().date() + timedelta(days=2)
    # approaching_songs = Song.objects.filter(
    #     stage_deadline=approaching_deadline,
    #     stage__in=['publishing', 'label_recording', 'marketing_assets', 'label_review', 'ready_for_digital', 'digital_distribution']
    # )
    #
    # for song in approaching_songs:
    #     alerts = SongAlertService.create_deadline_approaching_alert(song)
    #     summary['deadline_approaching_alerts'] += len(alerts)
    #     summary['total_alerts'] += len(alerts)
    #
    # # Find songs with approaching release dates (7 days)
    # approaching_release = timezone.now().date() + timedelta(days=7)
    # release_songs = Song.objects.filter(
    #     target_release_date=approaching_release
    # )
    #
    # for song in release_songs:
    #     alerts = SongAlertService.create_release_approaching_alert(song)
    #     summary['release_approaching_alerts'] += len(alerts)
    #     summary['total_alerts'] += len(alerts)
    #
    # return summary

    return {
        'overdue_alerts': 0,
        'deadline_approaching_alerts': 0,
        'release_approaching_alerts': 0,
        'total_alerts': 0
    }
