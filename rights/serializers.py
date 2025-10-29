from rest_framework import serializers
from decimal import Decimal
from .models import Credit, Split, SplitValidation
from identity.serializers import EntityListSerializer


class CreditSerializer(serializers.ModelSerializer):
    """Serializer for Credit model."""

    entity_name = serializers.CharField(source='entity.display_name', read_only=True)
    entity_details = EntityListSerializer(source='entity', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    share_kind_display = serializers.CharField(source='get_share_kind_display', read_only=True)
    scope_display = serializers.CharField(source='get_scope_display', read_only=True)
    object_title = serializers.SerializerMethodField()

    class Meta:
        model = Credit
        fields = [
            'id', 'scope', 'scope_display', 'object_id', 'object_title',
            'entity', 'entity_name', 'entity_details', 'role', 'role_display',
            'credited_as', 'share_kind', 'share_kind_display', 'share_value',
            'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_object_title(self, obj):
        """Get the title of the credited object."""
        if obj.scope == 'work':
            work = obj.get_work
            return work.title if work else f"Work #{obj.object_id}"
        elif obj.scope == 'recording':
            recording = obj.get_recording
            return recording.title if recording else f"Recording #{obj.object_id}"
        return f"{obj.scope} #{obj.object_id}"

    def validate(self, data):
        """Validate credit data."""
        # Ensure entity is set
        if 'entity' not in data or not data['entity']:
            raise serializers.ValidationError("Entity is required for credits.")

        # Validate share value if provided
        if 'share_value' in data and data['share_value'] is not None:
            if data['share_value'] < 0 or data['share_value'] > 100:
                raise serializers.ValidationError("Share value must be between 0 and 100.")

        return data


class SplitSerializer(serializers.ModelSerializer):
    """Serializer for Split model."""

    entity_name = serializers.CharField(source='entity.display_name', read_only=True)
    entity_details = EntityListSerializer(source='entity', read_only=True)
    right_type_display = serializers.CharField(source='get_right_type_display', read_only=True)
    scope_display = serializers.CharField(source='get_scope_display', read_only=True)
    object_title = serializers.SerializerMethodField()

    class Meta:
        model = Split
        fields = [
            'id', 'scope', 'scope_display', 'object_id', 'object_title',
            'entity', 'entity_name', 'entity_details', 'right_type',
            'right_type_display', 'share', 'source', 'is_locked', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_object_title(self, obj):
        """Get the title of the split object."""
        if obj.scope == 'work':
            work = obj.get_work
            return work.title if work else f"Work #{obj.object_id}"
        elif obj.scope == 'recording':
            recording = obj.get_recording
            return recording.title if recording else f"Recording #{obj.object_id}"
        return f"{obj.scope} #{obj.object_id}"

    def validate_share(self, value):
        """Validate share percentage."""
        if value < Decimal('0') or value > Decimal('100'):
            raise serializers.ValidationError("Share must be between 0 and 100.")
        return value

    def validate(self, data):
        """Validate split data."""
        # Ensure entity is set
        if 'entity' not in data or not data['entity']:
            raise serializers.ValidationError("Entity is required for splits.")

        # Check if updating locked split
        if self.instance and self.instance.is_locked and 'share' in data:
            if data['share'] != self.instance.share:
                raise serializers.ValidationError(
                    "Cannot modify share of a locked split. Unlock it first."
                )

        return data


class SplitValidationSerializer(serializers.Serializer):
    """Serializer for split validation results."""

    scope = serializers.CharField()
    object_id = serializers.IntegerField()
    object_title = serializers.CharField()
    right_type = serializers.CharField()
    right_type_display = serializers.CharField()
    total = serializers.DecimalField(max_digits=5, decimal_places=2)
    is_complete = serializers.BooleanField()
    missing = serializers.DecimalField(max_digits=5, decimal_places=2)
    splits = serializers.ListField(
        child=serializers.DictField()
    )


class SplitBulkCreateSerializer(serializers.Serializer):
    """Serializer for bulk creating splits."""

    scope = serializers.ChoiceField(choices=Split.SCOPE_CHOICES)
    object_id = serializers.IntegerField()
    right_type = serializers.ChoiceField(choices=Split.RIGHT_TYPE_CHOICES)
    splits = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
        help_text="List of splits with entity_id, share, and optional source"
    )

    def validate_splits(self, value):
        """Validate the splits list."""
        total = Decimal('0')
        for split_data in value:
            if 'entity_id' not in split_data:
                raise serializers.ValidationError("Each split must have an entity_id.")
            if 'share' not in split_data:
                raise serializers.ValidationError("Each split must have a share value.")

            share = Decimal(str(split_data['share']))
            if share < 0 or share > 100:
                raise serializers.ValidationError("Share values must be between 0 and 100.")
            total += share

        # Allow some tolerance for rounding
        if abs(total - Decimal('100')) > Decimal('0.01'):
            raise serializers.ValidationError(
                f"Total shares must equal 100%. Current total: {total}%"
            )

        return value


class AutoCalculateSplitsSerializer(serializers.Serializer):
    """Serializer for auto-calculating splits from credits."""

    scope = serializers.ChoiceField(choices=Split.SCOPE_CHOICES)
    object_id = serializers.IntegerField()

    def validate(self, data):
        """Validate that the object exists and has credits."""
        scope = data['scope']
        object_id = data['object_id']

        if scope == 'work':
            from catalog.models import Work
            if not Work.objects.filter(id=object_id).exists():
                raise serializers.ValidationError(f"Work #{object_id} does not exist.")

            # Check if work has credits
            credits = Credit.objects.filter(scope='work', object_id=object_id)
            if not credits.exists():
                raise serializers.ValidationError(
                    f"Work #{object_id} has no credits to calculate splits from."
                )

        elif scope == 'recording':
            from catalog.models import Recording
            if not Recording.objects.filter(id=object_id).exists():
                raise serializers.ValidationError(f"Recording #{object_id} does not exist.")

            # Check if recording has credits
            credits = Credit.objects.filter(scope='recording', object_id=object_id)
            if not credits.exists():
                raise serializers.ValidationError(
                    f"Recording #{object_id} has no credits to calculate splits from."
                )

        return data


class CreditBulkCreateSerializer(serializers.Serializer):
    """Serializer for bulk creating credits."""

    scope = serializers.ChoiceField(choices=Credit.SCOPE_CHOICES)
    object_id = serializers.IntegerField()
    credits = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
        help_text="List of credits with entity_id, role, and optional share_kind, share_value, credited_as"
    )

    def validate_credits(self, value):
        """Validate the credits list."""
        for credit_data in value:
            if 'entity_id' not in credit_data:
                raise serializers.ValidationError("Each credit must have an entity_id.")
            if 'role' not in credit_data:
                raise serializers.ValidationError("Each credit must have a role.")

            # Validate role
            role = credit_data['role']
            valid_roles = dict(Credit.ROLE_CHOICES).keys()
            if role not in valid_roles:
                raise serializers.ValidationError(
                    f"Invalid role: {role}. Valid roles: {', '.join(valid_roles)}"
                )

            # Validate share_value if provided
            if 'share_value' in credit_data:
                share_value = credit_data['share_value']
                if share_value is not None:
                    if share_value < 0 or share_value > 100:
                        raise serializers.ValidationError(
                            "Share values must be between 0 and 100."
                        )

        return value


class RightsValidationReportSerializer(serializers.Serializer):
    """Serializer for comprehensive rights validation report."""

    work_validation = serializers.DictField(required=False)
    recording_validation = serializers.DictField(required=False)
    errors = serializers.ListField(child=serializers.CharField())
    warnings = serializers.ListField(child=serializers.CharField())
    is_valid = serializers.BooleanField()