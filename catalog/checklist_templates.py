"""
Checklist templates for Song Workflow system.

Hardcoded templates that define checklist items for each workflow stage.
These can be easily edited in this file per stakeholder decision.
"""

# Publishing Stage Checklist
PUBLISHING_CHECKLIST_TEMPLATE = [
    {
        'category': 'Work Setup',
        'item_name': 'Work entity created',
        'description': 'Create a Work and link it to this song',
        'required': True,
        'validation_type': 'auto_entity_exists',
        'validation_rule': {'entity': 'work'},
        'help_text': 'Go to Works section and click "Create Work"',
        'order': 1,
    },
    {
        'category': 'Work Setup',
        'item_name': 'ISWC assigned',
        'description': 'Work must have an ISWC code',
        'required': True,
        'validation_type': 'auto_field_exists',
        'validation_rule': {'entity': 'work', 'field': 'iswc'},
        'help_text': 'ISWC can be assigned automatically or requested from registry',
        'order': 2,
    },
    {
        'category': 'Writer Splits',
        'item_name': 'At least 1 writer added',
        'description': 'Work must have at least one writer',
        'required': True,
        'validation_type': 'auto_count_minimum',
        'validation_rule': {'entity': 'work_writers', 'min_count': 1},
        'order': 3,
    },
    {
        'category': 'Writer Splits',
        'item_name': 'Writer splits = 100%',
        'description': 'All writer splits must total exactly 100%',
        'required': True,
        'validation_type': 'auto_split_validated',
        'validation_rule': {'entity': 'work', 'split_type': 'writer'},
        'order': 4,
    },
    {
        'category': 'Publisher Splits',
        'item_name': 'Publisher splits = 100% (if publishers exist)',
        'description': 'If publishers are added, splits must total 100%',
        'required': False,
        'validation_type': 'auto_split_validated',
        'validation_rule': {'entity': 'work', 'split_type': 'publisher', 'skip_if_empty': True},
        'order': 5,
    },
    {
        'category': 'Legal',
        'item_name': 'Publishing agreements uploaded',
        'description': 'Upload signed agreements with writers and publishers',
        'required': True,
        'validation_type': 'manual',
        'help_text': 'Upload PDF contracts in the Contracts section',
        'order': 6,
    },
]

# Label Recording Stage Checklist
# Song-level checklist for label_recording stage (simplified)
LABEL_RECORDING_CHECKLIST_TEMPLATE = [
    {
        'category': 'Recording Setup',
        'item_name': 'Recording entity created',
        'description': 'Create at least one Recording and link it to this song',
        'required': True,
        'validation_type': 'auto_entity_exists',
        'validation_rule': {'entity': 'recording'},
        'order': 1,
    },
]

# Per-recording checklist template (created for each recording)
RECORDING_CHECKLIST_TEMPLATE = [
    {
        'category': 'Recording Setup',
        'item_name': 'ISRC assigned',
        'description': 'Recording must have an ISRC code',
        'required': True,
        'validation_type': 'auto_field_exists',
        'validation_rule': {'entity': 'recording', 'field': 'isrc'},
        'order': 1,
    },
    {
        'category': 'Audio Files',
        'item_name': 'Master audio uploaded',
        'description': 'Upload the final master audio file',
        'required': True,
        'validation_type': 'auto_file_exists',
        'validation_rule': {'entity': 'recording', 'file_field': 'audio_master'},
        'help_text': 'Must be WAV or FLAC, minimum 16-bit/44.1kHz',
        'order': 2,
    },
    {
        'category': 'Audio Files',
        'item_name': 'Instrumental uploaded',
        'description': 'Upload instrumental version (if applicable)',
        'required': False,
        'validation_type': 'auto_file_exists',
        'validation_rule': {'entity': 'recording', 'file_field': 'audio_instrumental'},
        'order': 3,
    },
    {
        'category': 'Credits',
        'item_name': 'At least 1 credit added',
        'description': 'Add producer, featured artist, or other credits',
        'required': True,
        'validation_type': 'auto_count_minimum',
        'validation_rule': {'entity': 'recording_credits', 'min_count': 1},
        'order': 4,
    },
    {
        'category': 'Master Rights',
        'item_name': 'Master splits = 100%',
        'description': 'Master ownership splits must total exactly 100%',
        'required': True,
        'validation_type': 'auto_split_validated',
        'validation_rule': {'entity': 'recording', 'split_type': 'master'},
        'order': 5,
    },
    {
        'category': 'Legal',
        'item_name': 'Production contracts uploaded',
        'description': 'Upload signed contracts with producers and featured artists',
        'required': True,
        'validation_type': 'manual',
        'order': 6,
    },
    {
        'category': 'Legal',
        'item_name': 'Master rights cleared',
        'description': 'Confirm all master rights are cleared and owned',
        'required': True,
        'validation_type': 'manual',
        'help_text': 'Check for any samples or interpolations that need clearance',
        'order': 7,
    },
]

