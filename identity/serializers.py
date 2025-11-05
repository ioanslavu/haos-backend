from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Entity, EntityRole, SensitiveIdentity, Identifier, AuditLogSensitive,
    SocialMediaAccount, ContactPerson, ContactEmail, ContactPhone,
    DepartmentEntity, EntityScore, EntityScoreHistory
)

User = get_user_model()


class NullableDateField(serializers.DateField):
    """
    Custom DateField that converts empty strings to None.
    This handles frontend forms that send '' instead of null for optional date fields.
    """
    def to_internal_value(self, value):
        # Convert empty string to None
        if value == '' or value is None:
            return None
        return super().to_internal_value(value)


class IdentifierSerializer(serializers.ModelSerializer):
    """Serializer for Identifier model."""

    # Override date fields to handle empty strings
    issued_date = NullableDateField(required=False, allow_null=True)
    expiry_date = NullableDateField(required=False, allow_null=True)

    class Meta:
        model = Identifier
        fields = [
            'id', 'scheme', 'value', 'pii_flag', 'owner_type', 'owner_id',
            'issued_by', 'issued_date', 'expiry_date', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class EntityRoleSerializer(serializers.ModelSerializer):
    """Serializer for EntityRole model."""

    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = EntityRole
        fields = ['id', 'role', 'role_display', 'primary_role', 'is_internal', 'created_at']
        read_only_fields = ['created_at']


class SocialMediaAccountSerializer(serializers.ModelSerializer):
    """Serializer for SocialMediaAccount model."""

    platform_display = serializers.CharField(source='get_platform_display', read_only=True)
    platform_icon = serializers.SerializerMethodField()

    class Meta:
        model = SocialMediaAccount
        fields = [
            'id', 'entity', 'platform', 'platform_display', 'platform_icon',
            'handle', 'url', 'display_name', 'follower_count',
            'is_verified', 'is_primary', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_platform_icon(self, obj):
        """Return platform icon emoji"""
        return obj.get_platform_icon()


class ContactEmailSerializer(serializers.ModelSerializer):
    """Serializer for ContactEmail model."""

    class Meta:
        model = ContactEmail
        fields = ['id', 'email', 'label', 'is_primary', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class ContactPhoneSerializer(serializers.ModelSerializer):
    """Serializer for ContactPhone model."""

    class Meta:
        model = ContactPhone
        fields = ['id', 'phone', 'label', 'is_primary', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class ContactPersonSerializer(serializers.ModelSerializer):
    """Serializer for ContactPerson with nested emails and phones."""

    emails = ContactEmailSerializer(many=True, required=False)
    phones = ContactPhoneSerializer(many=True, required=False)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    engagement_stage_display = serializers.CharField(source='get_engagement_stage_display', read_only=True)
    sentiment_display = serializers.CharField(source='get_sentiment_display', read_only=True)

    class Meta:
        model = ContactPerson
        fields = [
            'id', 'entity', 'name', 'role', 'role_display',
            'engagement_stage', 'engagement_stage_display',
            'sentiment', 'sentiment_display', 'notes',
            'emails', 'phones', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def create(self, validated_data):
        emails_data = validated_data.pop('emails', [])
        phones_data = validated_data.pop('phones', [])

        contact_person = ContactPerson.objects.create(**validated_data)

        for email_data in emails_data:
            ContactEmail.objects.create(contact_person=contact_person, **email_data)

        for phone_data in phones_data:
            ContactPhone.objects.create(contact_person=contact_person, **phone_data)

        return contact_person

    def update(self, instance, validated_data):
        emails_data = validated_data.pop('emails', None)
        phones_data = validated_data.pop('phones', None)

        # Update ContactPerson fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update emails if provided
        if emails_data is not None:
            # Clear existing emails and recreate
            instance.emails.all().delete()
            for email_data in emails_data:
                ContactEmail.objects.create(contact_person=instance, **email_data)

        # Update phones if provided
        if phones_data is not None:
            # Clear existing phones and recreate
            instance.phones.all().delete()
            for phone_data in phones_data:
                ContactPhone.objects.create(contact_person=instance, **phone_data)

        return instance


class SensitiveIdentitySerializer(serializers.ModelSerializer):
    """Serializer for SensitiveIdentity - returns masked data by default."""

    cnp = serializers.SerializerMethodField()
    passport_number = serializers.SerializerMethodField()
    entity_name = serializers.CharField(source='entity.display_name', read_only=True)
    identification_type_display = serializers.CharField(source='get_identification_type_display', read_only=True)

    class Meta:
        model = SensitiveIdentity
        fields = [
            'id', 'entity', 'entity_name', 'identification_type', 'identification_type_display',
            'date_of_birth', 'place_of_birth',
            # ID card fields
            'cnp', 'id_series', 'id_number',
            # Passport fields
            'passport_number', 'passport_country',
            # Shared fields
            'id_issued_by', 'id_issued_date', 'id_expiry_date',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_cnp(self, obj):
        """Return masked CNP by default."""
        return obj.get_masked_cnp()

    def get_passport_number(self, obj):
        """Return masked passport number by default."""
        return obj.get_masked_passport_number()


class EntityListSerializer(serializers.ModelSerializer):
    """Light serializer for Entity listing."""

    roles = serializers.SerializerMethodField()
    has_internal_role = serializers.SerializerMethodField()
    kind_display = serializers.CharField(source='get_kind_display', read_only=True)
    profile_photo = serializers.ImageField(read_only=True)

    class Meta:
        model = Entity
        fields = [
            'id', 'kind', 'kind_display', 'display_name', 'alias_name', 'first_name', 'last_name',
            'stage_name', 'nationality', 'gender', 'email', 'phone', 'profile_photo', 'roles',
            'has_internal_role', 'created_at'
        ]
        read_only_fields = ['created_at']

    def get_roles(self, obj):
        """Return list of role names."""
        return [role.get_role_display() for role in obj.entity_roles.all()]

    def get_has_internal_role(self, obj):
        """Check if entity has any internal roles."""
        return obj.entity_roles.filter(is_internal=True).exists()


class EntityDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for Entity with related objects."""

    entity_roles = EntityRoleSerializer(many=True, read_only=True)
    identifiers = IdentifierSerializer(
        many=True,
        read_only=True,
        source='identifier_set'
    )
    sensitive_identity = SensitiveIdentitySerializer(read_only=True)
    social_media_accounts = SocialMediaAccountSerializer(many=True, read_only=True)
    contact_persons = ContactPersonSerializer(many=True, read_only=True)
    kind_display = serializers.CharField(source='get_kind_display', read_only=True)
    created_by = serializers.StringRelatedField(read_only=True)
    has_sensitive_data = serializers.SerializerMethodField()
    placeholders = serializers.SerializerMethodField()
    profile_photo = serializers.ImageField(read_only=True)

    class Meta:
        model = Entity
        fields = [
            'id', 'kind', 'kind_display', 'display_name', 'alias_name', 'first_name', 'last_name',
            'stage_name', 'nationality', 'gender', 'email', 'phone', 'profile_photo',
            'iban', 'bank_name', 'bank_branch',
            'address', 'city', 'state', 'zip_code', 'country',
            'company_registration_number', 'vat_number',
            'notes', 'entity_roles', 'identifiers', 'sensitive_identity', 'social_media_accounts',
            'contact_persons', 'has_sensitive_data', 'placeholders', 'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']

    def get_has_sensitive_data(self, obj):
        """Check if entity has sensitive identity data."""
        if obj.kind == 'PF':
            return hasattr(obj, 'sensitive_identity')
        return False

    def get_placeholders(self, obj):
        """Get contract placeholders for backward compatibility."""
        return obj.get_placeholders()


class RoleDataField(serializers.ListField):
    """
    Custom field that accepts roles in two formats:
    1. Simple list: ["artist", "producer"]
    2. Detailed list: [{"role": "artist", "is_internal": true}, ...]
    """
    def to_internal_value(self, data):
        if not data:
            return []

        result = []
        for item in data:
            if isinstance(item, str):
                # Simple format: just role name
                result.append({'role': item, 'is_internal': False})
            elif isinstance(item, dict):
                # Detailed format: validate required fields
                if 'role' not in item:
                    raise serializers.ValidationError("Each role object must have a 'role' field")
                result.append({
                    'role': item['role'],
                    'is_internal': item.get('is_internal', False)
                })
            else:
                raise serializers.ValidationError("Each role must be a string or an object")

        return result


class EntityCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating Entity."""

    roles = RoleDataField(
        write_only=True,
        required=False,
        help_text="List of roles (strings) or detailed role objects with is_internal flag"
    )
    primary_role = serializers.ChoiceField(
        choices=EntityRole.ROLE_CHOICES,
        write_only=True,
        required=False
    )

    # Sensitive identity fields (write-only)
    identification_type = serializers.ChoiceField(
        choices=SensitiveIdentity.IDENTIFICATION_TYPE_CHOICES,
        write_only=True,
        required=False,
        help_text="Type of identification: ID card or passport"
    )

    # ID card fields
    cnp = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        help_text="CNP for Physical Persons with ID card (will be encrypted)"
    )
    id_series = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        help_text="ID card series (e.g., 'RT')"
    )
    id_number = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        help_text="ID card number"
    )

    # Passport fields
    passport_number = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        help_text="Passport number (will be encrypted)"
    )
    passport_country = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        help_text="Country of passport issuance"
    )

    # Shared fields
    id_issued_by = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        help_text="Issuing authority"
    )
    id_issued_date = NullableDateField(
        write_only=True,
        required=False,
        allow_null=True,
        help_text="Date of issuance"
    )
    id_expiry_date = NullableDateField(
        write_only=True,
        required=False,
        allow_null=True,
        help_text="Expiry date"
    )
    date_of_birth = NullableDateField(
        write_only=True,
        required=False,
        allow_null=True,
        help_text="Date of birth"
    )
    place_of_birth = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        help_text="Place of birth"
    )

    class Meta:
        model = Entity
        fields = [
            'id', 'kind', 'display_name', 'alias_name', 'first_name', 'last_name', 'stage_name',
            'nationality', 'gender', 'email', 'phone', 'profile_photo',
            'iban', 'bank_name', 'bank_branch',
            'address', 'city', 'state', 'zip_code', 'country',
            'company_registration_number', 'vat_number',
            'notes', 'roles', 'primary_role',
            # Sensitive identity fields
            'identification_type', 'cnp', 'id_series', 'id_number',
            'passport_number', 'passport_country',
            'id_issued_by', 'id_issued_date', 'id_expiry_date',
            'date_of_birth', 'place_of_birth'
        ]

    def create(self, validated_data):
        roles_data = validated_data.pop('roles', [])
        primary_role = validated_data.pop('primary_role', None)

        # Extract sensitive identity fields
        identification_type = validated_data.pop('identification_type', 'ID_CARD')
        cnp_data = validated_data.pop('cnp', None)
        id_series_data = validated_data.pop('id_series', None)
        id_number_data = validated_data.pop('id_number', None)
        passport_number_data = validated_data.pop('passport_number', None)
        passport_country_data = validated_data.pop('passport_country', None)
        id_issued_by_data = validated_data.pop('id_issued_by', None)
        id_issued_date_data = validated_data.pop('id_issued_date', None)
        id_expiry_date_data = validated_data.pop('id_expiry_date', None)
        date_of_birth_data = validated_data.pop('date_of_birth', None)
        place_of_birth_data = validated_data.pop('place_of_birth', None)

        # Set created_by from request user
        if 'request' in self.context:
            validated_data['created_by'] = self.context['request'].user

        entity = Entity.objects.create(**validated_data)

        # Create SensitiveIdentity for PF with sensitive data
        has_sensitive_data = (
            cnp_data or id_series_data or id_number_data or
            passport_number_data or passport_country_data or
            id_issued_by_data or id_issued_date_data or id_expiry_date_data or
            date_of_birth_data or place_of_birth_data
        )

        if entity.kind == 'PF' and has_sensitive_data:
            sensitive_identity = SensitiveIdentity.objects.create(
                entity=entity,
                identification_type=identification_type
            )

            # Set ID card fields
            if identification_type == 'ID_CARD':
                if cnp_data and cnp_data.strip():
                    sensitive_identity.cnp = cnp_data.strip()
                if id_series_data and id_series_data.strip():
                    sensitive_identity.id_series = id_series_data.strip()
                if id_number_data and id_number_data.strip():
                    sensitive_identity.id_number = id_number_data.strip()

            # Set passport fields
            elif identification_type == 'PASSPORT':
                if passport_number_data and passport_number_data.strip():
                    sensitive_identity.passport_number = passport_number_data.strip()
                if passport_country_data and passport_country_data.strip():
                    sensitive_identity.passport_country = passport_country_data.strip()

            # Set shared fields
            if id_issued_by_data and id_issued_by_data.strip():
                sensitive_identity.id_issued_by = id_issued_by_data.strip()
            if id_issued_date_data:
                sensitive_identity.id_issued_date = id_issued_date_data
            if id_expiry_date_data:
                sensitive_identity.id_expiry_date = id_expiry_date_data
            if date_of_birth_data:
                sensitive_identity.date_of_birth = date_of_birth_data
            if place_of_birth_data and place_of_birth_data.strip():
                sensitive_identity.place_of_birth = place_of_birth_data.strip()

            sensitive_identity.save()

        # Create entity roles
        for role_data in roles_data:
            EntityRole.objects.create(
                entity=entity,
                role=role_data['role'],
                primary_role=(role_data['role'] == primary_role),
                is_internal=role_data.get('is_internal', False)
            )

        return entity

    def update(self, instance, validated_data):
        roles_data = validated_data.pop('roles', None)
        primary_role = validated_data.pop('primary_role', None)

        # Extract sensitive identity fields
        identification_type = validated_data.pop('identification_type', None)
        cnp_data = validated_data.pop('cnp', None)
        id_series_data = validated_data.pop('id_series', None)
        id_number_data = validated_data.pop('id_number', None)
        passport_number_data = validated_data.pop('passport_number', None)
        passport_country_data = validated_data.pop('passport_country', None)
        id_issued_by_data = validated_data.pop('id_issued_by', None)
        id_issued_date_data = validated_data.pop('id_issued_date', None)
        id_expiry_date_data = validated_data.pop('id_expiry_date', None)
        date_of_birth_data = validated_data.pop('date_of_birth', None)
        place_of_birth_data = validated_data.pop('place_of_birth', None)

        # Update entity fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update sensitive data for PF if provided
        has_sensitive_data = (
            identification_type is not None or
            cnp_data or id_series_data or id_number_data or
            passport_number_data or passport_country_data or
            id_issued_by_data or id_issued_date_data or id_expiry_date_data or
            date_of_birth_data or place_of_birth_data
        )

        if instance.kind == 'PF' and has_sensitive_data:
            sensitive_identity, created = SensitiveIdentity.objects.get_or_create(
                entity=instance
            )

            # Update identification type if provided
            if identification_type:
                sensitive_identity.identification_type = identification_type

            # Update ID card fields
            if sensitive_identity.identification_type == 'ID_CARD':
                if cnp_data is not None:
                    if cnp_data.strip():
                        sensitive_identity.cnp = cnp_data.strip()
                    else:
                        sensitive_identity._cnp_encrypted = None
                if id_series_data is not None:
                    sensitive_identity.id_series = id_series_data.strip() if id_series_data.strip() else None
                if id_number_data is not None:
                    sensitive_identity.id_number = id_number_data.strip() if id_number_data.strip() else None

            # Update passport fields
            elif sensitive_identity.identification_type == 'PASSPORT':
                if passport_number_data is not None:
                    if passport_number_data.strip():
                        sensitive_identity.passport_number = passport_number_data.strip()
                    else:
                        sensitive_identity._passport_number_encrypted = None
                if passport_country_data is not None:
                    sensitive_identity.passport_country = passport_country_data.strip() if passport_country_data.strip() else None

            # Update shared fields
            if id_issued_by_data is not None:
                sensitive_identity.id_issued_by = id_issued_by_data.strip() if id_issued_by_data.strip() else None
            if id_issued_date_data is not None:
                sensitive_identity.id_issued_date = id_issued_date_data
            if id_expiry_date_data is not None:
                sensitive_identity.id_expiry_date = id_expiry_date_data
            if date_of_birth_data is not None:
                sensitive_identity.date_of_birth = date_of_birth_data
            if place_of_birth_data is not None:
                sensitive_identity.place_of_birth = place_of_birth_data.strip() if place_of_birth_data.strip() else None

            sensitive_identity.save()

        # Update roles if provided
        if roles_data is not None:
            # Clear existing roles and recreate
            instance.entity_roles.all().delete()
            for role_data in roles_data:
                EntityRole.objects.create(
                    entity=instance,
                    role=role_data['role'],
                    primary_role=(role_data['role'] == primary_role),
                    is_internal=role_data.get('is_internal', False)
                )

        return instance


