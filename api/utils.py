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

    Django M2M fields can be:
    1. Direct M2M: assigned_to_users = ManyToManyField(User)
       - Filter: assigned_to_users=user
    2. Through model: handlers = ManyToManyField(User, through='CampaignHandler')
       - Through model has FK: CampaignHandler.user
       - Filter: handlers__user=user

    This function detects the pattern and returns the correct lookup string.

    Args:
        model: Django model class
        field_name: Name of M2M field (e.g., 'handlers', 'assigned_to_users')
        through_user_field: FK name in through model (default: 'user', None for direct M2M)

    Returns:
        str: Lookup string for filtering

    Raises:
        ValueError: If field doesn't exist or isn't a M2M field

    Examples:
        # Direct M2M: Task.assigned_to_users
        >>> get_m2m_lookup(Task, 'assigned_to_users', None)
        'assigned_to_users'

        # Through model: Campaign.handlers → CampaignHandler.user
        >>> get_m2m_lookup(Campaign, 'handlers', 'user')
        'handlers__user'
    """
    if not has_model_field(model, field_name):
        raise ValueError(f"Model {model.__name__} has no field '{field_name}'")

    field = model._meta.get_field(field_name)

    if not field.many_to_many:
        raise ValueError(
            f"Field '{field_name}' on {model.__name__} is not a ManyToManyField"
        )

    # Check if through model is auto-created or explicit
    through_model = field.remote_field.through
    is_auto_created = through_model._meta.auto_created

    if is_auto_created or through_user_field is None:
        # Direct M2M: assigned_to_users=user
        return field_name
    else:
        # Custom through model: handlers__user=user
        return f'{field_name}__{through_user_field}'