# Marketing Assets Stage Checklist
MARKETING_ASSETS_CHECKLIST_TEMPLATE = [
    {
        'category': 'Visual Assets',
        'item_name': 'Cover artwork uploaded',
        'description': 'Upload primary cover artwork (minimum 3000x3000px)',
        'required': True,
        'validation_type': 'auto_custom',
        'validation_rule': {
            'function': 'validate_cover_artwork',
            'min_width': 3000,
            'min_height': 3000,
            'allowed_formats': ['jpg', 'png']
        },
        'help_text': 'Must be JPG or PNG, RGB color mode, no watermarks',
        'order': 1,
    },
    {
        'category': 'Visual Assets',
        'item_name': 'Press photo uploaded',
        'description': 'Upload high-res press photo of artist',
        'required': True,
        'validation_type': 'auto_file_exists',
        'validation_rule': {'entity': 'song_assets', 'asset_type': 'press_photo'},
        'order': 2,
    },
    {
        'category': 'Promotional Materials',
        'item_name': 'Social media assets created',
        'description': 'Create Instagram, Facebook, Twitter graphics',
        'required': True,
        'validation_type': 'manual',
        'order': 3,
    },
    {
        'category': 'Copy',
        'item_name': 'Marketing copy written',
        'description': 'Write press release and promotional copy',
        'required': True,
        'validation_type': 'manual',
        'order': 4,
    },
    {
        'category': 'Optional',
        'item_name': 'Lyric video created',
        'description': 'Create lyric video (if applicable)',
        'required': False,
        'validation_type': 'manual',
        'order': 5,
    },
]

# Label Review Stage Checklist
LABEL_REVIEW_CHECKLIST_TEMPLATE = [
    {
        'category': 'Asset Review',
        'item_name': 'Cover artwork approved',
        'description': 'Review and approve cover artwork quality and design',
        'required': True,
        'validation_type': 'manual',
        'order': 1,
    },
    {
        'category': 'Asset Review',
        'item_name': 'Press photo approved',
        'description': 'Review and approve press photo',
        'required': True,
        'validation_type': 'manual',
        'order': 2,
    },
    {
        'category': 'Asset Review',
        'item_name': 'Promotional materials approved',
        'description': 'Review social media graphics and other promo materials',
        'required': True,
        'validation_type': 'manual',
        'order': 3,
    },
    {
        'category': 'Technical Check',
        'item_name': 'All assets meet technical specs',
        'description': 'Verify dimensions, formats, color modes',
        'required': True,
        'validation_type': 'manual',
        'order': 4,
    },
]

# Ready for Digital Stage Checklist
READY_FOR_DIGITAL_CHECKLIST_TEMPLATE = [
    {
        'category': 'Release Strategy',
        'item_name': 'Release strategy defined',
        'description': 'Single, EP, or Album? Pre-save campaign?',
        'required': True,
        'validation_type': 'manual',
        'order': 1,
    },
    {
        'category': 'Release Strategy',
        'item_name': 'Target release date set',
        'description': 'Set official release date',
        'required': True,
        'validation_type': 'auto_field_exists',
        'validation_rule': {'entity': 'song', 'field': 'target_release_date'},
        'order': 2,
    },
    {
        'category': 'Release Strategy',
        'item_name': 'Distribution platforms selected',
        'description': 'Choose which platforms to distribute to',
        'required': True,
        'validation_type': 'manual',
        'order': 3,
    },
]

