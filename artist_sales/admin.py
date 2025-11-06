from django.contrib import admin
from .models import (
    Brief, Opportunity, Proposal, ProposalArtist,
    DeliverablePack, DeliverablePackItem, UsageTerms,
    Deal, DealArtist, DealDeliverable, Approval, Invoice
)


# Inline classes

class ProposalArtistInline(admin.TabularInline):
    model = ProposalArtist
    extra = 1
    fields = ['artist', 'role', 'proposed_fee']
    autocomplete_fields = ['artist']


class DealArtistInline(admin.TabularInline):
    model = DealArtist
    extra = 1
    fields = ['artist', 'role', 'artist_fee', 'revenue_share_percent', 'contract_status', 'signed_date']
    autocomplete_fields = ['artist']


class DealDeliverableInline(admin.TabularInline):
    model = DealDeliverable
    extra = 1
    fields = ['deliverable_type', 'quantity', 'due_date', 'status']


class ApprovalInline(admin.TabularInline):
    model = Approval
    extra = 0
    fields = ['stage', 'version', 'status', 'submitted_at', 'approved_at']
    readonly_fields = ['submitted_at', 'approved_at']


class InvoiceInline(admin.TabularInline):
    model = Invoice
    extra = 0
    fields = ['invoice_number', 'invoice_type', 'amount', 'status', 'due_date']
    readonly_fields = ['invoice_number']


class DeliverablePackItemInline(admin.TabularInline):
    model = DeliverablePackItem
    extra = 1
    fields = ['deliverable_type', 'quantity', 'description']


# Model admins

