"""
Permission and visibility logic for Song Workflow system.

This module implements department-based permissions for viewing, editing,
and transitioning songs through workflow stages.
"""

# Stage Constants
WORKFLOW_STAGES = [
    ('draft', 'Draft'),
    ('publishing', 'Publishing'),
    ('label_recording', 'Label - Recording'),
    ('marketing_assets', 'Marketing - Assets'),
    ('label_review', 'Label - Review'),
    ('ready_for_digital', 'Ready for Digital'),
    ('digital_distribution', 'Digital Distribution'),
    ('released', 'Released'),
    ('archived', 'Archived'),
]

# Department codes (matching api.models.Department)
DEPT_PUBLISHING = 'publishing'
DEPT_LABEL = 'label'
DEPT_MARKETING = 'marketing'
DEPT_DIGITAL = 'digital'
DEPT_SALES = 'sales'

# Visibility Matrix: Which departments can VIEW songs at each stage
VISIBILITY_MATRIX = {
    'draft': [DEPT_PUBLISHING, DEPT_LABEL, DEPT_SALES],
    'publishing': [DEPT_PUBLISHING, DEPT_SALES],
    'label_recording': [DEPT_LABEL],
    'marketing_assets': [DEPT_LABEL, DEPT_MARKETING],
    'label_review': [DEPT_LABEL],
    'ready_for_digital': [DEPT_LABEL, DEPT_DIGITAL],
    'digital_distribution': [DEPT_DIGITAL, DEPT_LABEL],
    'released': [DEPT_PUBLISHING, DEPT_LABEL, DEPT_MARKETING, DEPT_DIGITAL, DEPT_SALES],
}

# Edit Matrix: Which departments can EDIT songs at each stage
EDIT_MATRIX = {
    'draft': [DEPT_PUBLISHING],
    'publishing': [DEPT_PUBLISHING],
    'label_recording': [DEPT_LABEL],
    'marketing_assets': [DEPT_MARKETING],
    'label_review': [DEPT_LABEL],
    'ready_for_digital': [DEPT_LABEL],
    'digital_distribution': [DEPT_DIGITAL],
    'released': [],  # No editing in released state
}

# Valid Transitions: Which stages can transition to which other stages
VALID_TRANSITIONS = {
    'draft': ['publishing', 'archived'],
    'publishing': ['label_recording', 'archived'],
    'label_recording': ['marketing_assets', 'archived'],
    'marketing_assets': ['label_review', 'archived'],
    'label_review': ['ready_for_digital', 'marketing_assets', 'archived'],  # Can send back
    'ready_for_digital': ['digital_distribution', 'archived'],
    'digital_distribution': ['released', 'archived'],
    'released': ['archived'],
}


def get_department_for_stage(stage):
    """
    Returns the primary department responsible for a stage.

    Args:
        stage: Workflow stage string

    Returns:
        Department code string or None
    """
    stage_department_map = {
        'draft': DEPT_PUBLISHING,
        'publishing': DEPT_PUBLISHING,
        'label_recording': DEPT_LABEL,
        'marketing_assets': DEPT_MARKETING,
        'label_review': DEPT_LABEL,
        'ready_for_digital': DEPT_LABEL,
        'digital_distribution': DEPT_DIGITAL,
        'released': None,  # No single owner
        'archived': None,
    }
    return stage_department_map.get(stage)


def user_can_view_song(user, song):
    """
    Determines if user can view a song based on:
    1. User's department
    2. User's role level
    3. Song's current stage
    4. Song ownership

    Args:
        user: User object (expects user.profile.role.level and user.profile.department)
        song: Song object (expects song.stage, song.created_by, song.is_archived)

    Returns:
        Boolean indicating if user can view song
    """
    # Check if user has profile
    if not hasattr(user, 'profile'):
        return False

    # Admins see everything
    if user.profile.role.level >= 1000:
        return True

    # Creator always sees their songs
    if song.created_by == user:
        return True

    # Archived songs - only admins and creator
    if song.is_archived:
        return False

    # Department-based visibility
    if not user.profile.department:
        return False

    user_dept = user.profile.department.code.lower()
    stage = song.stage

    allowed_depts = VISIBILITY_MATRIX.get(stage, [])
    return user_dept in allowed_depts