# Digital Distribution Stage Checklist
DIGITAL_DISTRIBUTION_CHECKLIST_TEMPLATE = [
    {
        'category': 'Release Setup',
        'item_name': 'Release entity created',
        'description': 'Create Release in system',
        'required': True,
        'validation_type': 'auto_entity_exists',
        'validation_rule': {'entity': 'release'},
        'order': 1,
    },
    {
        'category': 'Release Setup',
        'item_name': 'UPC/EAN assigned',
        'description': 'Assign barcode to release',
        'required': True,
        'validation_type': 'auto_field_exists',
        'validation_rule': {'entity': 'release', 'field': 'upc'},
        'order': 2,
    },
    {
        'category': 'Metadata',
        'item_name': 'Release metadata complete',
        'description': 'Genre, language, copyright, etc.',
        'required': True,
        'validation_type': 'auto_custom',
        'validation_rule': {'function': 'validate_release_metadata'},
        'order': 3,
    },
    {
        'category': 'Distribution',
        'item_name': 'Submitted to distributors',
        'description': 'Submit release package to distribution partners',
        'required': True,
        'validation_type': 'manual',
        'order': 4,
    },
    {
        'category': 'Distribution',
        'item_name': 'Publications created for each platform',
        'description': 'Create Publication entries for Spotify, Apple Music, etc.',
        'required': True,
        'validation_type': 'auto_count_minimum',
        'validation_rule': {'entity': 'release_publications', 'min_count': 1},
        'order': 5,
    },
    {
        'category': 'Pre-release',
        'item_name': 'Pre-save links generated',
        'description': 'Generate pre-save campaign links (if applicable)',
        'required': False,
        'validation_type': 'manual',
        'order': 6,
    },
]

# Template mapping by stage
CHECKLIST_TEMPLATES = {
    'draft': [],  # No checklist for draft
    'publishing': PUBLISHING_CHECKLIST_TEMPLATE,
    'label_recording': LABEL_RECORDING_CHECKLIST_TEMPLATE,
    'marketing_assets': MARKETING_ASSETS_CHECKLIST_TEMPLATE,
    'label_review': LABEL_REVIEW_CHECKLIST_TEMPLATE,
    'ready_for_digital': READY_FOR_DIGITAL_CHECKLIST_TEMPLATE,
    'digital_distribution': DIGITAL_DISTRIBUTION_CHECKLIST_TEMPLATE,
    'released': [],  # No checklist for released
    'archived': [],  # No checklist for archived
}


def generate_checklist_for_stage(song, stage):
    """
    Generates checklist items from template for a given stage.

    This function creates SongChecklistItem instances based on the template
    for the specified stage. Items are not saved to the database here - the
    calling code should save them.

    Args:
        song: Song model instance
        stage: Workflow stage string

    Returns:
        List of dictionaries containing checklist item data ready for creation
    """
    template = CHECKLIST_TEMPLATES.get(stage, [])

    checklist_items = []
    for item_template in template:
        item_data = {
            'song': song,
            'stage': stage,
            'category': item_template['category'],
            'item_name': item_template['item_name'],
            'description': item_template['description'],
            'order': item_template['order'],
            'required': item_template['required'],
            'validation_type': item_template['validation_type'],
            'validation_rule': item_template.get('validation_rule', {}),
            'help_text': item_template.get('help_text', ''),
            'is_complete': False,
        }
        checklist_items.append(item_data)

    return checklist_items


def get_template_for_stage(stage):
    """
    Returns the raw template for a stage (useful for previewing).

    Args:
        stage: Workflow stage string

    Returns:
        List of template dictionaries
    """
    return CHECKLIST_TEMPLATES.get(stage, [])


def get_all_templates():
    """
    Returns all checklist templates.

    Returns:
        Dictionary mapping stages to their templates
    """
    return CHECKLIST_TEMPLATES
