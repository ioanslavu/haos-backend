"""
Security utilities for redacting sensitive data in contract responses.

This module provides functions to detect and redact sensitive information
from API responses to prevent accidental exposure of PII and financial data.
"""

# List of sensitive field patterns that should be redacted
# Based on ACTUAL fields used in identity/models.py get_placeholders()
SENSITIVE_FIELD_PATTERNS = [
    # Romanian Personal Identification (from Entity.get_placeholders)
    'cnp',           # placeholders['cnp'], placeholders['entity.cnp']
    'id_number',     # placeholders['id_number'], placeholders['id.number']
    'id_series',     # placeholders['id_series'], placeholders['id.series']
    'id_primary_number',  # placeholders['entity.id_primary_number']

    # Romanian Company Identification
    'cui',           # placeholders['entity.cui']
    'vat_number',    # placeholders['entity.vat_number'], placeholders['entity.vat']

    # Passport Information (from Entity.get_placeholders)
    'passport_number',   # placeholders['passport_number'], placeholders['entity.passport_number']
    'passport_country',  # placeholders['passport_country'], placeholders['entity.passport_country']

    # Banking (from Entity.get_placeholders)
    'iban',          # placeholders['entity.iban']
    'bank_account',  # placeholders['entity.bank_account']

    # Contact Information (from Entity.get_placeholders)
    'phone',         # placeholders['entity.phone']

    # Physical Address (from Entity.get_placeholders)
    'address',       # placeholders['entity.address']
    'city',          # placeholders['entity.city']
    'zip_code',      # placeholders['entity.zip_code']

    # Birth Information (if added to Entity in future)
    'date_of_birth', 'birth_date', 'place_of_birth', 'birthplace',

    # Authentication and Security (general patterns for safety)
    'password', 'secret', 'api_key', 'token',
]

# Email domains that are considered internal/organizational
# These won't be masked in responses
INTERNAL_EMAIL_DOMAINS = [
    'hahahaproduction.com',
]


def is_sensitive_field(field_name: str) -> bool:
    """
    Check if a field name matches any sensitive data pattern.

    Args:
        field_name: The field name to check

    Returns:
        True if the field contains sensitive data, False otherwise
    """
    if not field_name:
        return False

    field_lower = field_name.lower()
    return any(pattern in field_lower for pattern in SENSITIVE_FIELD_PATTERNS)


def redact_value(value: any, redaction_type: str = 'partial') -> str:
    """
    Redact a sensitive value for display.

    Args:
        value: The value to redact (any type)
        redaction_type: Type of redaction ('full' or 'partial')

    Returns:
        Redacted string representation
    """
    if value is None:
        return '***REDACTED***'

    value_str = str(value)

    if redaction_type == 'full':
        return '***REDACTED***'

    # Partial redaction: show first 2 and last 2 characters if long enough
    if len(value_str) > 4:
        asterisk_count = min(len(value_str) - 4, 8)
        return f"{value_str[:2]}{'*' * asterisk_count}{value_str[-2:]}"
    elif len(value_str) > 0:
        return '*' * len(value_str)
    else:
        return '***REDACTED***'


def mask_email(email: str, force_mask: bool = False) -> str:
    """
    Mask an email address for privacy.

    Internal emails (from INTERNAL_EMAIL_DOMAINS) are not masked unless force_mask=True.

    Args:
        email: Email address to mask
        force_mask: If True, mask even internal emails

    Returns:
        Masked email address
    """
    if not email or '@' not in email:
        return email

    local_part, domain = email.split('@', 1)

    # Don't mask internal emails unless forced
    if not force_mask and domain.lower() in INTERNAL_EMAIL_DOMAINS:
        return email

    # Mask the local part
    if len(local_part) > 2:
        masked_local = f"{local_part[:2]}{'*' * min(len(local_part) - 2, 6)}"
    else:
        masked_local = local_part

    return f"{masked_local}@{domain}"


def redact_placeholder_values(placeholder_values: dict, redaction_type: str = 'partial') -> dict:
    """
    Redact sensitive fields from placeholder values dictionary.

    Args:
        placeholder_values: Dictionary of placeholder key-value pairs
        redaction_type: Type of redaction to apply ('full' or 'partial')

    Returns:
        Dictionary with sensitive values redacted
    """
    if not placeholder_values or not isinstance(placeholder_values, dict):
        return placeholder_values

    redacted = {}

    for key, value in placeholder_values.items():
        if is_sensitive_field(key):
            redacted[key] = redact_value(value, redaction_type)
        else:
            # Check if value is an email and mask it
            if isinstance(value, str) and '@' in value and '.' in value:
                # Simple email detection
                redacted[key] = mask_email(value)
            else:
                redacted[key] = value

    return redacted


def redact_audit_changes(changes: dict) -> dict:
    """
    Redact sensitive data from audit trail changes.

    Audit trails may contain before/after values that need redaction.

    Args:
        changes: Dictionary of field changes (typically {field: {'old': x, 'new': y}})

    Returns:
        Dictionary with sensitive values redacted
    """
    if not changes or not isinstance(changes, dict):
        return changes

    redacted = {}

    for field_name, change_value in changes.items():
        if is_sensitive_field(field_name):
            # If it's a dict with old/new values
            if isinstance(change_value, dict):
                redacted[field_name] = {
                    k: redact_value(v, 'full') for k, v in change_value.items()
                }
            else:
                redacted[field_name] = redact_value(change_value, 'full')
        else:
            redacted[field_name] = change_value

    return redacted


def get_redaction_summary(placeholder_values: dict) -> dict:
    """
    Get a summary of what was redacted.

    Useful for logging and debugging.

    Args:
        placeholder_values: Original placeholder values

    Returns:
        Dictionary with redaction statistics
    """
    if not placeholder_values or not isinstance(placeholder_values, dict):
        return {'total_fields': 0, 'redacted_fields': 0, 'redacted_field_names': []}

    redacted_fields = [key for key in placeholder_values.keys() if is_sensitive_field(key)]

    return {
        'total_fields': len(placeholder_values),
        'redacted_fields': len(redacted_fields),
        'redacted_field_names': redacted_fields,
    }
