from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Brief, Opportunity, Proposal, ProposalArtist,
    DeliverablePack, DeliverablePackItem, UsageTerms,
    Deal, DealArtist, DealDeliverable, Approval, Invoice
)
from identity.serializers import EntityListSerializer, ContactPersonSerializer

User = get_user_model()


# Brief Serializers

class BriefListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for brief listings"""
    account = EntityListSerializer(read_only=True)
    contact_person = ContactPersonSerializer(read_only=True)
    created_by_name = serializers.SerializerMethodField()
    department_display = serializers.SerializerMethodField()
    brief_status_display = serializers.CharField(source='get_brief_status_display', read_only=True)
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = Brief
        fields = [
            'id', 'campaign_title', 'account', 'contact_person',
            'brand_category', 'brief_status', 'brief_status_display',
            'received_date', 'sla_due_date', 'is_overdue',
            'budget_range_min', 'budget_range_max', 'currency',
            'department', 'department_display', 'created_by_name',
            'created_at', 'updated_at'
        ]

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None

    def get_department_display(self, obj):
        return obj.department.name if obj.department else "Admin Only"

    def get_is_overdue(self, obj):
        if obj.sla_due_date and obj.brief_status in ['new', 'qualified']:
            from django.utils import timezone
            return obj.sla_due_date < timezone.now().date()
        return False


class BriefDetailSerializer(serializers.ModelSerializer):
    """Full serializer for brief details"""
    account = EntityListSerializer(read_only=True)
    contact_person = ContactPersonSerializer(read_only=True)
    created_by_name = serializers.SerializerMethodField()
    department_display = serializers.SerializerMethodField()
    brief_status_display = serializers.CharField(source='get_brief_status_display', read_only=True)
    opportunities_count = serializers.SerializerMethodField()

    class Meta:
        model = Brief
        fields = '__all__'

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None

    def get_department_display(self, obj):
        return obj.department.name if obj.department else "Admin Only"

    def get_opportunities_count(self, obj):
        return obj.opportunities.count()


# Opportunity Serializers

class OpportunityListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for opportunity listings"""
    brief = serializers.SerializerMethodField()
    account = EntityListSerializer(read_only=True)
    owner_user_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    department_display = serializers.SerializerMethodField()
    stage_display = serializers.CharField(source='get_stage_display', read_only=True)
    weighted_value = serializers.SerializerMethodField()

    class Meta:
        model = Opportunity
        fields = [
            'id', 'opp_name', 'brief', 'account', 'stage', 'stage_display',
            'amount_expected', 'currency', 'probability_percent', 'weighted_value',
            'expected_close_date', 'actual_close_date', 'next_step',
            'owner_user', 'owner_user_name', 'department', 'department_display',
            'created_by_name', 'created_at', 'updated_at'
        ]

    def get_brief(self, obj):
        if obj.brief:
            return {'id': obj.brief.id, 'campaign_title': obj.brief.campaign_title}
        return None

    def get_owner_user_name(self, obj):
        return obj.owner_user.get_full_name() if obj.owner_user else None

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None

    def get_department_display(self, obj):
        return obj.department.name if obj.department else "Admin Only"

    def get_weighted_value(self, obj):
        """Calculate weighted value (amount * probability)"""
        if obj.amount_expected and obj.probability_percent:
            weighted = (obj.amount_expected * obj.probability_percent) / 100
            return str(weighted)
        return None


class OpportunityDetailSerializer(serializers.ModelSerializer):
    """Full serializer for opportunity details"""
    brief = BriefListSerializer(read_only=True)
    account = EntityListSerializer(read_only=True)
    owner_user_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    department_display = serializers.SerializerMethodField()
    stage_display = serializers.CharField(source='get_stage_display', read_only=True)
    proposals_count = serializers.SerializerMethodField()

    class Meta:
        model = Opportunity
        fields = '__all__'

    def get_owner_user_name(self, obj):
        return obj.owner_user.get_full_name() if obj.owner_user else None

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None

    def get_department_display(self, obj):
        return obj.department.name if obj.department else "Admin Only"

    def get_proposals_count(self, obj):
        return obj.proposals.count()


# Proposal Serializers

