from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Task, TaskAssignment, Activity, CampaignMetrics, EntityChangeRequest, FlowTrigger, ManualTrigger
from campaigns.models import Campaign
from identity.models import Entity
from contracts.models import Contract

User = get_user_model()


class TaskAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for TaskAssignment (users assigned to tasks)"""
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    assigned_by_email = serializers.EmailField(source='assigned_by.email', read_only=True, allow_null=True)

    class Meta:
        model = TaskAssignment
        fields = ['id', 'user', 'user_email', 'user_name', 'role', 'role_display', 'assigned_at', 'assigned_by', 'assigned_by_email']
        read_only_fields = ['assigned_at', 'assigned_by']

    def get_user_name(self, obj):
        return obj.user.get_full_name() if obj.user else None


class TaskSerializer(serializers.ModelSerializer):
    """
    Serializer for Task model with nested relationship details.
    Includes universal task system entity relationships.
    """
    assignments = TaskAssignmentSerializer(many=True, read_only=True)
    created_by_detail = serializers.SerializerMethodField(read_only=True)
    campaign_detail = serializers.SerializerMethodField(read_only=True)
    entity_detail = serializers.SerializerMethodField(read_only=True)
    contract_detail = serializers.SerializerMethodField(read_only=True)

    # Universal task system entity relationships
    song_detail = serializers.SerializerMethodField(read_only=True)
    work_detail = serializers.SerializerMethodField(read_only=True)
    recording_detail = serializers.SerializerMethodField(read_only=True)
    opportunity_detail = serializers.SerializerMethodField(read_only=True)
    deliverable_detail = serializers.SerializerMethodField(read_only=True)
    checklist_item_detail = serializers.SerializerMethodField(read_only=True)

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
            'tag',

            # Relationships
            'campaign',
            'campaign_detail',
            'entity',
            'entity_detail',
            'contract',
            'contract_detail',

            # Universal task system entity relationships
            'song',
            'song_detail',
            'work',
            'work_detail',
            'recording',
            'recording_detail',
            'opportunity',
            'opportunity_detail',
            'deliverable',
            'deliverable_detail',

            # Checklist linking
            'song_checklist_item',
            'checklist_item_detail',
            'source_stage',
            'source_checklist_name',

            # Assignment
            'assignments',
            'created_by',
            'created_by_detail',
            'department',
            'department_name',

            # Timeline
            'due_date',
            'reminder_date',
            'follow_up_reminder_sent',
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
        read_only_fields = ['created_at', 'updated_at', 'started_at', 'completed_at', 'follow_up_reminder_sent']

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

    def get_song_detail(self, obj):
        if obj.song:
            return {
                'id': obj.song.id,
                'title': obj.song.title,
                'stage': obj.song.stage,
                'artist': obj.song.artist.display_name if obj.song.artist else None
            }
        return None

    def get_work_detail(self, obj):
        if obj.work:
            # Get ISWC from Identifier model
            iswc = None
            try:
                from identity.models import Identifier
                identifier = Identifier.objects.get(
                    owner_type='work',
                    owner_id=obj.work.id,
                    scheme='ISWC'
                )
                iswc = identifier.value
            except Identifier.DoesNotExist:
                pass

            return {
                'id': obj.work.id,
                'title': obj.work.title,
                'iswc': iswc,
            }
        return None

    def get_recording_detail(self, obj):
        if obj.recording:
            # Get ISRC from Identifier model
            isrc = None
            try:
                from identity.models import Identifier
                identifier = Identifier.objects.get(
                    owner_type='recording',
                    owner_id=obj.recording.id,
                    scheme='ISRC'
                )
                isrc = identifier.value
            except Identifier.DoesNotExist:
                pass

            return {
                'id': obj.recording.id,
                'title': obj.recording.title,
                'isrc': isrc,
            }
        return None

    def get_opportunity_detail(self, obj):
        if obj.opportunity:
            return {
                'id': obj.opportunity.id,
                'name': obj.opportunity.name,
                'stage': obj.opportunity.stage,
                'value': str(obj.opportunity.value) if obj.opportunity.value else None
            }
        return None

    def get_deliverable_detail(self, obj):
        if obj.deliverable:
            return {
                'id': obj.deliverable.id,
                'deliverable_type': obj.deliverable.get_deliverable_type_display(),
                'status': obj.deliverable.status,
                'due_date': obj.deliverable.due_date
            }
        return None

    def get_checklist_item_detail(self, obj):
        if obj.song_checklist_item:
            return {
                'id': obj.song_checklist_item.id,
                'name': obj.song_checklist_item.item_name,
                'checklist_name': f"{obj.song_checklist_item.stage} - {obj.song_checklist_item.category}",
                'is_complete': obj.song_checklist_item.is_complete,
            }
        return None


class TaskCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating tasks.
    Note: assigned_users is handled via TaskAssignment in the ViewSet.
    """
    # Allow specifying user IDs for assignment (write-only)
    assigned_user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        help_text="List of user IDs to assign to this task"
    )

    class Meta:
        model = Task
        fields = [
            'id',  # Include id in response
            'title',
            'description',
            'task_type',
            'status',
            'priority',
            'tag',
            'campaign',
            'entity',
            'contract',
            'assigned_user_ids',  # For specifying assignments on create/update
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
        read_only_fields = ['id']

    def validate(self, data):
        # Associations (campaign, entity, contract) are now fully optional
        # Tasks can be created for general/internal work not tied to any specific association
        # Previous validation required at least one association, but this was too restrictive
        # for ad-hoc tasks, internal work, or digital department tasks
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


class EntityChangeRequestSerializer(serializers.ModelSerializer):
    """
    Serializer for EntityChangeRequest with user and entity details.
    """
    requested_by_detail = serializers.SerializerMethodField(read_only=True)
    reviewed_by_detail = serializers.SerializerMethodField(read_only=True)
    entity_detail = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = EntityChangeRequest
        fields = [
            'id',
            'entity',
            'entity_detail',
            'request_type',
            'requested_by',
            'requested_by_detail',
            'message',
            'status',
            'reviewed_by',
            'reviewed_by_detail',
            'reviewed_at',
            'admin_notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['requested_by', 'status', 'reviewed_by', 'reviewed_at']

    def get_requested_by_detail(self, obj):
        if obj.requested_by:
            return {
                'id': obj.requested_by.id,
                'email': obj.requested_by.email,
                'full_name': f"{obj.requested_by.first_name} {obj.requested_by.last_name}".strip() or obj.requested_by.email
            }
        return None

    def get_reviewed_by_detail(self, obj):
        if obj.reviewed_by:
            return {
                'id': obj.reviewed_by.id,
                'email': obj.reviewed_by.email,
                'full_name': f"{obj.reviewed_by.first_name} {obj.reviewed_by.last_name}".strip() or obj.reviewed_by.email
            }
        return None

    def get_entity_detail(self, obj):
        if obj.entity:
            return {
                'id': obj.entity.id,
                'display_name': obj.entity.display_name,
                'kind': obj.entity.kind,
            }
        return None

class FlowTriggerSerializer(serializers.ModelSerializer):
    """
    Serializer for FlowTrigger - automatic task creation triggers.
    Read-only for frontend consumption.
    """
    trigger_event_display = serializers.CharField(source='get_trigger_event_display', read_only=True)

    class Meta:
        model = FlowTrigger
        fields = [
            'id',
            'name',
            'description',
            'trigger_entity_type',
            'trigger_event',
            'trigger_event_display',
            'trigger_conditions',
            'creates_task',
            'task_config',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class ManualTriggerSerializer(serializers.ModelSerializer):
    """
    Serializer for ManualTrigger - UI button definitions for task creation.
    """
    visible_departments = serializers.SlugRelatedField(
        slug_field='name',
        many=True,
        read_only=True,
        source='visible_to_departments'
    )
    button_style_display = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ManualTrigger
        fields = [
            'id',
            'name',
            'button_label',
            'button_style',
            'button_style_display',
            'entity_type',
            'context',
            'action_type',
            'action_config',
            'visible_departments',
            'required_permissions',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_button_style_display(self, obj):
        return obj.button_style.capitalize() if obj.button_style else 'Primary'
