"""
Serializers for Artist Sales - Unified Opportunities API
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from identity.models import Entity, ContactPerson
from api.models import Department
from .models import (
    Opportunity, OpportunityArtist, OpportunityTask, OpportunityActivity,
    OpportunityComment, OpportunityDeliverable, Approval, Invoice,
    DeliverablePack, DeliverablePackItem, UsageTerms
)

User = get_user_model()


# === NESTED SERIALIZERS (for related objects) ===

class UserNestedSerializer(serializers.ModelSerializer):
    """Lightweight user serializer for nested use"""
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name']

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.email


class EntityNestedSerializer(serializers.ModelSerializer):
    """Lightweight entity serializer for nested use"""
    class Meta:
        model = Entity
        fields = ['id', 'display_name', 'kind']


class ContactPersonNestedSerializer(serializers.ModelSerializer):
    """Lightweight contact serializer for nested use"""
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = ContactPerson
        fields = ['id', 'full_name', 'email', 'phone']

    def get_full_name(self, obj):
        return obj.full_name


class DepartmentNestedSerializer(serializers.ModelSerializer):
    """Lightweight department serializer"""
    class Meta:
        model = Department
        fields = ['id', 'name']


# === OPPORTUNITY RELATED SERIALIZERS ===

class OpportunityArtistSerializer(serializers.ModelSerializer):
    """Serializer for OpportunityArtist with nested artist details"""
    artist = EntityNestedSerializer(read_only=True)
    artist_id = serializers.PrimaryKeyRelatedField(
        queryset=Entity.objects.filter(entity_roles__role='artist'),
        source='artist',
        write_only=True
    )

    class Meta:
        model = OpportunityArtist
        fields = [
            'id', 'opportunity', 'artist', 'artist_id', 'role',
            'proposed_fee', 'confirmed_fee', 'contract_status',
            'signed_date', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class OpportunityTaskSerializer(serializers.ModelSerializer):
    """Serializer for OpportunityTask"""
    assigned_to = UserNestedSerializer(read_only=True)
    assigned_to_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='assigned_to',
        write_only=True,
        required=False,
        allow_null=True
    )
    assigned_by = UserNestedSerializer(read_only=True)

    class Meta:
        model = OpportunityTask
        fields = [
            'id', 'opportunity', 'title', 'description', 'task_type',
            'assigned_to', 'assigned_to_id', 'assigned_by', 'due_date',
            'priority', 'status', 'completed_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['assigned_by', 'completed_at', 'created_at', 'updated_at']


class OpportunityActivitySerializer(serializers.ModelSerializer):
    """Serializer for OpportunityActivity (activity feed)"""
    user = UserNestedSerializer(read_only=True)

    class Meta:
        model = OpportunityActivity
        fields = [
            'id', 'opportunity', 'user', 'activity_type', 'title',
            'description', 'metadata', 'created_at'
        ]
        read_only_fields = ['created_at']


class OpportunityCommentSerializer(serializers.ModelSerializer):
    """Serializer for OpportunityComment"""
    user = UserNestedSerializer(read_only=True)

    class Meta:
        model = OpportunityComment
        fields = [
            'id', 'opportunity', 'user', 'comment', 'is_internal',
            'mentions', 'created_at', 'updated_at'
        ]
        read_only_fields = ['user', 'created_at', 'updated_at']


class OpportunityDeliverableSerializer(serializers.ModelSerializer):
    """Serializer for OpportunityDeliverable"""

    class Meta:
        model = OpportunityDeliverable
        fields = [
            'id', 'opportunity', 'deliverable_type', 'quantity',
            'description', 'due_date', 'status', 'asset_url',
            'kpi_target', 'kpi_actual', 'cost_center', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class ApprovalSerializer(serializers.ModelSerializer):
    """Serializer for Approval"""
    approver_contact = ContactPersonNestedSerializer(read_only=True)
    approver_user = UserNestedSerializer(read_only=True)

    class Meta:
        model = Approval
        fields = [
            'id', 'opportunity', 'deliverable', 'stage', 'version',
            'status', 'submitted_at', 'approved_at', 'approver_contact',
            'approver_user', 'notes', 'file_url', 'created_at', 'updated_at'
        ]
        read_only_fields = ['submitted_at', 'created_at', 'updated_at']


class InvoiceSerializer(serializers.ModelSerializer):
    """Serializer for Invoice"""

    class Meta:
        model = Invoice
        fields = [
            'id', 'opportunity', 'invoice_number', 'invoice_type',
            'issue_date', 'due_date', 'amount', 'currency', 'status',
            'paid_date', 'pdf_url', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['invoice_number', 'created_at', 'updated_at']


# === MAIN OPPORTUNITY SERIALIZERS ===

class OpportunityListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for opportunity list/kanban views"""
    account = EntityNestedSerializer(read_only=True)
    contact_person = ContactPersonNestedSerializer(read_only=True)
    owner = UserNestedSerializer(read_only=True)
    team = DepartmentNestedSerializer(read_only=True)

    # Annotated fields from queryset
    artists_count = serializers.IntegerField(read_only=True)
    tasks_count = serializers.IntegerField(read_only=True)
    active_tasks_count = serializers.IntegerField(read_only=True)

    stage_display = serializers.CharField(source='get_stage_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)

    class Meta:
        model = Opportunity
        fields = [
            'id', 'opportunity_number', 'title', 'stage', 'stage_display',
            'probability', 'priority', 'priority_display', 'account',
            'contact_person', 'owner', 'team', 'estimated_value', 'currency',
            'expected_close_date', 'artists_count', 'tasks_count',
            'active_tasks_count', 'tags', 'created_at', 'updated_at'
        ]


class OpportunityDetailSerializer(serializers.ModelSerializer):
    """Full detail serializer for opportunity with all related data"""
    account = EntityNestedSerializer(read_only=True)
    account_id = serializers.PrimaryKeyRelatedField(
        queryset=Entity.objects.all(),
        source='account',
        write_only=True
    )

    contact_person = ContactPersonNestedSerializer(read_only=True)
    contact_person_id = serializers.PrimaryKeyRelatedField(
        queryset=ContactPerson.objects.all(),
        source='contact_person',
        write_only=True,
        required=False,
        allow_null=True
    )

    owner = UserNestedSerializer(read_only=True)
    owner_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='owner',
        write_only=True
    )

    team = DepartmentNestedSerializer(read_only=True)
    team_id = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(),
        source='team',
        write_only=True,
        required=False,
        allow_null=True
    )

    created_by = UserNestedSerializer(read_only=True)

    # Related objects
    artists = OpportunityArtistSerializer(many=True, read_only=True)
    tasks = OpportunityTaskSerializer(many=True, read_only=True)
    deliverables = OpportunityDeliverableSerializer(many=True, read_only=True)

    # Display fields
    stage_display = serializers.CharField(source='get_stage_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)

    class Meta:
        model = Opportunity
        fields = [
            # Core
            'id', 'opportunity_number', 'title', 'stage', 'stage_display',
            'probability', 'priority', 'priority_display',

            # Relationships
            'account', 'account_id', 'contact_person', 'contact_person_id',
            'owner', 'owner_id', 'team', 'team_id', 'created_by',

            # Financial
            'estimated_value', 'currency', 'expected_close_date', 'actual_close_date',

            # Brief fields
            'campaign_objectives', 'target_audience', 'channels', 'brand_category',
            'budget_range_min', 'budget_range_max', 'campaign_start_date', 'campaign_end_date',

            # Proposal fields
            'proposal_version', 'proposal_history', 'fee_gross', 'agency_fee',
            'discounts', 'fee_net', 'proposal_sent_date', 'proposal_valid_until',

            # Contract fields
            'contract_number', 'po_number', 'contract_signed_date',
            'contract_start_date', 'contract_end_date', 'contract_file',

            # Execution
            'deliverable_pack', 'usage_terms',

            # Lost
            'lost_reason', 'lost_date', 'competitor',

            # Metadata
            'notes', 'tags', 'created_at', 'updated_at',

            # Related objects
            'artists', 'tasks', 'deliverables',
        ]
        read_only_fields = [
            'opportunity_number', 'contract_number', 'fee_net',
            'probability', 'created_by', 'created_at', 'updated_at'
        ]


class OpportunityCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating opportunities with minimal required fields"""

    class Meta:
        model = Opportunity
        fields = [
            'title', 'stage', 'priority', 'account', 'contact_person',
            'owner', 'team', 'estimated_value', 'currency', 'expected_close_date',
            'campaign_objectives', 'target_audience', 'brand_category',
            'budget_range_min', 'budget_range_max', 'notes', 'tags'
        ]

    def create(self, validated_data):
        # Set created_by from request user
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


# === DELIVERABLE PACK SERIALIZERS ===

class DeliverablePackItemSerializer(serializers.ModelSerializer):
    """Serializer for DeliverablePackItem"""
    deliverable_type_display = serializers.CharField(source='get_deliverable_type_display', read_only=True)

    class Meta:
        model = DeliverablePackItem
        fields = ['id', 'pack', 'deliverable_type', 'deliverable_type_display', 'quantity', 'description', 'created_at']
        read_only_fields = ['created_at']


class DeliverablePackSerializer(serializers.ModelSerializer):
    """Serializer for DeliverablePack with items"""
    items = DeliverablePackItemSerializer(many=True, read_only=True)

    class Meta:
        model = DeliverablePack
        fields = ['id', 'name', 'description', 'is_active', 'items', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


# === USAGE TERMS SERIALIZERS ===

class UsageTermsSerializer(serializers.ModelSerializer):
    """Serializer for UsageTerms"""

    class Meta:
        model = UsageTerms
        fields = [
            'id', 'name', 'usage_scope', 'territories', 'exclusivity_category',
            'exclusivity_duration_days', 'usage_duration_days', 'extensions_allowed',
            'buyout', 'brand_list_blocked', 'is_template', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
