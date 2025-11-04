"""
Utility functions for field introspection and M2M relationship handling.

These utilities use Django's _meta API for reliable field checking,
avoiding the pitfalls of hasattr() with descriptors and reverse relations.
"""
from django.core.exceptions import FieldDoesNotExist


def has_model_field(model, field_name):
    """
    Check if model has field using _meta (works for FK, M2M, reverse relations).

    This is more reliable than hasattr() because:
    - hasattr() returns True for descriptors that aren't actual fields
    - hasattr() doesn't work consistently with reverse relations
    - _meta.get_field() is the official Django API for field introspection

    Args:
        model: Django model class
        field_name: Name of field to check

    Returns:
        bool: True if field exists on model, False otherwise

    Example:
        >>> has_model_field(Campaign, 'handlers')
        True
        >>> has_model_field(Campaign, 'nonexistent_field')
        False
    """
    try:
        model._meta.get_field(field_name)
        return True
    except FieldDoesNotExist:
        return False


def get_m2m_lookup(model, field_name, through_user_field='user'):
    """
    Get correct M2M filter lookup, handling both direct M2M and through models.

    Standard assignment pattern (used by Campaign and Task):
    - related_name='assignments' on through model's parent FK
    - field_name='user' on through model's user FK
    - Result: 'assignments__user' lookup

    Django M2M fields can be:
    1. Direct M2M: assigned_to = ManyToManyField(User)
       - Filter: assigned_to=user
    2. Through model: assignments = ManyToManyField(User, through='TaskAssignment')
       - Through model has FK: TaskAssignment.user
       - Filter: assignments__user=user
    3. Reverse FK: assignments (related_name from TaskAssignment.task)
       - Through model: TaskAssignment with FKs to Task and User
       - Filter: assignments__user=user

    This function detects the pattern and returns the correct lookup string.

    Args:
        model: Django model class
        field_name: Name of M2M field or reverse FK (e.g., 'assignments', 'assigned_to')
        through_user_field: FK name in through model (default: 'user', None for direct M2M)

    Returns:
        str: Lookup string for filtering

    Raises:
        ValueError: If field doesn't exist or isn't a M2M/reverse FK field

    Examples:
        # Standard pattern: Task.assignments → TaskAssignment.user
        >>> get_m2m_lookup(Task, 'assignments', 'user')
        'assignments__user'

        # Standard pattern: Campaign.assignments → CampaignAssignment.user
        >>> get_m2m_lookup(Campaign, 'assignments', 'user')
        'assignments__user'

        # Direct FK (deprecated): Task.assigned_to
        >>> get_m2m_lookup(Task, 'assigned_to', None)
        'assigned_to'
    """
    if not has_model_field(model, field_name):
        raise ValueError(f"Model {model.__name__} has no field '{field_name}'")

    field = model._meta.get_field(field_name)

    # Handle ManyToMany fields
    if field.many_to_many:
        # Check if through model is auto-created or explicit
        through_model = field.remote_field.through
        is_auto_created = through_model._meta.auto_created

        if is_auto_created or through_user_field is None:
            # Direct M2M: assigned_to_users=user
            return field_name
        else:
            # Custom through model: handlers__user=user
            return f'{field_name}__{through_user_field}'

    # Handle reverse ForeignKey relations (one-to-many)
    elif field.one_to_many:
        # Reverse FK: handlers (related_name from CampaignHandler)
        # Always use through_user_field for reverse FK
        if through_user_field:
            return f'{field_name}__{through_user_field}'
        else:
            # If no through_user_field, just use the field name
            # This would match against the FK directly
            return field_name

    else:
        raise ValueError(
            f"Field '{field_name}' on {model.__name__} is neither a ManyToManyField nor a reverse ForeignKey"
        )
