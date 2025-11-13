"""
Catalog signals for Universal Task Automation System.

Handles automation for Work, Recording, Song, and SongChecklistItem changes.
"""

import logging
from django.db import models
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Work, Recording, Song, SongChecklistItem, SongStageStatus, WORKFLOW_STAGES

User = get_user_model()
logger = logging.getLogger(__name__)


# ==================== Work Signals ====================

@receiver(pre_save, sender=Work)
def track_work_field_changes(sender, instance, **kwargs):
    """Track old field values for change detection."""
    if instance.pk:
        try:
            old_work = Work.objects.get(pk=instance.pk)
            instance._old_iswc = old_work.iswc
        except Work.DoesNotExist:
            instance._old_iswc = None
    else:
        instance._old_iswc = None


@receiver(post_save, sender=Work)
def on_work_saved(sender, instance, created, **kwargs):
    """
    Handle Work save events.

    Actions:
    1. Auto-validate and complete checklist items based on Work field changes
    """
    try:
        # Get all songs that use this work
        songs = Song.objects.filter(work=instance)

        for song in songs:
            # Get ALL incomplete checklist items for this song
            checklist_items = SongChecklistItem.objects.filter(
                song=song,
                is_complete=False
            )

            for item in checklist_items:
                # Check if this item validates against work
                validation_rule = item.validation_rule or {}
                entity = validation_rule.get('entity')

                # Only process items that validate against 'work'
                if entity == 'work':
                    # Run validation
                    is_valid = item.validate()
                    logger.debug(
                        f"Work {instance.id}: Checking item '{item.item_name}' "
                        f"(validation_type={item.validation_type}, rule={item.validation_rule}) -> {is_valid}"
                    )

                    if is_valid:
                        item.is_complete = True
                        item.save(update_fields=['is_complete'])
                        logger.info(
                            f"Work {instance.id}: ✓ Auto-completed checklist item '{item.item_name}' "
                            f"for Song {song.id}"
                        )

    except Exception as e:
        logger.error(f"Error in work post_save signal for Work {instance.id}: {e}", exc_info=True)


# ==================== Recording Signals ====================

@receiver(pre_save, sender=Recording)
def track_recording_field_changes(sender, instance, **kwargs):
    """Track old field values for change detection."""
    if instance.pk:
        try:
            old_recording = Recording.objects.get(pk=instance.pk)
            instance._old_status = getattr(old_recording, 'status', None)
        except Recording.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=Recording)
def on_recording_saved(sender, instance, created, **kwargs):
    """
    Handle Recording save events.

    Actions:
    1. Auto-validate and complete checklist items based on Recording field changes
    """
    try:
        # Get the song associated with this recording
        if hasattr(instance, 'song') and instance.song:
            song = instance.song

            # Get ALL incomplete checklist items for this song
            checklist_items = SongChecklistItem.objects.filter(
                song=song,
                is_complete=False
            )

            for item in checklist_items:
                # Check if this item validates against recording
                validation_rule = item.validation_rule or {}
                entity = validation_rule.get('entity')

                # Only process items that validate against 'recording'
                if entity == 'recording':
                    # Run validation
                    is_valid = item.validate()
                    logger.debug(
                        f"Recording {instance.id}: Checking item '{item.item_name}' "
                        f"(validation_type={item.validation_type}, rule={item.validation_rule}) -> {is_valid}"
                    )

                    if is_valid:
                        item.is_complete = True
                        item.save(update_fields=['is_complete'])
                        logger.info(
                            f"Recording {instance.id}: ✓ Auto-completed checklist item '{item.item_name}' "
                            f"for Song {song.id}"
                        )

    except Exception as e:
        logger.error(f"Error in recording post_save signal for Recording {instance.id}: {e}", exc_info=True)


# ==================== Song Signals ====================

@receiver(pre_save, sender=Song)
def track_song_field_changes(sender, instance, **kwargs):
    """Track old field values for change detection."""
    if instance.pk:
        try:
            old_song = Song.objects.get(pk=instance.pk)
            instance._old_stage = old_song.stage
        except Song.DoesNotExist:
            instance._old_stage = None
    else:
        instance._old_stage = None


