"""
Catalog signals for Universal Task Automation System.

Handles automation for Work, Recording, Song, and SongChecklistItem changes.
"""

import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Work, Recording, Song, SongChecklistItem, SongStageStatus, WORKFLOW_STAGES

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

    Currently no automatic actions on Work save.
    Placeholder for future work-related automation.
    """
    pass


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

    Currently no automatic actions on Recording save.
    Placeholder for future recording-related automation.
    """
    pass


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
        except SongChecklistItem.DoesNotExist:
            instance._old_is_complete = None
    else:
        instance._old_is_complete = False


@receiver(post_save, sender=SongChecklistItem)
def on_checklist_item_saved(sender, instance, created, **kwargs):
    """
    Handle SongChecklistItem save events.

    Actions:
    1. Sync with related task (bidirectional)
    2. Check if marketing task should complete (when all marketing_assets items done)
    """
    try:
        # 1. Bidirectional sync: checklist ↔ task
        if hasattr(instance, 'tasks') and instance.tasks.exists():
            # Get related task
            task = instance.tasks.first()

            # If checklist item completed, mark task as done
            if instance.is_complete and task.status != 'done':
                from django.utils import timezone
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

        # 2. Check if this is a marketing_assets item and handle marketing task completion
        if instance.checklist_name == 'marketing_assets':
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
            checklist_name='marketing_assets'
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
