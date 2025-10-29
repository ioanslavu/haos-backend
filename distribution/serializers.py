from rest_framework import serializers
from django.utils import timezone
from .models import Publication, PublicationReport


class PublicationListSerializer(serializers.ModelSerializer):
    """Light serializer for Publication listing."""

    platform_display = serializers.CharField(source='get_platform_display', read_only=True)
    platform_icon = serializers.CharField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    territory_display = serializers.CharField(source='get_territory_display', read_only=True)
    channel_display = serializers.CharField(source='get_channel_display', read_only=True)
    object_title = serializers.SerializerMethodField()
    object_type_display = serializers.CharField(source='get_object_type_display', read_only=True)

    class Meta:
        model = Publication
        fields = [
            'id', 'object_type', 'object_type_display', 'object_id',
            'object_title', 'platform', 'platform_display', 'platform_icon',
            'territory', 'territory_display', 'status', 'status_display',
            'channel', 'channel_display', 'is_monetized', 'url',
            'published_at', 'is_active', 'created_at'
        ]
        read_only_fields = ['created_at']

    def get_object_title(self, obj):
        """Get the title of the published object."""
        if obj.object_type == 'recording':
            recording = obj.get_recording
            return recording.title if recording else f"Recording #{obj.object_id}"
        elif obj.object_type == 'release':
            release = obj.get_release
            return release.title if release else f"Release #{obj.object_id}"
        return f"{obj.object_type} #{obj.object_id}"


class PublicationDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for Publication with full information."""

    platform_display = serializers.CharField(source='get_platform_display', read_only=True)
    platform_icon = serializers.CharField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    territory_display = serializers.CharField(source='get_territory_display', read_only=True)
    channel_display = serializers.CharField(source='get_channel_display', read_only=True)
    object_title = serializers.SerializerMethodField()
    object_details = serializers.SerializerMethodField()
    object_type_display = serializers.CharField(source='get_object_type_display', read_only=True)

    class Meta:
        model = Publication
        fields = [
            'id', 'object_type', 'object_type_display', 'object_id',
            'object_title', 'object_details', 'platform', 'platform_display',
            'platform_icon', 'territory', 'territory_display', 'status',
            'status_display', 'url', 'external_id', 'content_id',
            'published_at', 'scheduled_for', 'taken_down_at', 'is_active',
            'channel', 'channel_display', 'is_monetized', 'owner_account',
            'distributor', 'metrics', 'last_metrics_update', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'is_active']

    def get_object_title(self, obj):
        """Get the title of the published object."""
        if obj.object_type == 'recording':
            recording = obj.get_recording
            return recording.title if recording else f"Recording #{obj.object_id}"
        elif obj.object_type == 'release':
            release = obj.get_release
            return release.title if release else f"Release #{obj.object_id}"
        return f"{obj.object_type} #{obj.object_id}"

    def get_object_details(self, obj):
        """Get basic details of the published object."""
        if obj.object_type == 'recording':
            recording = obj.get_recording
            if recording:
                return {
                    'title': recording.title,
                    'isrc': recording.get_isrc(),
                    'duration': recording.formatted_duration,
                    'work_title': recording.work.title if recording.work else None
                }
        elif obj.object_type == 'release':
            release = obj.get_release
            if release:
                return {
                    'title': release.title,
                    'upc': release.get_upc(),
                    'release_date': release.release_date,
                    'track_count': release.track_count,
                    'label_name': release.label_name
                }
        return None


class PublicationCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating Publication."""

    class Meta:
        model = Publication
        fields = [
            'object_type', 'object_id', 'platform', 'territory', 'status',
            'url', 'external_id', 'content_id', 'published_at', 'scheduled_for',
            'taken_down_at', 'channel', 'is_monetized', 'owner_account',
            'distributor', 'metrics', 'notes'
        ]

    def validate(self, data):
        """Validate publication data."""
        # Validate object exists
        if 'object_type' in data and 'object_id' in data:
            object_type = data['object_type']
            object_id = data['object_id']

            if object_type == 'recording':
                from catalog.models import Recording
                if not Recording.objects.filter(id=object_id).exists():
                    raise serializers.ValidationError(
                        f"Recording #{object_id} does not exist."
                    )
            elif object_type == 'release':
                from catalog.models import Release
                if not Release.objects.filter(id=object_id).exists():
                    raise serializers.ValidationError(
                        f"Release #{object_id} does not exist."
                    )

        # Validate dates
        if 'scheduled_for' in data and 'published_at' in data:
            if data['scheduled_for'] and data['published_at']:
                if data['scheduled_for'] <= data['published_at']:
                    raise serializers.ValidationError(
                        "Scheduled date must be after published date."
                    )

        # Check for duplicate publications
        if not self.instance:  # Only check on create
            existing = Publication.objects.filter(
                object_type=data.get('object_type'),
                object_id=data.get('object_id'),
                platform=data.get('platform'),
                territory=data.get('territory')
            )
            if existing.exists():
                raise serializers.ValidationError(
                    "A publication already exists for this object, platform, and territory."
                )

        return data