@receiver(post_save, sender=Song)
def on_song_saved(sender, instance, created, **kwargs):
    """
    Handle Song save events.

    Actions:
    1. When stage changes, update existing tasks to show previous stage
    2. Create digital release task when song moves to digital_distribution stage
    """
    try:
        # Handle stage change
        if hasattr(instance, '_old_stage') and instance._old_stage:
            if instance._old_stage != instance.stage:
                logger.info(
                    f"Song {instance.id}: Stage changed from '{instance._old_stage}' "
                    f"to '{instance.stage}'"
                )

                # Update tasks from previous stages to show they're from old stage
                from crm_extensions.models import Task
                old_tasks = Task.objects.filter(
                    song=instance,
                    source_stage=instance._old_stage,
                    status__in=['todo', 'in_progress', 'blocked']
                )

                for task in old_tasks:
                    # Add prefix to show it's from previous stage
                    if not task.title.startswith(f'[Previous: {instance._old_stage}]'):
                        task.title = f'[Previous: {instance._old_stage}] {task.title}'
                        task.save(update_fields=['title'])

                logger.info(f"Song {instance.id}: Updated {old_tasks.count()} task(s) from previous stage")

                # Create marketing task and notification when entering marketing_assets stage
                if instance.stage == 'marketing_assets':
                    _create_marketing_task_and_notification(instance)

                # Create digital release task when moving to digital_distribution
                if instance.stage == 'digital_distribution':
                    _create_digital_release_task(instance)

    except Exception as e:
        logger.error(f"Error in song post_save signal for Song {instance.id}: {e}")


@receiver(post_save, sender=Song)
def create_song_stage_statuses(sender, instance, created, **kwargs):
    """
    Automatically create SongStageStatus records for new songs.
    Creates 8 stage status records (one per workflow stage).
    First stage (draft) is set to 'in_progress', rest are 'not_started'.
    """
    if created:
        try:
            stage_statuses = []

            for idx, (stage_code, stage_name) in enumerate(WORKFLOW_STAGES):
                # Skip 'archived' stage - it's not part of the main workflow
                if stage_code == 'archived':
                    continue

                # First stage starts as in_progress
                if idx == 0:
                    status = 'in_progress'
                    started_at = instance.created_at
                else:
                    status = 'not_started'
                    started_at = None

                stage_statuses.append(
                    SongStageStatus(
                        song=instance,
                        stage=stage_code,
                        status=status,
                        started_at=started_at,
                    )
                )

            # Bulk create for performance
            if stage_statuses:
                SongStageStatus.objects.bulk_create(stage_statuses)
                logger.info(
                    f"Song {instance.id}: Created {len(stage_statuses)} stage status records"
                )

        except Exception as e:
            logger.error(f"Error creating stage statuses for Song {instance.id}: {e}")


# ==================== SongChecklistItem Signals ====================

@receiver(pre_save, sender=SongChecklistItem)
def track_checklist_item_changes(sender, instance, **kwargs):
    """Track old field values for change detection."""
    if instance.pk:
        try:
            old_item = SongChecklistItem.objects.get(pk=instance.pk)
            instance._old_is_complete = old_item.is_complete
            instance._old_asset_url = old_item.asset_url
        except SongChecklistItem.DoesNotExist:
            instance._old_is_complete = None
            instance._old_asset_url = None
    else:
        instance._old_is_complete = False
        instance._old_asset_url = None


@receiver(post_save, sender=SongChecklistItem)
def on_checklist_item_saved(sender, instance, created, **kwargs):
    """
    Handle SongChecklistItem save events.

    Actions:
    1. Auto-complete when asset_url is added
    2. Sync with related task (bidirectional)
    3. Check if marketing task should complete (when all marketing_assets items done)
    """
    try:
        from django.utils import timezone

        # 1. Auto-complete checklist item when asset_url is added
        if hasattr(instance, '_old_asset_url'):
            # Check if asset_url was just added (changed from empty to filled)
            if not instance._old_asset_url and instance.asset_url:
                if not instance.is_complete:
                    # Auto-complete the item
                    instance.is_complete = True
                    instance.completed_at = timezone.now()
                    # Note: completed_by should be set by the view/API when updating asset_url
                    instance.save(update_fields=['is_complete', 'completed_at'])
                    logger.info(
                        f"ChecklistItem {instance.id} ('{instance.item_name}'): "
                        f"Auto-completed because asset_url was added"
                    )

        # 2. Bidirectional sync: checklist ↔ task
        if hasattr(instance, 'tasks') and instance.tasks.exists():
            # Get related task
            task = instance.tasks.first()

            # If checklist item completed, mark task as done
            if instance.is_complete and task.status != 'done':
                task.status = 'done'
                task.completed_at = timezone.now()
                task.save(update_fields=['status', 'completed_at'])
                logger.info(
                    f"ChecklistItem {instance.id}: Marked related task {task.id} as done"
                )

            # If checklist item uncompleted, revert task status
            elif not instance.is_complete and task.status == 'done':
                task.status = 'todo'
                task.completed_at = None
                task.save(update_fields=['status', 'completed_at'])
                logger.info(
                    f"ChecklistItem {instance.id}: Reverted related task {task.id} to todo"
                )

        # 3. Check if this is a marketing_assets item and handle marketing task completion
        if instance.stage == 'marketing_assets':
            _check_marketing_task_completion(instance.song)

    except Exception as e:
        logger.error(
            f"Error in checklist item post_save signal for "
            f"SongChecklistItem {instance.id}: {e}"
        )