@admin.register(Brief)
class BriefAdmin(admin.ModelAdmin):
    list_display = [
        'campaign_title',
        'account',
        'brand_category',
        'brief_status',
        'received_date',
        'sla_due_date',
        'created_at',
    ]
    list_filter = ['brief_status', 'brand_category', 'received_date', 'sla_due_date']
    search_fields = ['campaign_title', 'account__display_name', 'objectives', 'notes']
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'received_date']
    autocomplete_fields = ['account', 'contact_person']

    fieldsets = (
        ('Brief Information', {
            'fields': ('campaign_title', 'account', 'contact_person', 'brand_category', 'brief_status')
        }),
        ('Campaign Details', {
            'fields': ('objectives', 'target_audience', 'channels', 'must_haves', 'nice_to_have')
        }),
        ('Timeline & Budget', {
            'fields': ('timing_start', 'timing_end', 'budget_range_min', 'budget_range_max', 'currency')
        }),
        ('SLA & Dates', {
            'fields': ('received_date', 'sla_due_date')
        }),
        ('Department & Ownership', {
            'fields': ('department', 'created_by')
        }),
        ('Metadata', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = [
        'opp_name',
        'account',
        'stage',
        'amount_expected',
        'probability_percent',
        'expected_close_date',
        'owner_user',
        'created_at',
    ]
    list_filter = ['stage', 'expected_close_date', 'created_at']
    search_fields = ['opp_name', 'account__display_name', 'next_step', 'notes']
    readonly_fields = ['created_at', 'updated_at', 'created_by']
    autocomplete_fields = ['brief', 'account', 'owner_user']

    fieldsets = (
        ('Opportunity Information', {
            'fields': ('opp_name', 'brief', 'account', 'stage')
        }),
        ('Financial', {
            'fields': ('amount_expected', 'currency', 'probability_percent')
        }),
        ('Timeline', {
            'fields': ('expected_close_date', 'actual_close_date')
        }),
        ('Pipeline Management', {
            'fields': ('next_step', 'lost_reason')
        }),
        ('Ownership', {
            'fields': ('owner_user', 'department', 'created_by')
        }),
        ('Metadata', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Proposal)
class ProposalAdmin(admin.ModelAdmin):
    list_display = [
        'opportunity',
        'version',
        'proposal_status',
        'fee_net',
        'currency',
        'sent_date',
        'valid_until',
        'created_at',
    ]
    list_filter = ['proposal_status', 'sent_date', 'created_at']
    search_fields = ['opportunity__opp_name', 'notes']
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'fee_net']
    autocomplete_fields = ['opportunity']
    inlines = [ProposalArtistInline]

    fieldsets = (
        ('Proposal Information', {
            'fields': ('opportunity', 'version', 'proposal_status')
        }),
        ('Pricing', {
            'fields': ('fee_gross', 'discounts', 'agency_fee', 'fee_net', 'currency')
        }),
        ('Dates', {
            'fields': ('sent_date', 'valid_until')
        }),
        ('Metadata', {
            'fields': ('notes', 'created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(DeliverablePack)
class DeliverablePackAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at', 'updated_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    inlines = [DeliverablePackItemInline]

    fieldsets = (
        ('Pack Information', {
            'fields': ('name', 'description', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(UsageTerms)
class UsageTermsAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'usage_duration_days',
        'exclusivity_category',
        'buyout',
        'is_template',
        'created_at',
    ]
    list_filter = ['is_template', 'buyout', 'extensions_allowed', 'created_at']
    search_fields = ['name', 'notes']

    fieldsets = (
        ('Terms Information', {
            'fields': ('name', 'is_template')
        }),
        ('Usage Rights', {
            'fields': ('usage_scope', 'territories', 'usage_duration_days', 'extensions_allowed', 'buyout')
        }),
        ('Exclusivity', {
            'fields': ('exclusivity_category', 'exclusivity_duration_days', 'brand_list_blocked')
        }),
        ('Metadata', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = [
        'contract_number',
        'deal_title',
        'account',
        'deal_status',
        'fee_total',
        'start_date',
        'end_date',
        'created_at',
    ]
    list_filter = ['deal_status', 'payment_terms', 'start_date', 'end_date', 'created_at']
    search_fields = ['contract_number', 'po_number', 'deal_title', 'account__display_name', 'notes']
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'contract_number']
    autocomplete_fields = ['opportunity', 'account', 'deliverable_pack', 'usage_terms']
    inlines = [DealArtistInline, DealDeliverableInline, ApprovalInline, InvoiceInline]

    fieldsets = (
        ('Deal Information', {
            'fields': ('contract_number', 'po_number', 'deal_title', 'opportunity', 'account', 'deal_status')
        }),
        ('Financial', {
            'fields': ('fee_total', 'currency', 'payment_terms')
        }),
        ('Timeline', {
            'fields': ('start_date', 'end_date', 'signed_date')
        }),
        ('Deliverables & Rights', {
            'fields': ('deliverable_pack', 'usage_terms')
        }),
        ('Brand Safety', {
            'fields': ('brand_safety_score',)
        }),
        ('Files', {
            'fields': ('contract_file',)
        }),
        ('Department & Ownership', {
            'fields': ('department', 'created_by')
        }),
        ('Metadata', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(DealDeliverable)
class DealDeliverableAdmin(admin.ModelAdmin):
    list_display = [
        'deal',
        'deliverable_type',
        'quantity',
        'status',
        'due_date',
        'created_at',
    ]
    list_filter = ['status', 'deliverable_type', 'due_date', 'created_at']
    search_fields = ['deal__deal_title', 'description', 'notes']
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['deal']


@admin.register(Approval)
class ApprovalAdmin(admin.ModelAdmin):
    list_display = [
        'deal',
        'stage',
        'version',
        'status',
        'submitted_at',
        'approved_at',
    ]
    list_filter = ['status', 'stage', 'submitted_at', 'approved_at']
    search_fields = ['deal__deal_title', 'notes']
    readonly_fields = ['submitted_at', 'approved_at', 'created_at', 'updated_at']
    autocomplete_fields = ['deal', 'deliverable', 'approver_contact', 'approver_user']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = [
        'invoice_number',
        'deal',
        'invoice_type',
        'amount',
        'status',
        'issue_date',
        'due_date',
        'paid_date',
    ]
    list_filter = ['status', 'invoice_type', 'issue_date', 'due_date', 'created_at']
    search_fields = ['invoice_number', 'deal__deal_title', 'notes']
    readonly_fields = ['invoice_number', 'created_at', 'updated_at']
    autocomplete_fields = ['deal']

    fieldsets = (
        ('Invoice Information', {
            'fields': ('invoice_number', 'deal', 'invoice_type', 'status')
        }),
        ('Financial', {
            'fields': ('amount', 'currency')
        }),
        ('Dates', {
            'fields': ('issue_date', 'due_date', 'paid_date')
        }),
        ('Files', {
            'fields': ('pdf_url',)
        }),
        ('Metadata', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