def user_can_view_splits(user, song):
    """
    Determines if user can view split information (writer/publisher/master splits).

    IMPORTANT: Sales can see Publishing stage songs but NOT splits.

    Args:
        user: User object
        song: Song object

    Returns:
        Boolean indicating if user can view splits
    """
    if not hasattr(user, 'profile') or not user.profile.department:
        return False

    # Admins see everything
    if user.profile.role.level >= 1000:
        return True

    user_dept = user.profile.department.code.lower()

    # Sales CANNOT see splits (even though they can see Publishing songs)
    if user_dept == DEPT_SALES:
        return False

    # Marketing CANNOT see splits
    if user_dept == DEPT_MARKETING:
        return False

    # Digital CANNOT see splits (only names)
    if user_dept == DEPT_DIGITAL:
        return False

    # Publishing can see splits for their songs
    if user_dept == DEPT_PUBLISHING and song.stage in ['draft', 'publishing']:
        return True

    # Label can see splits for songs in their stages
    if user_dept == DEPT_LABEL and song.stage in [
        'label_recording', 'marketing_assets', 'label_review',
        'ready_for_digital', 'digital_distribution'
    ]:
        return True

    return False


def user_can_edit_song(user, song):
    """
    Determines if user can edit a song.

    Args:
        user: User object
        song: Song object

    Returns:
        Boolean indicating if user can edit song
    """
    if not user_can_view_song(user, song):
        return False

    if not hasattr(user, 'profile'):
        return False

    # Admins can edit everything
    if user.profile.role.level >= 1000:
        return True

    # Creator can edit in DRAFT stage only
    if song.created_by == user and song.stage == 'draft':
        return True

    # Department-based edit permissions
    if not user.profile.department:
        return False

    user_dept = user.profile.department.code.lower()
    stage = song.stage

    allowed_depts = EDIT_MATRIX.get(stage, [])
    return user_dept in allowed_depts


def user_can_transition_stage(user, song, target_stage):
    """
    Determines if user can transition song to target stage.

    Checks:
    1. User can edit song
    2. Transition is valid
    3. Checklist is complete (unless admin)

    Args:
        user: User object
        song: Song object
        target_stage: Target stage string

    Returns:
        Tuple of (Boolean, error_message)
            - (True, None) if allowed
            - (False, "error message") if not allowed
    """
    if not user_can_edit_song(user, song):
        return False, "You do not have permission to edit this song"

    if not hasattr(user, 'profile'):
        return False, "User profile not found"

    # Check if transition is valid
    current_stage = song.stage
    allowed_next_stages = VALID_TRANSITIONS.get(current_stage, [])

    if target_stage not in allowed_next_stages:
        return False, f"Cannot transition from {current_stage} to {target_stage}"

    # Check if checklist is complete (unless admin or archiving)
    if user.profile.role.level < 1000 and target_stage != 'archived':
        checklist_progress = song.calculate_checklist_progress()
        if checklist_progress < 100:
            return False, f"Checklist must be 100% complete before transitioning (currently {checklist_progress}%)"

    return True, None


def get_visible_stages_for_user(user):
    """
    Returns list of stages that user can view songs in.
    Useful for filtering song lists.

    Args:
        user: User object

    Returns:
        List of stage codes
    """
    if not hasattr(user, 'profile'):
        return []

    # Admins see all stages
    if user.profile.role.level >= 1000:
        return [stage[0] for stage in WORKFLOW_STAGES]

    if not user.profile.department:
        return []

    user_dept = user.profile.department.code.lower()

    # Collect all stages this department can view
    visible_stages = []
    for stage, allowed_depts in VISIBILITY_MATRIX.items():
        if user_dept in allowed_depts:
            visible_stages.append(stage)

    return visible_stages


def get_editable_stages_for_user(user):
    """
    Returns list of stages that user can edit songs in.
    Useful for showing edit buttons.

    Args:
        user: User object

    Returns:
        List of stage codes
    """
    if not hasattr(user, 'profile'):
        return []

    # Admins can edit all stages (except released)
    if user.profile.role.level >= 1000:
        return [stage[0] for stage in WORKFLOW_STAGES if stage[0] != 'released']

    if not user.profile.department:
        return []

    user_dept = user.profile.department.code.lower()

    # Collect all stages this department can edit
    editable_stages = []
    for stage, allowed_depts in EDIT_MATRIX.items():
        if user_dept in allowed_depts:
            editable_stages.append(stage)

    return editable_stages
