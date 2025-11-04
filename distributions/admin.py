from django.contrib import admin
from .models import Distribution, DistributionCatalogItem, DistributionRevenueReport


class DistributionCatalogItemInline(admin.TabularInline):
    """Inline view of catalog items in Distribution admin"""
    model = DistributionCatalogItem
    extra = 0
    fields = ['recording', 'release', 'platforms', 'individual_revenue_share', 'distribution_status', 'release_date']
    autocomplete_fields = ['recording', 'release']


class DistributionRevenueReportInline(admin.TabularInline):
    """Inline view of revenue reports in DistributionCatalogItem admin"""
    model = DistributionRevenueReport
    extra = 0
    fields = ['platform', 'reporting_period', 'revenue_amount', 'currency', 'streams', 'downloads']


@admin.register(Distribution)
class DistributionAdmin(admin.ModelAdmin):
    """Admin interface for Distribution model"""
    list_display = ['entity', 'deal_type', 'deal_status', 'global_revenue_share_percentage',
                    'signing_date', 'department', 'created_at']
    list_filter = ['deal_type', 'deal_status', 'department', 'signing_date']
    search_fields = ['entity__display_name', 'notes', 'special_terms']
    autocomplete_fields = ['entity', 'contract', 'contact_person']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'updated_at', 'track_count', 'total_revenue']
    inlines = [DistributionCatalogItemInline]

    def track_count(self, obj):
        """Return the count of catalog items for this distribution"""
        return obj.catalog_items.count()
    track_count.short_description = 'Track Count'

    def total_revenue(self, obj):
        """Return the total revenue across all catalog items for this distribution"""
        from decimal import Decimal
        total = Decimal('0.00')
        for catalog_item in obj.catalog_items.all():
            total += catalog_item.total_revenue
        return f"{total} EUR"
    total_revenue.short_description = 'Total Revenue'

    fieldsets = (
        ('Basic Information', {
            'fields': ('entity', 'deal_type', 'deal_status', 'department')
        }),
        ('Financial Terms', {
            'fields': ('global_revenue_share_percentage', 'signing_date', 'contract')
        }),
        ('Contact & Notes', {
            'fields': ('contact_person', 'notes', 'special_terms')
        }),
        ('Computed Fields', {
            'fields': ('track_count', 'total_revenue'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(DistributionCatalogItem)
class DistributionCatalogItemAdmin(admin.ModelAdmin):
    """Admin interface for DistributionCatalogItem model"""
    list_display = ['distribution', 'catalog_item_title', 'catalog_item_type',
                    'distribution_status', 'effective_revenue_share', 'total_revenue', 'added_at']
    list_filter = ['distribution_status', 'platforms', 'added_at']
    search_fields = ['recording__title', 'release__title', 'notes']
    autocomplete_fields = ['distribution', 'recording', 'release']
    date_hierarchy = 'added_at'
    readonly_fields = ['added_at', 'catalog_item_title', 'catalog_item_type',
                       'effective_revenue_share', 'total_revenue']
    inlines = [DistributionRevenueReportInline]

    fieldsets = (
        ('Distribution', {
            'fields': ('distribution',)
        }),
        ('Catalog Item', {
            'fields': ('recording', 'release'),
            'description': 'Select either a recording OR a release (not both)'
        }),
        ('Distribution Settings', {
            'fields': ('platforms', 'individual_revenue_share', 'distribution_status', 'release_date')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Computed Fields', {
            'fields': ('catalog_item_title', 'catalog_item_type', 'effective_revenue_share', 'total_revenue'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('added_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(DistributionRevenueReport)
class DistributionRevenueReportAdmin(admin.ModelAdmin):
    """Admin interface for DistributionRevenueReport model"""
    list_display = ['catalog_item', 'platform', 'reporting_period', 'revenue_amount',
                    'currency', 'streams', 'downloads', 'created_at']
    list_filter = ['platform', 'reporting_period', 'currency', 'created_at']
    search_fields = ['catalog_item__recording__title', 'catalog_item__release__title', 'notes']
    autocomplete_fields = ['catalog_item']
    date_hierarchy = 'reporting_period'
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Catalog Item', {
            'fields': ('catalog_item',)
        }),
        ('Platform & Period', {
            'fields': ('platform', 'reporting_period')
        }),
        ('Revenue Data', {
            'fields': ('revenue_amount', 'currency')
        }),
        ('Engagement Metrics', {
            'fields': ('streams', 'downloads'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