class PublicationBulkCreateSerializer(serializers.Serializer):
    """Serializer for bulk creating publications."""

    object_type = serializers.ChoiceField(choices=Publication.OBJECT_TYPE_CHOICES)
    object_id = serializers.IntegerField()
    platforms = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
        help_text="List of platform publications with platform, territory, url, etc."
    )

    def validate_platforms(self, value):
        """Validate the platforms list."""
        for platform_data in value:
            if 'platform' not in platform_data:
                raise serializers.ValidationError("Each publication must have a platform.")
            if 'territory' not in platform_data:
                raise serializers.ValidationError("Each publication must have a territory.")

            # Validate platform
            platform = platform_data['platform']
            valid_platforms = dict(Publication.PLATFORM_CHOICES).keys()
            if platform not in valid_platforms:
                raise serializers.ValidationError(
                    f"Invalid platform: {platform}. Valid platforms: {', '.join(valid_platforms)}"
                )

        return value


class CoverageReportSerializer(serializers.Serializer):
    """Serializer for coverage report."""

    object_type = serializers.CharField()
    object_id = serializers.IntegerField()
    object_title = serializers.CharField()
    total_platforms = serializers.IntegerField()
    covered_count = serializers.IntegerField()
    coverage_percentage = serializers.FloatField()
    covered_platforms = serializers.ListField(child=serializers.CharField())
    missing_platforms = serializers.ListField(child=serializers.CharField())
    publications = PublicationListSerializer(many=True)
    by_territory = serializers.DictField()
    by_status = serializers.DictField()


class TerritoryStatsSerializer(serializers.Serializer):
    """Serializer for territory statistics."""

    territory = serializers.CharField()
    territory_display = serializers.CharField()
    publication_count = serializers.IntegerField()
    platforms = serializers.ListField(child=serializers.CharField())
    live_count = serializers.IntegerField()
    scheduled_count = serializers.IntegerField()
    taken_down_count = serializers.IntegerField()
    monetized_count = serializers.IntegerField()


class PlatformStatsSerializer(serializers.Serializer):
    """Serializer for platform statistics."""

    platform = serializers.CharField()
    platform_display = serializers.CharField()
    platform_icon = serializers.CharField()
    publication_count = serializers.IntegerField()
    territories = serializers.ListField(child=serializers.CharField())
    live_count = serializers.IntegerField()
    scheduled_count = serializers.IntegerField()
    taken_down_count = serializers.IntegerField()
    monetized_count = serializers.IntegerField()
    total_views = serializers.IntegerField(required=False)
    total_revenue = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)


class UpdateMetricsSerializer(serializers.Serializer):
    """Serializer for updating publication metrics."""

    metrics = serializers.DictField(
        help_text="Dictionary of metrics (views, likes, revenue, etc.)"
    )

    def validate_metrics(self, value):
        """Validate metrics data."""
        if not value:
            raise serializers.ValidationError("Metrics cannot be empty.")

        # Ensure numeric values are properly formatted
        for key, val in value.items():
            if isinstance(val, (int, float)):
                if val < 0:
                    raise serializers.ValidationError(
                        f"Metric '{key}' cannot be negative."
                    )

        return value


class PublicationActionSerializer(serializers.Serializer):
    """Serializer for publication actions (go live, take down, etc.)."""

    action = serializers.ChoiceField(
        choices=['go_live', 'schedule', 'take_down', 'unschedule']
    )
    scheduled_for = serializers.DateTimeField(
        required=False,
        help_text="Required when action is 'schedule'"
    )
    reason = serializers.CharField(
        required=False,
        max_length=500,
        help_text="Optional reason for the action"
    )

    def validate(self, data):
        """Validate action data."""
        action = data['action']

        if action == 'schedule' and 'scheduled_for' not in data:
            raise serializers.ValidationError(
                "scheduled_for is required when scheduling a publication."
            )

        if action == 'schedule' and data.get('scheduled_for'):
            if data['scheduled_for'] <= timezone.now():
                raise serializers.ValidationError(
                    "Scheduled date must be in the future."
                )

        return data