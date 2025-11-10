"""
Django Admin for Artist Sales - Unified Opportunities System
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    Opportunity, OpportunityArtist, OpportunityTask, OpportunityActivity,
    OpportunityComment, OpportunityDeliverable, Approval, Invoice,
    DeliverablePack, DeliverablePackItem, UsageTerms
)


class OpportunityArtistInline(admin.TabularInline):
    model = OpportunityArtist
    extra = 0
    fields = ['artist', 'role', 'proposed_fee', 'confirmed_fee', 'contract_status']
    autocomplete_fields = ['artist']


class OpportunityTaskInline(admin.TabularInline):
    model = OpportunityTask
    extra = 0
    fields = ['title', 'task_type', 'assigned_to', 'due_date', 'priority', 'status']
    autocomplete_fields = ['assigned_to']


@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = [
        'opportunity_number', 'title', 'stage', 'account',
        'owner', 'team', 'estimated_value', 'probability',
        'priority', 'created_at'
    ]
    list_filter = ['stage', 'priority', 'team', 'currency']
    search_fields = ['opportunity_number', 'title', 'account__display_name']
    autocomplete_fields = ['account', 'contact_person', 'owner']
    readonly_fields = ['opportunity_number', 'contract_number', 'fee_net', 'probability', 'created_at', 'updated_at']
    inlines = [OpportunityArtistInline, OpportunityTaskInline]

    fieldsets = (
        ('Core', {
            'fields': ('opportunity_number', 'title', 'stage', 'priority', 'account', 'contact_person', 'owner', 'team')
        }),
        ('Financial', {
            'fields': ('estimated_value', 'currency', 'probability', 'expected_close_date')
        }),
        ('Brief', {
            'fields': ('campaign_objectives', 'target_audience', 'brand_category', 'budget_range_min', 'budget_range_max'),
            'classes': ('collapse',)
        }),
        ('Proposal', {
            'fields': ('fee_gross', 'discounts', 'agency_fee', 'fee_net'),
            'classes': ('collapse',)
        }),
        ('Contract', {
            'fields': ('contract_number', 'po_number', 'contract_file'),
            'classes': ('collapse',)
        }),
    )


@admin.register(OpportunityTask)
class OpportunityTaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'opportunity', 'assigned_to', 'due_date', 'status', 'priority']
    list_filter = ['status', 'priority', 'task_type']
    search_fields = ['title', 'opportunity__title']
    autocomplete_fields = ['opportunity', 'assigned_to']


@admin.register(OpportunityActivity)
class OpportunityActivityAdmin(admin.ModelAdmin):
    list_display = ['title', 'opportunity', 'activity_type', 'user', 'created_at']
    list_filter = ['activity_type']
    search_fields = ['title', 'opportunity__title']
    readonly_fields = ['created_at']


@admin.register(OpportunityComment)
class OpportunityCommentAdmin(admin.ModelAdmin):
    list_display = ['opportunity', 'user', 'is_internal', 'created_at']
    list_filter = ['is_internal']
    search_fields = ['comment', 'opportunity__title']


@admin.register(OpportunityDeliverable)
class OpportunityDeliverableAdmin(admin.ModelAdmin):
    list_display = ['deliverable_type', 'opportunity', 'quantity', 'due_date', 'status']
    list_filter = ['deliverable_type', 'status']
    search_fields = ['opportunity__title']


@admin.register(Approval)
class ApprovalAdmin(admin.ModelAdmin):
    list_display = ['stage', 'opportunity', 'status', 'submitted_at']
    list_filter = ['stage', 'status']
    search_fields = ['opportunity__title']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'opportunity', 'invoice_type', 'amount', 'status', 'due_date']
    list_filter = ['invoice_type', 'status']
    search_fields = ['invoice_number', 'opportunity__title']
    readonly_fields = ['invoice_number']


class DeliverablePackItemInline(admin.TabularInline):
    model = DeliverablePackItem
    extra = 1


@admin.register(DeliverablePack)
class DeliverablePackAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name']
    inlines = [DeliverablePackItemInline]


@admin.register(UsageTerms)
class UsageTermsAdmin(admin.ModelAdmin):
    list_display = ['name', 'usage_duration_days', 'buyout', 'is_template']
    list_filter = ['is_template', 'buyout']
    search_fields = ['name']
