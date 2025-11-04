from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Distribution, DistributionCatalogItem, DistributionRevenueReport, PLATFORM_CHOICES
from identity.serializers import EntityListSerializer, ContactPersonSerializer
from catalog.serializers import RecordingListSerializer, ReleaseListSerializer

User = get_user_model()


class ContractMinimalSerializer(serializers.Serializer):
    """Minimal serializer for contract display"""
    id = serializers.IntegerField()
    contract_number = serializers.CharField()
    title = serializers.CharField()


class DistributionRevenueReportSerializer(serializers.ModelSerializer):
    """Serializer for revenue reports"""
    platform_display = serializers.CharField(source='get_platform_display', read_only=True)
    created_by_name = serializers.SerializerMethodField()
    # Override reporting_period to accept month format (YYYY-MM)
    reporting_period = serializers.CharField()

    class Meta:
        model = DistributionRevenueReport
        fields = [
            'id',
            'catalog_item',
            'platform',
            'platform_display',
            'reporting_period',
            'revenue_amount',
            'currency',
            'streams',
            'downloads',
            'notes',
            'created_at',
            'updated_at',
            'created_by',
            'created_by_name',
        ]
        read_only_fields = ['created_at', 'updated_at', 'catalog_item']  # catalog_item set via URL

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None

    def validate_reporting_period(self, value):
        """Convert month format (YYYY-MM) to first day of month (YYYY-MM-01)"""
        from datetime import date

        if isinstance(value, str):
            # If format is YYYY-MM (month input), convert to first day of month
            if len(value) == 7 and value[4] == '-':
                year, month = value.split('-')
                return date(int(year), int(month), 1)
            # If format is already YYYY-MM-DD, parse it
            elif len(value) == 10:
                year, month, day = value.split('-')
                return date(int(year), int(month), int(day))

        return value


class DistributionCatalogItemListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for catalog item listings"""
    recording = RecordingListSerializer(read_only=True)
    release = ReleaseListSerializer(read_only=True)
    catalog_item_title = serializers.CharField(read_only=True)
    catalog_item_type = serializers.CharField(read_only=True)
    effective_revenue_share = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    platforms_display = serializers.SerializerMethodField()
    distribution_status_display = serializers.CharField(source='get_distribution_status_display', read_only=True)

    class Meta:
        model = DistributionCatalogItem
        fields = [
            'id',
            'distribution',
            'recording',
            'release',
            'catalog_item_title',
            'catalog_item_type',
            'platforms',
            'platforms_display',
            'individual_revenue_share',
            'effective_revenue_share',
            'distribution_status',
            'distribution_status_display',
            'release_date',
            'total_revenue',
            'notes',
            'added_at',
        ]
        read_only_fields = ['added_at']

    def get_platforms_display(self, obj):
        """Return list of platform display names"""
        if not obj.platforms:
            return []
        platform_dict = dict(PLATFORM_CHOICES)
        return [platform_dict.get(p, p) for p in obj.platforms]


class DistributionCatalogItemDetailSerializer(serializers.ModelSerializer):
    """Full serializer for catalog items with revenue reports"""
    recording = RecordingListSerializer(read_only=True)
    release = ReleaseListSerializer(read_only=True)
    catalog_item_title = serializers.CharField(read_only=True)
    catalog_item_type = serializers.CharField(read_only=True)
    effective_revenue_share = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    platforms_display = serializers.SerializerMethodField()
    distribution_status_display = serializers.CharField(source='get_distribution_status_display', read_only=True)
    revenue_reports = DistributionRevenueReportSerializer(many=True, read_only=True)

    class Meta:
        model = DistributionCatalogItem
        fields = [
            'id',
            'distribution',
            'recording',
            'release',
            'catalog_item_title',
            'catalog_item_type',
            'platforms',
            'platforms_display',
            'individual_revenue_share',
            'effective_revenue_share',
            'distribution_status',
            'distribution_status_display',
            'release_date',
            'total_revenue',
            'notes',
            'added_at',
            'revenue_reports',
        ]
        read_only_fields = ['added_at']

    def get_platforms_display(self, obj):
        """Return list of platform display names"""
        if not obj.platforms:
            return []
        platform_dict = dict(PLATFORM_CHOICES)
        return [platform_dict.get(p, p) for p in obj.platforms]


class DistributionCatalogItemCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating catalog items"""

    class Meta:
        model = DistributionCatalogItem
        fields = [
            'id',
            'distribution',
            'recording',
            'release',
            'platforms',
            'individual_revenue_share',
            'distribution_status',
            'release_date',
            'notes',
        ]
        read_only_fields = ['distribution']  # Set via URL in perform_create

    def validate(self, data):
        """Validate that exactly one of recording or release is set"""
        recording = data.get('recording')
        release = data.get('release')

        if not recording and not release:
            raise serializers.ValidationError("Must provide either a recording or a release")
        if recording and release:
            raise serializers.ValidationError("Cannot provide both recording and release")

        return data


class DistributionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for distribution listings"""
    entity = EntityListSerializer(read_only=True)
    contact_person = ContactPersonSerializer(read_only=True)
    deal_type_display = serializers.CharField(source='get_deal_type_display', read_only=True)
    deal_status_display = serializers.CharField(source='get_deal_status_display', read_only=True)
    department_display = serializers.SerializerMethodField()
    track_count = serializers.IntegerField(read_only=True)
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Distribution
        fields = [
            'id',
            'entity',
            'deal_type',
            'deal_type_display',
            'deal_status',
            'deal_status_display',
            'global_revenue_share_percentage',
            'signing_date',
            'track_count',
            'total_revenue',
            'contact_person',
            'department',
            'department_display',
            'notes',
            'created_at',
            'updated_at',
            'created_by_name',
        ]

    def get_department_display(self, obj):
        """Return department name or 'Admin Only' for null departments"""
        if obj.department:
            return obj.department.name
        return "Admin Only"

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None


class DistributionDetailSerializer(serializers.ModelSerializer):
    """Full serializer for distribution details"""
    entity = EntityListSerializer(read_only=True)
    contract = ContractMinimalSerializer(read_only=True)
    contact_person = ContactPersonSerializer(read_only=True)
    deal_type_display = serializers.CharField(source='get_deal_type_display', read_only=True)
    deal_status_display = serializers.CharField(source='get_deal_status_display', read_only=True)
    department_display = serializers.SerializerMethodField()
    track_count = serializers.IntegerField(read_only=True)
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    catalog_items = DistributionCatalogItemDetailSerializer(many=True, read_only=True)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Distribution
        fields = [
            'id',
            'entity',
            'deal_type',
            'deal_type_display',
            'deal_status',
            'deal_status_display',
            'contract',
            'global_revenue_share_percentage',
            'signing_date',
            'track_count',
            'total_revenue',
            'contact_person',
            'notes',
            'special_terms',
            'department',
            'department_display',
            'catalog_items',
            'created_at',
            'updated_at',
            'created_by',
            'created_by_name',
        ]

    def get_department_display(self, obj):
        """Return department name or 'Admin Only' for null departments"""
        if obj.department:
            return obj.department.name
        return "Admin Only"

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None


class DistributionCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating distributions"""

    class Meta:
        model = Distribution
        fields = [
            'id',
            'entity',
            'deal_type',
            'deal_status',
            'contract',
            'department',
            'global_revenue_share_percentage',
            'signing_date',
            'contact_person',
            'notes',
            'special_terms',
        ]

    def validate(self, data):
        """Auto-populate deal_type based on entity roles if not provided"""
        entity = data.get('entity')

        # If deal_type is provided, use it as-is (user can override)
        if 'deal_type' not in data or not data['deal_type']:
            # Auto-populate deal_type from entity roles
            if entity:
                roles = entity.entity_roles.values_list('role', flat=True)

                if 'aggregator' in roles:
                    data['deal_type'] = 'aggregator'
                elif 'label' in roles:
                    data['deal_type'] = 'label'
                elif 'artist' in roles:
                    data['deal_type'] = 'artist'
                else:
                    # Default to artist if no matching role found
                    data['deal_type'] = 'artist'

        # Validate department assignment (for create only)
        request = self.context.get('request')
        if request and hasattr(request, 'user') and not self.instance:
            user = request.user
            profile = getattr(user, 'profile', None)

            if not profile:
                raise serializers.ValidationError(
                    "User profile not found. Cannot create distribution."
                )

            # Admins can create distributions for any department, or leave null for admin-only
            if profile.is_admin:
                # Admins can leave department as null (admin-only distribution)
                # If they specify a department, it's validated by the FK
                pass
            else:
                # Non-admins must be assigned to a department
                if not profile.department:
                    raise serializers.ValidationError(
                        "You must be assigned to a department to create distributions."
                    )
                # Auto-set department for non-admins (ignore any department sent in request)
                data['department'] = profile.department

        return data

    def create(self, validated_data):
        """Set created_by from request user"""
        request = self.context.get('request')
        if request and request.user:
            validated_data['created_by'] = request.user
        return super().create(validated_data)
