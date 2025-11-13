"""
Rights signals for checklist auto-validation.

Handles auto-validation when splits (writers, publishers, masters) are created/updated.
"""

import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Split

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Split)
def on_split_saved(sender, instance, created, **kwargs):
    """
    Handle Split save events.

    When writers, publishers, or master splits are created/updated,
    trigger checklist validation for the related entity.
    """
    try:
        # Trigger validation based on scope and right_type
        if instance.scope == 'work' and instance.right_type in ['writer', 'publisher']:
            _validate_work_checklists(instance.object_id, instance.right_type)
        elif instance.scope == 'recording' and instance.right_type == 'master':
            _validate_recording_checklists(instance.object_id)

    except Exception as e:
        logger.error(
            f"Error in split post_save signal for Split #{instance.id}: {e}",
            exc_info=True
        )


@receiver(post_delete, sender=Split)
def on_split_deleted(sender, instance, **kwargs):
    """
    Handle Split delete events.

    When splits are deleted, re-validate checklists (items may become incomplete).
    """
    try:
        # Trigger validation based on scope
        if instance.scope == 'work':
            _validate_work_checklists(instance.object_id, instance.right_type)
        elif instance.scope == 'recording':
            _validate_recording_checklists(instance.object_id)

    except Exception as e:
        logger.error(
            f"Error in split post_delete signal for Split #{instance.id}: {e}",
            exc_info=True
        )


def _validate_work_checklists(work_id, right_type=None):
    """
    Validate and auto-complete work-related checklist items.

    Args:
        work_id: ID of the Work that was updated
        right_type: Optional right_type filter ('writer' or 'publisher')
    """
    from catalog.models import Work, Song, SongChecklistItem

    try:
        work = Work.objects.get(id=work_id)

        # Find all songs that use this work
        songs = Song.objects.filter(work=work)

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

                # Only process items that validate against 'work' or 'work_writers'
                if entity in ['work', 'work_writers']:
                    # Run validation
                    is_valid = item.validate()

                    if is_valid:
                        item.is_complete = True
                        item.save(update_fields=['is_complete'])
                        logger.info(
                            f"Split ({right_type}): ✓ Auto-completed checklist item '{item.item_name}' "
                            f"for Song {song.id} (Work {work_id})"
                        )
                    elif item.is_complete:
                        # If was complete but no longer valid (e.g., split deleted), mark incomplete
                        item.is_complete = False
                        item.save(update_fields=['is_complete'])
                        logger.info(
                            f"Split ({right_type}): ✗ Marked checklist item '{item.item_name}' as incomplete "
                            f"for Song {song.id} (Work {work_id})"
                        )

    except Work.DoesNotExist:
        logger.warning(f"Work #{work_id} not found for split validation")
    except Exception as e:
        logger.error(f"Error validating work checklists for Work #{work_id}: {e}", exc_info=True)


def _validate_recording_checklists(recording_id):
    """
    Validate and auto-complete recording-related checklist items.

    Args:
        recording_id: ID of the Recording that was updated
    """
    from catalog.models import Recording, Song, SongChecklistItem

    try:
        recording = Recording.objects.get(id=recording_id)

        # Get the song associated with this recording
        if hasattr(recording, 'song') and recording.song:
            song = recording.song

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

                    if is_valid:
                        item.is_complete = True
                        item.save(update_fields=['is_complete'])
                        logger.info(
                            f"Split (master): ✓ Auto-completed checklist item '{item.item_name}' "
                            f"for Song {song.id} (Recording {recording_id})"
                        )
                    elif item.is_complete:
                        # If was complete but no longer valid, mark incomplete
                        item.is_complete = False
                        item.save(update_fields=['is_complete'])
                        logger.info(
                            f"Split (master): ✗ Marked checklist item '{item.item_name}' as incomplete "
                            f"for Song {song.id} (Recording {recording_id})"
                        )

    except Recording.DoesNotExist:
        logger.warning(f"Recording #{recording_id} not found for split validation")
    except Exception as e:
        logger.error(f"Error validating recording checklists for Recording #{recording_id}: {e}", exc_info=True)