def _check_marketing_task_completion(song):
    """
    Check if all required marketing_assets checklist items are complete.
    If so, mark the marketing task as done.

    Args:
        song: Song instance
    """
    from crm_extensions.models import Task

    try:
        # Get all marketing_assets checklist items for this song
        marketing_items = SongChecklistItem.objects.filter(
            song=song,
            stage='marketing_assets'
        )

        # Separate required and optional items
        required_items = [item for item in marketing_items if item.required]

        # Check if all required items are complete
        if required_items:
            all_required_complete = all(item.is_complete for item in required_items)

            # Find marketing tasks for this song
            marketing_tasks = Task.objects.filter(
                song=song,
                task_type='content_creation',
                title__icontains='marketing'
            )

            for task in marketing_tasks:
                if all_required_complete:
                    # Mark task as done if all required items are complete
                    if task.status != 'done':
                        task.status = 'done'
                        task.save(update_fields=['status'])
                        logger.info(
                            f"Song {song.id}: Marked marketing task {task.id} as done "
                            f"(all required marketing assets complete)"
                        )
                else:
                    # Reopen task if it was done but not all items are complete anymore
                    if task.status == 'done':
                        task.status = 'in_progress'
                        task.save(update_fields=['status'])
                        logger.info(
                            f"Song {song.id}: Reopened marketing task {task.id} "
                            f"(required marketing assets incomplete)"
                        )

    except Exception as e:
        logger.error(f"Error checking marketing task completion for Song {song.id}: {e}")


def _create_marketing_task_and_notification(song):
    """
    Create a task and notification for marketing manager when song enters marketing_assets stage.

    Args:
        song: Song instance
    """
    from crm_extensions.models import Task, TaskAssignment
    from api.models import Department
    from notifications.models import Notification
    from django.contrib.contenttypes.models import ContentType

    try:
        # Check if task already exists
        existing_task = Task.objects.filter(
            song=song,
            task_type='content_creation',
            title__icontains='marketing'
        ).first()

        if existing_task:
            logger.info(f"Song {song.id}: Marketing task already exists (task {existing_task.id})")
            return

        # Get marketing department
        try:
            marketing_dept = Department.objects.get(code='marketing')
        except Department.DoesNotExist:
            logger.warning(f"Song {song.id}: Marketing department not found, cannot create marketing task")
            return

        # Get marketing manager(s)
        marketing_managers = User.objects.filter(
            profile__department=marketing_dept,
            profile__role__code__in=['marketing_manager', 'manager']
        )

        if not marketing_managers.exists():
            logger.warning(f"Song {song.id}: No marketing managers found, creating task without assignment")

        # Create task
        task = Task.objects.create(
            title=f'Create marketing assets for "{song.title}"',
            description=f'Prepare all marketing materials for this song including social media posts, thumbnails, and promotional content.',
            song=song,
            department=marketing_dept,
            task_type='content_creation',
            priority=3,
            status='todo',
            source_stage='marketing_assets'
        )

        logger.info(
            f"Song {song.id}: Created marketing task {task.id} for marketing department"
        )

        # Assign task to marketing managers and send notifications
        song_content_type = ContentType.objects.get_for_model(Song)

        for manager in marketing_managers:
            # Assign task
            TaskAssignment.objects.create(
                task=task,
                user=manager,
                role='assignee'
            )

            # Create notification
            notification = Notification.objects.create(
                user=manager,
                message=f'New song "{song.title}" has entered the marketing stage and needs your attention.',
                notification_type='status_change',
                content_type=song_content_type,
                object_id=song.id,
                action_url=f'/songs/{song.id}',
                metadata={
                    'song_id': song.id,
                    'song_title': song.title,
                    'stage': 'marketing_assets',
                    'task_id': task.id
                }
            )

            logger.info(
                f"Song {song.id}: Assigned task to {manager.email} and sent notification #{notification.id}"
            )

    except Exception as e:
        logger.error(f"Error creating marketing task and notification for Song {song.id}: {e}", exc_info=True)


