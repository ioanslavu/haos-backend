from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Task, Activity, CampaignMetrics
from campaigns.models import Campaign
from identity.models import Entity
from contracts.models import Contract

User = get_user_model()


class TaskSerializer(serializers.ModelSerializer):
    """
    Serializer for Task model with nested relationship details.
    """
    assigned_to_detail = serializers.SerializerMethodField(read_only=True)
    created_by_detail = serializers.SerializerMethodField(read_only=True)
    campaign_detail = serializers.SerializerMethodField(read_only=True)
    entity_detail = serializers.SerializerMethodField(read_only=True)
    contract_detail = serializers.SerializerMethodField(read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    is_blocked = serializers.BooleanField(read_only=True)
    subtasks_count = serializers.IntegerField(source='subtasks.count', read_only=True)

    class Meta:
        model = Task
        fields = [
            'id',
            'title',
            'description',
            'task_type',
            'status',
            'priority',

            # Relationships
            'campaign',
            'campaign_detail',
            'entity',
            'entity_detail',
            'contract',
            'contract_detail',

            # Assignment
            'assigned_to',
            'assigned_to_detail',
            'created_by',
            'created_by_detail',
            'department',
            'department_name',

            # Timeline
            'due_date',
            'reminder_date',
            'started_at',
            'completed_at',

            # Dependencies
            'parent_task',
            'blocks_tasks',
            'subtasks_count',

            # Time tracking
            'estimated_hours',
            'actual_hours',

            # Metadata
            'metadata',
            'notes',

            # Computed fields
            'is_overdue',
            'is_blocked',

            # Timestamps
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at', 'started_at', 'completed_at']

    def get_assigned_to_detail(self, obj):
        if obj.assigned_to:
            return {
                'id': obj.assigned_to.id,
                'email': obj.assigned_to.email,
                'full_name': f"{obj.assigned_to.first_name} {obj.assigned_to.last_name}".strip() or obj.assigned_to.email
            }
        return None

    def get_created_by_detail(self, obj):
        if obj.created_by:
            return {
                'id': obj.created_by.id,
                'email': obj.created_by.email,
                'full_name': f"{obj.created_by.first_name} {obj.created_by.last_name}".strip() or obj.created_by.email
            }
        return None

    def get_campaign_detail(self, obj):
        if obj.campaign:
            return {
                'id': obj.campaign.id,
                'name': obj.campaign.campaign_name,
                'status': obj.campaign.status,
                'value': str(obj.campaign.value)
            }
        return None

    def get_entity_detail(self, obj):
        if obj.entity:
            return {
                'id': obj.entity.id,
                'display_name': obj.entity.display_name,
                'kind': obj.entity.kind
            }
        return None

    def get_contract_detail(self, obj):
        if obj.contract:
            return {
                'id': obj.contract.id,
                'title': obj.contract.title,
                'contract_number': obj.contract.contract_number,
                'status': obj.contract.status
            }
        return None


class TaskCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating tasks.
    """
    class Meta:
        model = Task
        fields = [
            'title',
            'description',
            'task_type',
            'status',
            'priority',
            'campaign',
            'entity',
            'contract',
            'assigned_to',
            'department',
            'due_date',
            'reminder_date',
            'parent_task',
            'blocks_tasks',
            'estimated_hours',
            'actual_hours',
            'metadata',
            'notes',
        ]

    def validate(self, data):
        # Ensure at least one association is provided
        if not any([data.get('campaign'), data.get('entity'), data.get('contract')]):
            raise serializers.ValidationError(
                "At least one of campaign, entity, or contract must be provided."
            )
        return data


class ActivitySerializer(serializers.ModelSerializer):
    """
    Serializer for Activity model with nested relationship details.
    """
    created_by_detail = serializers.SerializerMethodField(read_only=True)
    entity_detail = serializers.SerializerMethodField(read_only=True)
    campaign_detail = serializers.SerializerMethodField(read_only=True)
    contact_person_detail = serializers.SerializerMethodField(read_only=True)
    participants_detail = serializers.SerializerMethodField(read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    follow_up_task_detail = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Activity
        fields = [
            'id',
            'type',
            'subject',
            'content',

            # Relationships
            'entity',
            'entity_detail',
            'contact_person',
            'contact_person_detail',
            'campaign',
            'campaign_detail',
            'contract',

            # Participants
            'created_by',
            'created_by_detail',
            'participants',
            'participants_detail',
            'external_participants',

            # Communication
            'direction',
            'sentiment',

            # Activity metadata
            'activity_date',
            'duration_minutes',
            'location',

            # Follow-up
            'follow_up_required',
            'follow_up_date',
            'follow_up_completed',
            'follow_up_task',
            'follow_up_task_detail',

            # Attachments
            'attachments',
            'related_url',

            # Department
            'department',
            'department_name',

            # Metadata
            'metadata',

            # Timestamps
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at', 'follow_up_task']

    def get_created_by_detail(self, obj):
        if obj.created_by:
            return {
                'id': obj.created_by.id,
                'email': obj.created_by.email,
                'full_name': f"{obj.created_by.first_name} {obj.created_by.last_name}".strip() or obj.created_by.email
            }
        return None

    def get_entity_detail(self, obj):
        if obj.entity:
            return {
                'id': obj.entity.id,
                'display_name': obj.entity.display_name,
                'kind': obj.entity.kind
            }
        return None

    def get_campaign_detail(self, obj):
        if obj.campaign:
            return {
                'id': obj.campaign.id,
                'name': obj.campaign.campaign_name,
                'status': obj.campaign.status
            }
        return None

    def get_contact_person_detail(self, obj):
        if obj.contact_person:
            return {
                'id': obj.contact_person.id,
                'name': obj.contact_person.name,
                'email': obj.contact_person.email,
                'phone': obj.contact_person.phone
            }
        return None

    def get_participants_detail(self, obj):
        return [
            {
                'id': user.id,
                'email': user.email,
                'full_name': f"{user.first_name} {user.last_name}".strip() or user.email
            }
            for user in obj.participants.all()
        ]

    def get_follow_up_task_detail(self, obj):
        if obj.follow_up_task:
            return {
                'id': obj.follow_up_task.id,
                'title': obj.follow_up_task.title,
                'status': obj.follow_up_task.status,
                'due_date': obj.follow_up_task.due_date
            }
        return None


class ActivityCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating activities.
    """
    class Meta:
        model = Activity
        fields = [
            'type',
            'subject',
            'content',
            'entity',
            'contact_person',
            'campaign',
            'contract',
            'participants',
            'external_participants',
            'direction',
            'sentiment',
            'activity_date',
            'duration_minutes',
            'location',
            'follow_up_required',
            'follow_up_date',
            'attachments',
            'related_url',
            'department',
            'metadata',
        ]

    def validate(self, data):
        # Ensure at least one association is provided
        if not any([data.get('entity'), data.get('campaign'), data.get('contract')]):
            raise serializers.ValidationError(
                "At least one of entity, campaign, or contract must be provided."
            )

        # Validate follow-up requirements
        if data.get('follow_up_required') and not data.get('follow_up_date'):
            raise serializers.ValidationError(
                "Follow-up date is required when follow-up is marked as required."
            )

        return data


class CampaignMetricsSerializer(serializers.ModelSerializer):
    """
    Serializer for CampaignMetrics model.
    """
    campaign_name = serializers.CharField(source='campaign.campaign_name', read_only=True)
    campaign_status = serializers.CharField(source='campaign.status', read_only=True)

    class Meta:
        model = CampaignMetrics
        fields = [
            'id',
            'campaign',
            'campaign_name',
            'campaign_status',
            'recorded_date',
            'source',

            # Performance metrics
            'impressions',
            'clicks',
            'ctr',
            'conversions',
            'conversion_rate',
            'cost',
            'cpc',
            'cpa',

            # Social media metrics
            'reach',
            'engagement',
            'engagement_rate',
            'followers_gained',
            'followers_lost',

            # Content metrics
            'views',
            'watch_time_minutes',
            'shares',
            'comments',
            'likes',

            # Music metrics
            'streams',
            'downloads',
            'playlist_adds',
            'radio_plays',

            # Revenue metrics
            'revenue',
            'roi',

            # Custom metrics
            'custom_metrics',

            # Timestamps
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class CampaignWithMetricsSerializer(serializers.ModelSerializer):
    """
    Extended campaign serializer that includes latest metrics.
    """
    latest_metrics = serializers.SerializerMethodField()
    tasks_count = serializers.IntegerField(source='tasks.count', read_only=True)
    activities_count = serializers.IntegerField(source='activities.count', read_only=True)

    class Meta:
        model = Campaign
        fields = '__all__'

    def get_latest_metrics(self, obj):
        latest = obj.metrics_history.order_by('-recorded_date').first()
        if latest:
            return CampaignMetricsSerializer(latest).data
        return None