"""
Identity signals for checklist auto-validation.

Handles auto-validation when identifiers (ISWC, ISRC, UPC) are created/updated.
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Identifier

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Identifier)
def on_identifier_saved(sender, instance, created, **kwargs):
    """
    Handle Identifier save events.

    When ISWC/ISRC/UPC identifiers are created/updated, trigger checklist validation
    for the related entity.

    Actions:
    1. ISWC (Work) → Validate work-related checklist items
    2. ISRC (Recording) → Validate recording-related checklist items
    3. UPC (Release) → Validate release-related checklist items
    """
    try:
        # Handle ISWC (Work identifier)
        if instance.scheme == 'ISWC' and instance.owner_type == 'work':
            _validate_work_checklists(instance.owner_id)

        # Handle ISRC (Recording identifier)
        elif instance.scheme == 'ISRC' and instance.owner_type == 'recording':
            _validate_recording_checklists(instance.owner_id)

        # Handle UPC/EAN (Release identifier)
        elif instance.scheme in ['UPC', 'EAN'] and instance.owner_type == 'release':
            _validate_release_checklists(instance.owner_id)

    except Exception as e:
        logger.error(
            f"Error in identifier post_save signal for {instance.scheme} "
            f"#{instance.owner_id}: {e}",
            exc_info=True
        )


def _validate_work_checklists(work_id):
    """
    Validate and auto-complete work-related checklist items.

    Args:
        work_id: ID of the Work that was updated
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

                # Only process items that validate against 'work'
                if entity == 'work':
                    # Run validation
                    is_valid = item.validate()
                    logger.debug(
                        f"Identifier ISWC for Work {work_id}: Checking item '{item.item_name}' "
                        f"(type={item.validation_type}, rule={item.validation_rule}) -> {is_valid}"
                    )

                    if is_valid:
                        item.is_complete = True
                        item.save(update_fields=['is_complete'])
                        logger.info(
                            f"Identifier ISWC: ✓ Auto-completed checklist item '{item.item_name}' "
                            f"for Song {song.id} (Work {work_id})"
                        )

    except Work.DoesNotExist:
        logger.warning(f"Work #{work_id} not found for ISWC identifier validation")
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
                    logger.debug(
                        f"Identifier ISRC for Recording {recording_id}: Checking item '{item.item_name}' "
                        f"(type={item.validation_type}, rule={item.validation_rule}) -> {is_valid}"
                    )

                    if is_valid:
                        item.is_complete = True
                        item.save(update_fields=['is_complete'])
                        logger.info(
                            f"Identifier ISRC: ✓ Auto-completed checklist item '{item.item_name}' "
                            f"for Song {song.id} (Recording {recording_id})"
                        )

    except Recording.DoesNotExist:
        logger.warning(f"Recording #{recording_id} not found for ISRC identifier validation")
    except Exception as e:
        logger.error(f"Error validating recording checklists for Recording #{recording_id}: {e}", exc_info=True)


def _validate_release_checklists(release_id):
    """
    Validate and auto-complete release-related checklist items.

    Args:
        release_id: ID of the Release that was updated
    """
    from catalog.models import Song, SongChecklistItem
    from distributions.models import Release

    try:
        release = Release.objects.get(id=release_id)

        # Find songs associated with this release
        # (Implementation depends on your Release-Song relationship)
        songs = Song.objects.filter(releases=release)

        for song in songs:
            # Get ALL incomplete checklist items for this song
            checklist_items = SongChecklistItem.objects.filter(
                song=song,
                is_complete=False
            )

            for item in checklist_items:
                # Check if this item validates against release
                validation_rule = item.validation_rule or {}
                entity = validation_rule.get('entity')

                # Only process items that validate against 'release'
                if entity == 'release':
                    # Run validation
                    is_valid = item.validate()
                    logger.debug(
                        f"Identifier UPC for Release {release_id}: Checking item '{item.item_name}' "
                        f"(type={item.validation_type}, rule={item.validation_rule}) -> {is_valid}"
                    )

                    if is_valid:
                        item.is_complete = True
                        item.save(update_fields=['is_complete'])
                        logger.info(
                            f"Identifier UPC: ✓ Auto-completed checklist item '{item.item_name}' "
                            f"for Song {song.id} (Release {release_id})"
                        )

    except Exception as e:
        logger.error(f"Error validating release checklists for Release #{release_id}: {e}", exc_info=True)