def _create_digital_release_task(song):
    """
    Create a task for digital manager when song moves to digital_distribution stage.

    Args:
        song: Song instance
    """
    from crm_extensions.models import Task
    from api.models import Department

    try:
        # Check if task already exists
        existing_task = Task.objects.filter(
            song=song,
            task_type='platform_setup',
            title__icontains='Release'
        ).first()

        if existing_task:
            logger.info(f"Song {song.id}: Digital release task already exists (task {existing_task.id})")
            return

        # Get digital department
        try:
            digital_dept = Department.objects.get(name='digital')
        except Department.DoesNotExist:
            logger.warning(f"Song {song.id}: Digital department not found, cannot create release task")
            return

        # Create task
        task = Task.objects.create(
            title=f'Release "{song.title}" to digital platforms',
            description=f'Distribute this song to streaming platforms and digital stores.',
            song=song,
            department=digital_dept,
            task_type='platform_setup',
            priority=3,
            status='todo',
            source_stage='digital_distribution'
        )

        logger.info(
            f"Song {song.id}: Created digital release task {task.id} for digital department"
        )

    except Exception as e:
        logger.error(f"Error creating digital release task for Song {song.id}: {e}")


# ==================== SongStageStatus Signals ====================

@receiver(pre_save, sender=SongStageStatus)
def track_stage_status_changes(sender, instance, **kwargs):
    """Track old status value for change detection."""
    if instance.pk:
        try:
            old_status = SongStageStatus.objects.get(pk=instance.pk)
            instance._old_status = old_status.status
        except SongStageStatus.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=SongStageStatus)
def on_stage_status_changed(sender, instance, created, **kwargs):
    """
    Handle SongStageStatus changes.

    When a stage is started (changed to 'in_progress' for the first time):
    1. Create checklist items for that stage if they don't exist
    2. For marketing_assets stage, create task and notification
    """
    from catalog import checklist_templates

    try:
        # Check if status changed to 'in_progress'
        old_status = getattr(instance, '_old_status', None)
        is_newly_started = (
            instance.status == 'in_progress' and
            old_status != 'in_progress'
        )

        if not is_newly_started:
            return

        song = instance.song
        stage = instance.stage

        logger.info(
            f"Song {song.id}: Stage {stage} started (status changed to in_progress)"
        )

        # 1. Update song's main stage field if different
        if song.stage != stage:
            from django.utils import timezone

            logger.info(
                f"Song {song.id}: Transitioning song from {song.stage} to {stage}"
            )

            # Update song stage
            song.stage = stage
            song.stage_entered_at = timezone.now()

            # Assign to department for new stage
            from catalog.permissions import get_department_for_stage
            target_dept_code = get_department_for_stage(stage)
            if target_dept_code:
                from api.models import Department
                try:
                    target_dept = Department.objects.get(code=target_dept_code)
                    song.assigned_department = target_dept
                    logger.info(
                        f"Song {song.id}: Assigned to {target_dept.name} department"
                    )
                except Department.DoesNotExist:
                    pass

            song.save(update_fields=['stage', 'stage_entered_at', 'assigned_department'])
            logger.info(
                f"Song {song.id}: Song stage updated to {stage}"
            )

        # 2. Create checklist items if they don't exist for this stage
        existing_items = SongChecklistItem.objects.filter(
            song=song,
            stage=stage
        ).count()

        if existing_items == 0:
            logger.info(
                f"Song {song.id}: Creating checklist items for stage {stage}"
            )
            checklist_items_data = checklist_templates.generate_checklist_for_stage(
                song, stage
            )
            for item_data in checklist_items_data:
                SongChecklistItem.objects.create(**item_data)
            logger.info(
                f"Song {song.id}: Created {len(checklist_items_data)} checklist items for {stage}"
            )
        else:
            logger.info(
                f"Song {song.id}: Checklist items already exist for {stage} ({existing_items} items)"
            )

        # 3. For marketing_assets stage, create task and notification
        if stage == 'marketing_assets':
            _create_marketing_task_and_notification(song)

    except Exception as e:
        logger.error(
            f"Error in stage status post_save signal for "
            f"SongStageStatus {instance.id}: {e}"
        )
