"""
Serializers for contract audit trail.
Combines data from django-auditlog, WebhookEvent, and model changes.
"""
from rest_framework import serializers
from auditlog.models import LogEntry
from .models import Contract, ContractSignature, WebhookEvent
from .security_utils import redact_audit_changes, mask_email


class AuditEventSerializer(serializers.Serializer):
    """
    Unified audit event serializer for contract timeline.
    Combines events from multiple sources into a consistent format.
    """
    timestamp = serializers.DateTimeField(
        help_text="When this event occurred"
    )
    event_type = serializers.CharField(
        help_text="Type of event (status_change, signature, webhook, etc.)"
    )
    event_category = serializers.ChoiceField(
        choices=[
            ('contract', 'Contract Change'),
            ('signature', 'Signature Event'),
            ('webhook', 'Webhook Event'),
            ('system', 'System Event'),
        ],
        help_text="Category of event for UI grouping"
    )
    actor = serializers.CharField(
        allow_null=True,
        help_text="Who performed this action (user email or 'System')"
    )
    description = serializers.CharField(
        help_text="Human-readable description of what happened"
    )
    changes = serializers.JSONField(
        allow_null=True,
        help_text="Detailed changes (field-level for auditlog entries)"
    )
    metadata = serializers.JSONField(
        allow_null=True,
        help_text="Additional context (IP, verification status, etc.)"
    )
    source = serializers.CharField(
        help_text="Source of this event (auditlog, webhook, manual)"
    )

    def to_representation(self, instance):
        """
        Apply security redaction to sensitive audit data.

        Redacts sensitive field changes and masks email addresses.
        """
        data = super().to_representation(instance)

        # Redact sensitive data from changes field
        if data.get('changes'):
            data['changes'] = redact_audit_changes(data['changes'])

        # Mask actor email if present
        if data.get('actor') and '@' in str(data.get('actor', '')):
            data['actor'] = mask_email(data['actor'])

        return data


class ContractAuditTrailSerializer(serializers.Serializer):
    """
    Complete audit trail for a contract.
    """
    contract_id = serializers.IntegerField()
    contract_number = serializers.CharField()
    current_status = serializers.CharField()
    events = AuditEventSerializer(many=True)
    summary = serializers.DictField(
        help_text="Summary statistics (total events, signatures, etc.)"
    )
