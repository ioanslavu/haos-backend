from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Campaign, CampaignHandler
from identity.serializers import EntityListSerializer, ContactPersonSerializer

User = get_user_model()


class CampaignHandlerSerializer(serializers.ModelSerializer):
    """Serializer for CampaignHandler"""
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = CampaignHandler
        fields = ['id', 'user', 'user_email', 'user_name', 'role', 'role_display', 'assigned_at']
        read_only_fields = ['assigned_at']

    def get_user_name(self, obj):
        return obj.user.get_full_name() if obj.user else None


class CampaignListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for campaign listings"""
    client = EntityListSerializer(read_only=True)
    artist = EntityListSerializer(read_only=True)
    brand = EntityListSerializer(read_only=True)
    contact_person = ContactPersonSerializer(read_only=True)
    created_by_name = serializers.SerializerMethodField()
    department_display = serializers.CharField(source='get_department_display', read_only=True)

    class Meta:
        model = Campaign
        fields = [
            'id',
            'campaign_name',
            'client',
            'artist',
            'brand',
            'contact_person',
            'department',
            'department_display',
            'value',
            'status',
            'confirmed_at',
            'created_at',
            'updated_at',
            'created_by_name',
        ]

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None


class CampaignDetailSerializer(serializers.ModelSerializer):
    """Full serializer for campaign details"""
    client = EntityListSerializer(read_only=True)
    artist = EntityListSerializer(read_only=True)
    brand = EntityListSerializer(read_only=True)
    contact_person = ContactPersonSerializer(read_only=True)
    handlers = CampaignHandlerSerializer(many=True, read_only=True)
    created_by_name = serializers.SerializerMethodField()
    department_display = serializers.CharField(source='get_department_display', read_only=True)

    class Meta:
        model = Campaign
        fields = [
            'id',
            'campaign_name',
            'client',
            'artist',
            'brand',
            'contact_person',
            'department',
            'department_display',
            'value',
            'status',
            'confirmed_at',
            'notes',
            'handlers',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at', 'department']

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None


class CampaignCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating campaigns"""
    handlers = CampaignHandlerSerializer(many=True, required=False)

    class Meta:
        model = Campaign
        fields = [
            'id',
            'campaign_name',
            'client',
            'artist',
            'brand',
            'contact_person',
            'value',
            'status',
            'confirmed_at',
            'notes',
            'handlers',
        ]
        read_only_fields = ['id']  # department is auto-set, not included in fields

    def validate_value(self, value):
        """Ensure value is positive"""
        if value < 0:
            raise serializers.ValidationError("Value must be positive")
        return value

    def validate(self, data):
        """
        Cross-field validation
        """
        # If status is confirmed or later, confirmed_at should be set
        status = data.get('status')
        confirmed_at = data.get('confirmed_at')

        if status in ['confirmed', 'active', 'completed'] and not confirmed_at:
            # Auto-set confirmed_at
            from django.utils import timezone
            data['confirmed_at'] = timezone.now()

        # Validate user has department (for create only)
        request = self.context.get('request')
        if request and hasattr(request, 'user') and not self.instance:
            user = request.user
            if not hasattr(user, 'profile') or not user.profile.department:
                raise serializers.ValidationError(
                    "You must be assigned to a department to create campaigns."
                )

        # Validate handlers belong to the same department as campaign
        handlers_data = data.get('handlers', [])
        if handlers_data:
            # Determine campaign department
            campaign_department = None
            if self.instance:
                # Update: use existing campaign's department
                campaign_department = self.instance.department
            elif request and hasattr(request, 'user') and hasattr(request.user, 'profile'):
                # Create: use creator's department
                campaign_department = request.user.profile.department

            if campaign_department:
                invalid_handlers = []
                for handler_data in handlers_data:
                    handler_user = handler_data.get('user')
                    if handler_user:
                        if not hasattr(handler_user, 'profile') or \
                           handler_user.profile.department != campaign_department:
                            invalid_handlers.append(
                                f"{handler_user.get_full_name() or handler_user.email}"
                            )

                if invalid_handlers:
                    raise serializers.ValidationError({
                        'handlers': f"The following users are not from the {campaign_department} department "
                                  f"and cannot be assigned as handlers: {', '.join(invalid_handlers)}"
                    })

        return data

    def create(self, validated_data):
        """Set created_by and department from request user, handle handlers"""
        handlers_data = validated_data.pop('handlers', [])

        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            user = request.user
            validated_data['created_by'] = user

            # Auto-set department from user's profile
            if hasattr(user, 'profile') and user.profile.department:
                validated_data['department'] = user.profile.department

        campaign = super().create(validated_data)

        # Create handlers
        # By default, add the creator as lead if no handlers specified
        if not handlers_data and request and hasattr(request, 'user'):
            CampaignHandler.objects.create(
                campaign=campaign,
                user=request.user,
                role='lead'
            )
        else:
            for handler_data in handlers_data:
                CampaignHandler.objects.create(
                    campaign=campaign,
                    **handler_data
                )

        return campaign

    def update(self, instance, validated_data):
        """Update campaign and handlers"""
        handlers_data = validated_data.pop('handlers', None)

        # Update campaign fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update handlers if provided
        if handlers_data is not None:
            # Clear existing handlers and recreate
            instance.handlers.all().delete()
            for handler_data in handlers_data:
                CampaignHandler.objects.create(
                    campaign=instance,
                    **handler_data
                )

        return instance
