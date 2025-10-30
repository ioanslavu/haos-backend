from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Campaign, CampaignHandler
from identity.serializers import EntityListSerializer, ContactPersonSerializer
from catalog.serializers import RecordingListSerializer

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
    song = RecordingListSerializer(read_only=True)
    contact_person = ContactPersonSerializer(read_only=True)
    created_by_name = serializers.SerializerMethodField()
    department_display = serializers.SerializerMethodField()
    service_type_display = serializers.CharField(source='get_service_type_display', read_only=True)
    platform_display = serializers.CharField(source='get_platform_display', read_only=True)
    kpi_completion = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = [
            'id',
            'campaign_name',
            'client',
            'artist',
            'brand',
            'song',
            'contact_person',
            'department',
            'department_display',
            'value',
            'currency',
            'status',
            'service_type',
            'service_type_display',
            'platform',
            'platform_display',
            'start_date',
            'end_date',
            'budget_allocated',
            'budget_spent',
            'client_health_score',
            'kpi_completion',
            'confirmed_at',
            'created_at',
            'updated_at',
            'created_by_name',
        ]

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None

    def get_department_display(self, obj):
        """Return department name or 'Admin Only' for null departments"""
        if obj.department:
            return obj.department.name
        return "Admin Only"

    def get_kpi_completion(self, obj):
        """Calculate KPI completion percentage"""
        if not obj.kpi_targets or not obj.kpi_actuals:
            return None

        completed_count = 0
        total_count = 0

        for kpi_name, target_data in obj.kpi_targets.items():
            if kpi_name in obj.kpi_actuals:
                total_count += 1
                actual = obj.kpi_actuals[kpi_name].get('actual', 0)
                target = target_data.get('target', 0)
                if target and actual >= target:
                    completed_count += 1

        if total_count == 0:
            return None

        return round((completed_count / total_count) * 100, 1)


class CampaignDetailSerializer(serializers.ModelSerializer):
    """Full serializer for campaign details"""
    client = EntityListSerializer(read_only=True)
    artist = EntityListSerializer(read_only=True)
    brand = EntityListSerializer(read_only=True)
    song = RecordingListSerializer(read_only=True)
    contact_person = ContactPersonSerializer(read_only=True)
    handlers = CampaignHandlerSerializer(many=True, read_only=True)
    created_by_name = serializers.SerializerMethodField()
    department_display = serializers.SerializerMethodField()
    service_type_display = serializers.CharField(source='get_service_type_display', read_only=True)
    platform_display = serializers.CharField(source='get_platform_display', read_only=True)
    tasks_count = serializers.IntegerField(source='tasks.count', read_only=True)
    activities_count = serializers.IntegerField(source='activities.count', read_only=True)

    class Meta:
        model = Campaign
        fields = [
            'id',
            'campaign_name',
            'client',
            'artist',
            'brand',
            'song',
            'contact_person',
            'department',
            'department_display',
            'value',
            'currency',
            'status',
            'service_type',
            'service_type_display',
            'platform',
            'platform_display',
            'start_date',
            'end_date',
            'budget_allocated',
            'budget_spent',
            'client_health_score',
            'kpi_targets',
            'kpi_actuals',
            'department_data',
            'confirmed_at',
            'notes',
            'handlers',
            'tasks_count',
            'activities_count',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at', 'department']

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None

    def get_department_display(self, obj):
        """Return department name or 'Admin Only' for null departments"""
        if obj.department:
            return obj.department.name
        return "Admin Only"


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
            'song',
            'contact_person',
            'department',  # Optional: Admins can specify or leave null (admin-only), auto-set for others
            'value',
            'currency',
            'status',
            'service_type',
            'platform',
            'start_date',
            'end_date',
            'budget_allocated',
            'budget_spent',
            'client_health_score',
            'kpi_targets',
            'kpi_actuals',
            'department_data',
            'confirmed_at',
            'notes',
            'handlers',
        ]
        read_only_fields = ['id']
        extra_kwargs = {
            'department': {'required': False, 'allow_null': True},
            'service_type': {'required': False, 'allow_blank': True},
            'platform': {'required': False, 'allow_blank': True},
            'currency': {'required': False},
        }

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

        # Validate department assignment (for create only)
        request = self.context.get('request')
        if request and hasattr(request, 'user') and not self.instance:
            user = request.user
            profile = getattr(user, 'profile', None)

            if not profile:
                raise serializers.ValidationError(
                    "User profile not found. Cannot create campaign."
                )

            # Admins can create campaigns for any department, or leave null for admin-only
            if profile.is_admin:
                # Admins can leave department as null (admin-only campaign)
                # If they specify a department, it's validated by the FK
                pass
            else:
                # Non-admins must be assigned to a department
                if not profile.department:
                    raise serializers.ValidationError(
                        "You must be assigned to a department to create campaigns."
                    )
                # Auto-set department for non-admins (ignore any department sent in request)
                data['department'] = profile.department

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
        """Set created_by from request user, handle handlers"""
        handlers_data = validated_data.pop('handlers', [])

        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            user = request.user
            validated_data['created_by'] = user
            # Note: department is already set in validate() method

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