class SensitiveIdentityRevealSerializer(serializers.Serializer):
    """Serializer for sensitive identity data reveal request (CNP, passport number, etc.)."""

    reason = serializers.CharField(
        max_length=500,
        help_text="Reason for accessing sensitive identity data"
    )

    def validate_reason(self, value):
        """Ensure reason is not empty."""
        if not value or len(value.strip()) < 10:
            raise serializers.ValidationError(
                "Please provide a detailed reason for accessing this sensitive data."
            )
        return value.strip()


class AuditLogSensitiveSerializer(serializers.ModelSerializer):
    """Serializer for audit log entries."""

    entity_name = serializers.CharField(source='entity.display_name', read_only=True)
    viewer_username = serializers.CharField(source='viewer_user.username', read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    field_display = serializers.CharField(source='get_field_display', read_only=True)

    class Meta:
        model = AuditLogSensitive
        fields = [
            'id', 'entity', 'entity_name', 'field', 'field_display',
            'action', 'action_display', 'viewer_user', 'viewer_username',
            'reason', 'viewed_at', 'ip_address'
        ]
        read_only_fields = fields  # All fields are read-only for audit logs


# Backward compatibility with Client system
class ClientCompatibilitySerializer(serializers.ModelSerializer):
    """Provides backward compatibility with the old Client model."""

    # Map old Client fields to Entity fields
    full_name = serializers.CharField(source='display_name')
    client_name = serializers.CharField(source='display_name', read_only=True)
    name = serializers.CharField(source='display_name', read_only=True)

    # Old placeholder system compatibility
    placeholders = serializers.SerializerMethodField()

    class Meta:
        model = Entity
        fields = [
            'id', 'full_name', 'client_name', 'name', 'email', 'phone',
            'address', 'city', 'state', 'zip_code', 'country',
            'placeholders', 'created_at', 'updated_at'
        ]

    def get_placeholders(self, obj):
        """Get placeholders in old format for backward compatibility."""
        return obj.get_placeholders()


class EntityScoreHistorySerializer(serializers.ModelSerializer):
    """Serializer for EntityScoreHistory."""

    changed_by_name = serializers.SerializerMethodField()
    score_change = serializers.SerializerMethodField()

    class Meta:
        model = EntityScoreHistory
        fields = [
            'id', 'entity_score', 'health_score',
            'collaboration_frequency_score', 'feedback_score', 'payment_latency_score',
            'notes', 'changed_by', 'changed_by_name', 'change_reason',
            'changed_at', 'score_change'
        ]
        read_only_fields = fields  # All fields are read-only for history

    def get_changed_by_name(self, obj):
        """Return full name of the user who made the change."""
        if obj.changed_by:
            return obj.changed_by.get_full_name() or obj.changed_by.email
        return None

    def get_score_change(self, obj):
        """Return the score change from previous entry."""
        return obj.get_score_change()


class EntityScoreSerializer(serializers.ModelSerializer):
    """Serializer for EntityScore with trend and history."""

    entity_name = serializers.CharField(source='entity.display_name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    updated_by_name = serializers.SerializerMethodField()
    score_trend = serializers.SerializerMethodField()
    recent_history = serializers.SerializerMethodField()

    class Meta:
        model = EntityScore
        fields = [
            'id', 'entity', 'entity_name', 'department', 'department_name',
            'health_score', 'collaboration_frequency_score', 'feedback_score', 'payment_latency_score',
            'notes', 'updated_by', 'updated_by_name', 'score_trend', 'recent_history',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'entity_name', 'department_name']

    def get_updated_by_name(self, obj):
        """Return full name of the user who last updated."""
        if obj.updated_by:
            return obj.updated_by.get_full_name() or obj.updated_by.email
        return None

    def get_score_trend(self, obj):
        """Return score trend: 'up', 'down', or 'stable'."""
        return obj.get_score_trend()

    def get_recent_history(self, obj):
        """Return last 5 history entries."""
        history = obj.history.order_by('-changed_at')[:5]
        return EntityScoreHistorySerializer(history, many=True).data


class EntityScoreCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating EntityScore."""

    class Meta:
        model = EntityScore
        fields = [
            'id', 'entity', 'department', 'health_score',
            'collaboration_frequency_score', 'feedback_score', 'payment_latency_score',
            'notes'
        ]
        read_only_fields = ['id']

    def validate(self, data):
        """Validate EntityScore data."""
        # Ensure scores are within range (1-10) - this is also validated by model
        for field in ['health_score', 'collaboration_frequency_score', 'feedback_score', 'payment_latency_score']:
            if field in data and data[field] is not None:
                if not (1 <= data[field] <= 10):
                    raise serializers.ValidationError({
                        field: f"{field} must be between 1 and 10"
                    })

        # For non-admins, ensure they can only create/update scores for their own department
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            user = request.user
            profile = getattr(user, 'profile', None)

            if profile and not profile.is_admin:
                # Non-admins can only work with their own department
                if 'department' in data and data['department'] != profile.department:
                    raise serializers.ValidationError({
                        'department': "You can only manage entity scores for your own department"
                    })

        return data

    def create(self, validated_data):
        """Create EntityScore and set updated_by."""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['updated_by'] = request.user

        return super().create(validated_data)

    def update(self, instance, validated_data):
        """Update EntityScore and set updated_by."""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['updated_by'] = request.user

        return super().update(instance, validated_data)