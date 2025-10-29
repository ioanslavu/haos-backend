from django.contrib import admin
from django.utils.html import format_html
from django import forms
from .models import (
    ContractTemplate, ContractTemplateVersion, Contract, ContractSignature,
    ContractScope, ContractRate, ShareType, ContractShare
)


class ContractScopeInline(admin.TabularInline):
    model = ContractScope
    extra = 0
    fields = ['work', 'recording', 'release', 'all_in_term', 'include_derivatives', 'notes']
    autocomplete_fields = ['work', 'recording', 'release']


class ContractRateInline(admin.TabularInline):
    model = ContractRate
    extra = 0
    fields = ['right_type', 'channel', 'percent', 'base', 'minimum_rate', 'producer_points_default', 'notes']


@admin.register(ContractTemplate)
class ContractTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_by', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_by', 'created_at', 'updated_at']


@admin.register(ContractTemplateVersion)
class ContractTemplateVersionAdmin(admin.ModelAdmin):
    list_display = ['template', 'version_number', 'created_by', 'created_at']
    list_filter = ['template', 'created_at']
    search_fields = ['template__name', 'change_description']
    readonly_fields = ['created_by', 'created_at']


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ['contract_number', 'title', 'label_entity', 'template', 'status',
                    'term_start', 'term_end', 'created_by', 'created_at']
    list_filter = ['status', 'template', 'term_start', 'created_at']
    search_fields = ['contract_number', 'title', 'label_entity__display_name', 'counterparty_entity__display_name']
    autocomplete_fields = ['label_entity', 'counterparty_entity', 'created_by']
    readonly_fields = ['contract_number', 'created_by', 'created_at', 'updated_at',
                       'signed_at', 'get_scopes_display', 'get_rates_display']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Basic Information', {
            'fields': ('contract_number', 'title', 'label_entity', 'counterparty_entity', 'template')
        }),
        ('Contract Details', {
            'fields': ('status', 'contract_type', 'term_start', 'term_end', 'territory', 'advance')
        }),
        ('Content & Documents', {
            'fields': ('gdrive_file_id', 'gdrive_file_url', 'gdrive_pdf_file_id', 'gdrive_pdf_file_url'),
            'classes': ('collapse',)
        }),
        ('Scopes & Rates', {
            'fields': ('get_scopes_display', 'get_rates_display'),
            'classes': ('collapse',)
        }),
        ('Signature Information', {
            'fields': ('dropbox_sign_request_id', 'signed_at'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    inlines = [ContractScopeInline, ContractRateInline]

    def get_scopes_display(self, obj):
        """Display contract scopes in a formatted way."""
        scopes = obj.scopes.all()
        if not scopes:
            return 'No scopes defined'

        html = '<ul style="margin: 0; padding-left: 20px;">'
        for scope in scopes:
            scope_text = ""
            if scope.work:
                scope_text += f"Work: {scope.work.title}"
            elif scope.recording:
                scope_text += f"Recording: {scope.recording.title}"
            elif scope.release:
                scope_text += f"Release: {scope.release.title}"
            else:
                scope_text += "All"

            if scope.all_in_term:
                scope_text += " [All in term]"
            if scope.include_derivatives:
                scope_text += " [Include derivatives]"

            html += f'<li>{scope_text}</li>'
        html += '</ul>'
        return format_html(html)
    get_scopes_display.short_description = 'Contract Scopes'

    def get_rates_display(self, obj):
        """Display contract rates in a formatted way."""
        rates = obj.rates.all()
        if not rates:
            return 'No rates defined'

        html = '<ul style="margin: 0; padding-left: 20px;">'
        for rate in rates:
            rate_text = f"{rate.get_right_type_display()}: {rate.percent}% of {rate.get_base_display()}"
            if rate.channel:
                rate_text += f" ({rate.get_channel_display()})"
            if rate.minimum_rate:
                rate_text += f" [Min: ${rate.minimum_rate}]"
            html += f'<li>{rate_text}</li>'
        html += '</ul>'
        return format_html(html)
    get_rates_display.short_description = 'Contract Rates'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('label_entity', 'counterparty_entity', 'template', 'created_by').prefetch_related('scopes', 'rates')


@admin.register(ContractSignature)
class ContractSignatureAdmin(admin.ModelAdmin):
    list_display = ['contract', 'signer_email', 'signer_name', 'status', 'signed_at']
    list_filter = ['status', 'created_at']
    search_fields = ['signer_email', 'signer_name', 'contract__contract_number']
    readonly_fields = ['dropbox_sign_signature_id', 'sent_at', 'viewed_at', 'signed_at', 'declined_at', 'created_at', 'updated_at']
    autocomplete_fields = ['contract']

    fieldsets = (
        ('Contract', {
            'fields': ('contract',)
        }),
        ('Signer Information', {
            'fields': ('signer_email', 'signer_name', 'signer_role')
        }),
        ('Signature Status', {
            'fields': ('status', 'dropbox_sign_signature_id', 'sent_at', 'viewed_at', 'signed_at', 'declined_at')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ContractScope)
class ContractScopeAdmin(admin.ModelAdmin):
    list_display = ['contract', 'get_scope_object', 'all_in_term', 'include_derivatives', 'created_at']
    list_filter = ['all_in_term', 'include_derivatives', 'created_at']
    search_fields = ['contract__contract_number', 'contract__title', 'work__title', 'recording__title', 'release__title']
    autocomplete_fields = ['contract', 'work', 'recording', 'release']
    readonly_fields = ['created_at', 'updated_at', 'get_scope_object']

    fieldsets = (
        ('Contract', {
            'fields': ('contract',)
        }),
        ('Scope Definition', {
            'fields': ('work', 'recording', 'release', 'get_scope_object')
        }),
        ('Terms', {
            'fields': ('all_in_term', 'include_derivatives', 'notes')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_scope_object(self, obj):
        """Display the scope object with a link."""
        if obj.work:
            return format_html('<a href="/admin/catalog/work/{}/change/">{}</a>',
                               obj.work.id, obj.work.title)
        elif obj.recording:
            return format_html('<a href="/admin/catalog/recording/{}/change/">{}</a>',
                               obj.recording.id, obj.recording.title)
        elif obj.release:
            return format_html('<a href="/admin/catalog/release/{}/change/">{}</a>',
                               obj.release.id, obj.release.title)
        return 'All'
    get_scope_object.short_description = 'Scope Object'


@admin.register(ContractRate)
class ContractRateAdmin(admin.ModelAdmin):
    list_display = ['contract', 'right_type', 'percent', 'channel', 'base', 'created_at']
    list_filter = ['right_type', 'channel', 'base', 'created_at']
    search_fields = ['contract__contract_number', 'contract__title', 'notes']
    autocomplete_fields = ['contract']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Contract', {
            'fields': ('contract',)
        }),
        ('Rate Information', {
            'fields': ('right_type', 'channel', 'percent', 'base', 'minimum_rate', 'producer_points_default')
        }),
        ('Escalation', {
            'fields': ('escalation_clause',)
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ShareType)
class ShareTypeAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'get_contract_types_display', 'created_at']
    list_filter = ['created_at']
    search_fields = ['code', 'name', 'description']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'name', 'description')
        }),
        ('Configuration', {
            'fields': ('placeholder_keys', 'contract_types')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_contract_types_display(self, obj):
        """Display contract types as comma-separated list."""
        if not obj.contract_types:
            return 'All types'
        return ', '.join(obj.contract_types)
    get_contract_types_display.short_description = 'Contract Types'


class ContractShareInline(admin.TabularInline):
    model = ContractShare
    extra = 0
    fields = ['share_type', 'value', 'unit', 'valid_from', 'valid_to']
    autocomplete_fields = ['share_type']
    readonly_fields = ['created_at']


@admin.register(ContractShare)
class ContractShareAdmin(admin.ModelAdmin):
    list_display = ['contract', 'share_type', 'value', 'unit', 'valid_from', 'valid_to', 'created_at']
    list_filter = ['unit', 'share_type', 'created_at']
    search_fields = ['contract__contract_number', 'contract__title', 'share_type__name', 'share_type__code']
    autocomplete_fields = ['contract', 'share_type']
    readonly_fields = ['created_at', 'updated_at', 'get_placeholder_display']
    date_hierarchy = 'valid_from'

    fieldsets = (
        ('Contract', {
            'fields': ('contract',)
        }),
        ('Share Information', {
            'fields': ('share_type', 'value', 'unit')
        }),
        ('Validity Period', {
            'fields': ('valid_from', 'valid_to')
        }),
        ('Placeholders', {
            'fields': ('get_placeholder_display',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_placeholder_display(self, obj):
        """Display the generated placeholders for this share."""
        placeholders = obj.get_placeholder_values()
        if not placeholders:
            return 'No placeholders'

        html = '<table style="width: 100%; border-collapse: collapse;">'
        html += '<tr style="background: #f5f5f5;"><th style="padding: 8px; text-align: left; border: 1px solid #ddd;">Placeholder</th><th style="padding: 8px; text-align: left; border: 1px solid #ddd;">Value</th></tr>'
        for key, value in placeholders.items():
            html += f'<tr><td style="padding: 8px; border: 1px solid #ddd;"><code>{{{{{key}}}}}</code></td><td style="padding: 8px; border: 1px solid #ddd;">{value}</td></tr>'
        html += '</table>'
        return format_html(html)
    get_placeholder_display.short_description = 'Generated Placeholders'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('contract', 'share_type')
