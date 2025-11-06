"""
Validation functions for Song Workflow checklist items.

These functions validate checklist items based on their validation_type.
"""

from decimal import Decimal
from identity.models import Identifier
from rights.models import Split, Credit


def validate_auto_field_exists(item):
    """
    Validates that a database field has a value.

    Validation rule format:
    {
        'entity': 'work' | 'recording' | 'release' | 'song',
        'field': 'field_name'
    }

    Args:
        item: SongChecklistItem instance with validation_rule

    Returns:
        Boolean indicating if validation passed
    """
    rule = item.validation_rule
    entity_type = rule.get('entity')
    field_name = rule.get('field')

    if not entity_type or not field_name:
        return False

    song = item.song

    # Get the entity based on type
    entity = None
    if entity_type == 'work':
        entity = song.primary_work
    elif entity_type == 'recording':
        entity = song.primary_recording
    elif entity_type == 'release':
        entity = song.primary_release
    elif entity_type == 'song':
        entity = song

    if not entity:
        return False

    # Special handling for identifier fields (ISWC, ISRC, UPC)
    if field_name in ['iswc', 'isrc', 'upc']:
        try:
            scheme = field_name.upper()
            owner_type = entity_type
            if entity_type == 'song':
                return False  # Songs don't have identifiers directly

            identifier = Identifier.objects.get(
                owner_type=owner_type,
                owner_id=entity.id,
                scheme=scheme
            )
            return bool(identifier.value)
        except Identifier.DoesNotExist:
            return False

    # Check regular field
    value = getattr(entity, field_name, None)
    return value is not None and value != ''


def validate_auto_file_exists(item):
    """
    Validates that a file or URL exists.

    Validation rule format:
    {
        'entity': 'recording' | 'song_assets',
        'file_field': 'field_name',  # For recording
        'asset_type': 'cover_art' | 'press_photo'  # For song_assets
    }

    Args:
        item: SongChecklistItem instance

    Returns:
        Boolean indicating if validation passed
    """
    rule = item.validation_rule
    entity_type = rule.get('entity')
    song = item.song

    if entity_type == 'recording':
        # Check if recording has a specific file field
        recording = song.primary_recording
        if not recording:
            return False

        file_field = rule.get('file_field')
        if not file_field:
            return False

        # Check Asset model for this recording
        from catalog.models import Asset

        # Map file_field to asset kind
        file_field_mapping = {
            'audio_master': ['audio_wav', 'audio_mp3', 'audio_flac', 'audio_aiff'],
            'audio_instrumental': ['audio_wav', 'audio_mp3', 'audio_flac', 'audio_aiff'],
        }

        allowed_kinds = file_field_mapping.get(file_field, [])
        if not allowed_kinds:
            return False

        # Check if asset exists with is_master=True for master, or any for instrumental
        if file_field == 'audio_master':
            return recording.assets.filter(
                kind__in=allowed_kinds,
                is_master=True
            ).exists()
        else:
            return recording.assets.filter(kind__in=allowed_kinds).exists()

    elif entity_type == 'song_assets':
        # Check if song has specific asset type
        # This requires SongAsset model (to be created in Phase 3)
        # For now, return False as model doesn't exist yet
        # TODO: Implement when SongAsset model is created
        return False

    return False


def validate_auto_split_validated(item):
    """
    Validates that splits equal 100%.

    Validation rule format:
    {
        'entity': 'work' | 'recording',
        'split_type': 'writer' | 'publisher' | 'master',
        'skip_if_empty': True | False  # Optional: allow 0% if no splits exist
    }

    Args:
        item: SongChecklistItem instance

    Returns:
        Boolean indicating if validation passed
    """
    rule = item.validation_rule
    entity_type = rule.get('entity')
    split_type = rule.get('split_type')
    skip_if_empty = rule.get('skip_if_empty', False)

    if not entity_type or not split_type:
        return False

    song = item.song

    # Get the entity
    entity = None
    if entity_type == 'work':
        entity = song.primary_work
    elif entity_type == 'recording':
        entity = song.primary_recording

    if not entity:
        return False

    # Get splits for this entity
    splits = Split.objects.filter(
        scope=entity_type,
        object_id=entity.id,
        right_type=split_type
    )

    total = sum(s.share for s in splits)

    # Special case: publishers can be 0% (no publishers)
    if skip_if_empty and total == Decimal('0'):
        return True

    # Check if total is approximately 100%
    return abs(total - Decimal('100')) < Decimal('0.01')


def validate_auto_entity_exists(item):
    """
    Validates that a related entity (Work, Recording, Release) exists.

    Validation rule format:
    {
        'entity': 'work' | 'recording' | 'release'
    }

    Args:
        item: SongChecklistItem instance

    Returns:
        Boolean indicating if validation passed
    """
    rule = item.validation_rule
    entity_type = rule.get('entity')

    if not entity_type:
        return False

    song = item.song

    if entity_type == 'work':
        return song.primary_work is not None
    elif entity_type == 'recording':
        return song.primary_recording is not None
    elif entity_type == 'release':
        return song.primary_release is not None

    return False