class ProposalArtistSerializer(serializers.ModelSerializer):
    """Serializer for ProposalArtist (M2M)"""
    artist = EntityListSerializer(read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = ProposalArtist
        fields = ['id', 'artist', 'role', 'role_display', 'proposed_fee', 'created_at']


class ProposalListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for proposal listings"""
    opportunity = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    proposal_status_display = serializers.CharField(source='get_proposal_status_display', read_only=True)
    artists_count = serializers.SerializerMethodField()

    class Meta:
        model = Proposal
        fields = [
            'id', 'opportunity', 'version', 'proposal_status', 'proposal_status_display',
            'fee_gross', 'discounts', 'agency_fee', 'fee_net', 'currency',
            'sent_date', 'valid_until', 'artists_count',
            'created_by_name', 'created_at', 'updated_at'
        ]

    def get_opportunity(self, obj):
        return {
            'id': obj.opportunity.id,
            'opp_name': obj.opportunity.opp_name,
            'account_name': obj.opportunity.account.display_name
        }

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None

    def get_artists_count(self, obj):
        return obj.proposal_artists.count()


class ProposalDetailSerializer(serializers.ModelSerializer):
    """Full serializer for proposal details"""
    opportunity = OpportunityListSerializer(read_only=True)
    proposal_artists = ProposalArtistSerializer(many=True, read_only=True)
    created_by_name = serializers.SerializerMethodField()
    proposal_status_display = serializers.CharField(source='get_proposal_status_display', read_only=True)

    class Meta:
        model = Proposal
        fields = '__all__'

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None


# Deliverable Pack Serializers

class DeliverablePackItemSerializer(serializers.ModelSerializer):
    """Serializer for DeliverablePackItem"""
    deliverable_type_display = serializers.CharField(source='get_deliverable_type_display', read_only=True)

    class Meta:
        model = DeliverablePackItem
        fields = ['id', 'deliverable_type', 'deliverable_type_display', 'quantity', 'description', 'created_at']


class DeliverablePackListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for deliverable pack listings"""
    items_count = serializers.SerializerMethodField()
    items = DeliverablePackItemSerializer(many=True, read_only=True)

    class Meta:
        model = DeliverablePack
        fields = ['id', 'name', 'description', 'is_active', 'items_count', 'items', 'created_at', 'updated_at']

    def get_items_count(self, obj):
        return obj.items.count()


class DeliverablePackDetailSerializer(serializers.ModelSerializer):
    """Full serializer for deliverable pack details"""
    items = DeliverablePackItemSerializer(many=True, read_only=True)

    class Meta:
        model = DeliverablePack
        fields = '__all__'


# Usage Terms Serializers

class UsageTermsListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for usage terms listings"""
    usage_scope_display = serializers.SerializerMethodField()

    class Meta:
        model = UsageTerms
        fields = [
            'id', 'name', 'usage_scope', 'usage_scope_display',
            'usage_duration_days', 'exclusivity_category', 'exclusivity_duration_days',
            'buyout', 'is_template', 'created_at', 'updated_at'
        ]

    def get_usage_scope_display(self, obj):
        """Return list of usage scope display names"""
        if not obj.usage_scope:
            return []
        scope_dict = dict(UsageTerms.USAGE_SCOPE_CHOICES)
        return [scope_dict.get(s, s) for s in obj.usage_scope]


class UsageTermsDetailSerializer(serializers.ModelSerializer):
    """Full serializer for usage terms details"""
    usage_scope_display = serializers.SerializerMethodField()

    class Meta:
        model = UsageTerms
        fields = '__all__'

    def get_usage_scope_display(self, obj):
        """Return list of usage scope display names"""
        if not obj.usage_scope:
            return []
        scope_dict = dict(UsageTerms.USAGE_SCOPE_CHOICES)
        return [scope_dict.get(s, s) for s in obj.usage_scope]


# Deal Serializers

class DealArtistSerializer(serializers.ModelSerializer):
    """Serializer for DealArtist (M2M)"""
    artist = EntityListSerializer(read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    contract_status_display = serializers.CharField(source='get_contract_status_display', read_only=True)

    class Meta:
        model = DealArtist
        fields = [
            'id', 'artist', 'role', 'role_display', 'artist_fee',
            'revenue_share_percent', 'contract_status', 'contract_status_display',
            'signed_date', 'created_at', 'updated_at'
        ]


class DealDeliverableSerializer(serializers.ModelSerializer):
    """Serializer for DealDeliverable"""
    deliverable_type_display = serializers.CharField(source='get_deliverable_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    approvals_count = serializers.SerializerMethodField()

    class Meta:
        model = DealDeliverable
        fields = [
            'id', 'deal', 'deliverable_type', 'deliverable_type_display', 'quantity',
            'description', 'due_date', 'status', 'status_display',
            'asset_url', 'kpi_target', 'kpi_actual', 'cost_center',
            'approvals_count', 'notes', 'created_at', 'updated_at'
        ]

    def get_approvals_count(self, obj):
        return obj.approvals.count()


class ApprovalSerializer(serializers.ModelSerializer):
    """Serializer for Approval"""
    deliverable = serializers.SerializerMethodField()
    approver_contact = ContactPersonSerializer(read_only=True)
    approver_user_name = serializers.SerializerMethodField()
    stage_display = serializers.CharField(source='get_stage_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Approval
        fields = [
            'id', 'deliverable', 'stage', 'stage_display', 'version',
            'submitted_at', 'approved_at', 'approver_contact', 'approver_user_name',
            'status', 'status_display', 'notes', 'file_url',
            'created_at', 'updated_at'
        ]

    def get_deliverable(self, obj):
        if obj.deliverable:
            return {
                'id': obj.deliverable.id,
                'deliverable_type': obj.deliverable.get_deliverable_type_display()
            }
        return None

    def get_approver_user_name(self, obj):
        return obj.approver_user.get_full_name() if obj.approver_user else None


class InvoiceSerializer(serializers.ModelSerializer):
    """Serializer for Invoice"""
    invoice_type_display = serializers.CharField(source='get_invoice_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'invoice_type', 'invoice_type_display',
            'issue_date', 'due_date', 'amount', 'currency',
            'status', 'status_display', 'paid_date', 'pdf_url',
            'is_overdue', 'notes', 'created_at', 'updated_at'
        ]

    def get_is_overdue(self, obj):
        if obj.status in ['issued', 'sent'] and obj.due_date:
            from django.utils import timezone
            return obj.due_date < timezone.now().date()
        return False


class DealListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for deal listings"""
    opportunity = serializers.SerializerMethodField()
    account = EntityListSerializer(read_only=True)
    created_by_name = serializers.SerializerMethodField()
    department_display = serializers.SerializerMethodField()
    deal_status_display = serializers.CharField(source='get_deal_status_display', read_only=True)
    payment_terms_display = serializers.CharField(source='get_payment_terms_display', read_only=True)
    artists_count = serializers.SerializerMethodField()
    deliverables_count = serializers.SerializerMethodField()

    class Meta:
        model = Deal
        fields = [
            'id', 'contract_number', 'po_number', 'deal_title',
            'opportunity', 'account', 'deal_status', 'deal_status_display',
            'fee_total', 'currency', 'payment_terms', 'payment_terms_display',
            'start_date', 'end_date', 'signed_date',
            'artists_count', 'deliverables_count',
            'department', 'department_display', 'created_by_name',
            'created_at', 'updated_at'
        ]

    def get_opportunity(self, obj):
        return {
            'id': obj.opportunity.id,
            'opp_name': obj.opportunity.opp_name
        }

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None

    def get_department_display(self, obj):
        return obj.department.name if obj.department else "Admin Only"

    def get_artists_count(self, obj):
        return obj.deal_artists.count()

    def get_deliverables_count(self, obj):
        return obj.deliverables.count()


class DealDetailSerializer(serializers.ModelSerializer):
    """Full serializer for deal details"""
    opportunity = OpportunityListSerializer(read_only=True)
    account = EntityListSerializer(read_only=True)
    deliverable_pack = DeliverablePackListSerializer(read_only=True)
    usage_terms = UsageTermsListSerializer(read_only=True)
    deal_artists = DealArtistSerializer(many=True, read_only=True)
    deliverables = DealDeliverableSerializer(many=True, read_only=True)
    approvals = ApprovalSerializer(many=True, read_only=True)
    invoices = InvoiceSerializer(many=True, read_only=True)
    created_by_name = serializers.SerializerMethodField()
    department_display = serializers.SerializerMethodField()
    deal_status_display = serializers.CharField(source='get_deal_status_display', read_only=True)
    payment_terms_display = serializers.CharField(source='get_payment_terms_display', read_only=True)

    class Meta:
        model = Deal
        fields = '__all__'

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None

    def get_department_display(self, obj):
        return obj.department.name if obj.department else "Admin Only"