def validate_auto_count_minimum(item):
    """
    Validates that a minimum count of related items exists.

    Validation rule format:
    {
        'entity': 'work_writers' | 'recording_credits' | 'release_publications',
        'min_count': 1
    }

    Args:
        item: SongChecklistItem instance

    Returns:
        Boolean indicating if validation passed
    """
    rule = item.validation_rule
    entity_type = rule.get('entity')
    min_count = rule.get('min_count', 1)

    if not entity_type:
        return False

    song = item.song

    count = 0

    if entity_type == 'work_writers':
        # Count writer splits for the work
        if not song.primary_work:
            return False
        count = Split.objects.filter(
            scope='work',
            object_id=song.primary_work.id,
            right_type='writer'
        ).count()

    elif entity_type == 'recording_credits':
        # Count credits for the recording
        if not song.primary_recording:
            return False
        count = Credit.objects.filter(
            scope='recording',
            object_id=song.primary_recording.id
        ).count()

    elif entity_type == 'release_publications':
        # Count publications for the release
        if not song.primary_release:
            return False
        # This requires Publication model - placeholder for now
        # TODO: Implement when Publication model exists
        count = 0

    return count >= min_count


def validate_cover_artwork(song):
    """
    Custom validator for cover artwork.

    Checks:
    - At least one cover_art asset exists
    - Primary artwork is set
    - Dimensions meet minimum requirements (3000x3000)
    - Format is JPG or PNG

    Args:
        song: Song instance

    Returns:
        Boolean indicating if validation passed
    """
    # This requires SongAsset model (to be created in Phase 3)
    # For now, return False as placeholder
    # TODO: Implement when SongAsset model is created

    # Expected implementation:
    # assets = song.assets.filter(asset_type='cover_art')
    # if not assets.exists():
    #     return False
    #
    # primary_artwork = assets.filter(is_primary=True).first()
    # if not primary_artwork:
    #     return False
    #
    # # Check dimensions
    # if primary_artwork.width < 3000 or primary_artwork.height < 3000:
    #     return False
    #
    # # Check format
    # if primary_artwork.file_format.lower() not in ['jpg', 'jpeg', 'png']:
    #     return False
    #
    # return True

    return False


def validate_release_metadata(song):
    """
    Custom validator for release metadata completeness.

    Checks required fields:
    - title
    - genre
    - language
    - copyright_text (or similar)
    - p_line (or similar)

    Args:
        song: Song instance

    Returns:
        Boolean indicating if validation passed
    """
    release = song.primary_release
    if not release:
        return False

    # Check required fields
    required_fields = ['title', 'type', 'release_date']

    for field in required_fields:
        value = getattr(release, field, None)
        if not value:
            return False

    # Additional checks for metadata completeness
    # Note: catalog.models.Release might not have all these fields yet
    # This is a placeholder for when more fields are added

    return True


def run_validation(item):
    """
    Dispatcher function that runs the appropriate validator based on validation_type.

    Args:
        item: SongChecklistItem instance

    Returns:
        Boolean indicating if validation passed
    """
    validation_type = item.validation_type

    # Manual validation is checked by is_complete flag
    if validation_type == 'manual':
        return item.is_complete

    # Automatic validations
    elif validation_type == 'auto_field_exists':
        return validate_auto_field_exists(item)

    elif validation_type == 'auto_file_exists':
        return validate_auto_file_exists(item)

    elif validation_type == 'auto_split_validated':
        return validate_auto_split_validated(item)

    elif validation_type == 'auto_entity_exists':
        return validate_auto_entity_exists(item)

    elif validation_type == 'auto_count_minimum':
        return validate_auto_count_minimum(item)

    elif validation_type == 'auto_custom':
        # Call custom validation function
        rule = item.validation_rule
        function_name = rule.get('function')

        if function_name == 'validate_cover_artwork':
            return validate_cover_artwork(item.song)
        elif function_name == 'validate_release_metadata':
            return validate_release_metadata(item.song)

    # Unknown validation type
    return False


def revalidate_checklist_item(item):
    """
    Re-runs validation for a checklist item and updates its status.

    This is useful for automatic validations when related data changes.

    Args:
        item: SongChecklistItem instance

    Returns:
        Boolean indicating new validation status
    """
    # Skip manual validations
    if item.validation_type == 'manual':
        return item.is_complete

    # Run validation
    is_valid = run_validation(item)

    # Update item if status changed
    if is_valid != item.is_complete:
        item.is_complete = is_valid
        item.save(update_fields=['is_complete'])

    return is_valid


def revalidate_song_checklist(song):
    """
    Re-validates all automatic checklist items for a song's current stage.

    Useful when related entities (Work, Recording, etc.) are updated.

    Args:
        song: Song instance

    Returns:
        Dictionary with validation summary
    """
    # Get checklist items for current stage (requires SongChecklistItem model)
    # This is a placeholder for when model is created
    # TODO: Implement when SongChecklistItem model exists

    # Expected implementation:
    # items = song.checklist_items.filter(
    #     stage=song.stage,
    #     validation_type__startswith='auto'
    # )
    #
    # results = {
    #     'total': items.count(),
    #     'passed': 0,
    #     'failed': 0,
    #     'updated': []
    # }
    #
    # for item in items:
    #     old_status = item.is_complete
    #     new_status = revalidate_checklist_item(item)
    #
    #     if new_status:
    #         results['passed'] += 1
    #     else:
    #         results['failed'] += 1
    #
    #     if old_status != new_status:
    #         results['updated'].append({
    #             'item_id': item.id,
    #             'item_name': item.item_name,
    #             'old_status': old_status,
    #             'new_status': new_status
    #         })
    #
    # return results

    return {
        'total': 0,
        'passed': 0,
        'failed': 0,
        'updated': []
    }
