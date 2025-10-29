from django.contrib import admin
from django.utils.html import format_html
from django import forms
from .models import Publication, PublicationReport


class PublicationAdminForm(forms.ModelForm):
    class Meta:
        model = Publication
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        # Model's clean method will handle the validation
        return cleaned_data


@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    form = PublicationAdminForm
    list_display = ['get_object_display', 'platform_with_icon', 'territory', 'status',
                    'channel', 'is_monetized', 'published_at', 'is_active', 'created_at']
    list_filter = ['object_type', 'platform', 'status', 'territory', 'channel',
                   'is_monetized', 'published_at', 'created_at']
    search_fields = ['url', 'external_id', 'owner_account', 'distributor', 'notes']
    readonly_fields = ['created_at', 'updated_at', 'get_object_display', 'platform_icon',
                       'is_active', 'last_metrics_update', 'get_metrics_display']
    date_hierarchy = 'published_at'

    fieldsets = (
        ('Object', {
            'fields': ('object_type', 'object_id', 'get_object_display')
        }),
        ('Platform Information', {
            'fields': ('platform', 'platform_icon', 'url', 'external_id', 'content_id')
        }),
        ('Territory & Availability', {
            'fields': ('territory', 'status')
        }),
        ('Publishing Details', {
            'fields': ('published_at', 'scheduled_for', 'taken_down_at', 'is_active')
        }),
        ('Distribution', {
            'fields': ('channel', 'is_monetized', 'owner_account', 'distributor')
        }),
        ('Metrics', {
            'fields': ('get_metrics_display', 'last_metrics_update'),
            'classes': ('collapse',)
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

    def get_object_display(self, obj):
        if obj.object_type == 'recording':
            recording = obj.get_recording
            if recording:
                return format_html('<a href="/admin/catalog/recording/{}/change/">Recording: {}</a>',
                                   recording.id, recording.title)
        elif obj.object_type == 'release':
            release = obj.get_release
            if release:
                return format_html('<a href="/admin/catalog/release/{}/change/">Release: {}</a>',
                                   release.id, release.title)
        return f"{obj.object_type} #{obj.object_id}"
    get_object_display.short_description = 'Object'

    def platform_with_icon(self, obj):
        return format_html('{} {}', obj.platform_icon, obj.get_platform_display())
    platform_with_icon.short_description = 'Platform'

    def get_metrics_display(self, obj):
        """Display metrics in a formatted way."""
        if not obj.metrics:
            return 'No metrics available'

        html = '<div style="font-family: monospace;">'
        for key, value in obj.metrics.items():
            html += f'{key}: {value:,}<br>' if isinstance(value, (int, float)) else f'{key}: {value}<br>'
        html += '</div>'
        return format_html(html)
    get_metrics_display.short_description = 'Metrics'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related()


# Admin actions
@admin.action(description='Mark as Live')
def mark_as_live(modeladmin, request, queryset):
    """Mark selected publications as live."""
    from django.utils import timezone
    updated = queryset.update(
        status='live',
        published_at=timezone.now()
    )
    modeladmin.message_user(request, f'{updated} publication(s) marked as live.')


@admin.action(description='Mark as Taken Down')
def mark_as_taken_down(modeladmin, request, queryset):
    """Mark selected publications as taken down."""
    from django.utils import timezone
    updated = queryset.update(
        status='taken_down',
        taken_down_at=timezone.now()
    )
    modeladmin.message_user(request, f'{updated} publication(s) marked as taken down.')


@admin.action(description='Generate Coverage Report')
def generate_coverage_report(modeladmin, request, queryset):
    """Generate coverage report for selected publications."""
    from django.contrib import messages
    import json

    reports = {}
    for pub in queryset:
        key = f"{pub.object_type}_{pub.object_id}"
        if key not in reports:
            reports[key] = PublicationReport.get_coverage_report(pub.object_type, pub.object_id)

    if reports:
        message = "Coverage Reports:\n"
        for key, report in reports.items():
            obj_type, obj_id = key.split('_')
            message += f"\n{obj_type.title()} #{obj_id}:\n"
            message += f"  • Coverage: {report['coverage_percentage']:.1f}%\n"
            message += f"  • Platforms: {report['covered_count']}/{report['total_platforms']}\n"
            message += f"  • Missing: {', '.join(report['missing_platforms'][:5])}"
            if len(report['missing_platforms']) > 5:
                message += f" (+{len(report['missing_platforms']) - 5} more)"
            message += "\n"

        messages.info(request, message)


@admin.action(description='Update Metrics')
def update_metrics(modeladmin, request, queryset):
    """Placeholder action for updating metrics from platform APIs."""
    from django.contrib import messages

    # In production, this would call platform APIs to get latest metrics
    messages.info(request, 'Metrics update functionality not yet implemented. '
                          'This would fetch latest metrics from platform APIs.')


# Add actions to the admin
PublicationAdmin.actions = [mark_as_live, mark_as_taken_down,
                             generate_coverage_report, update_metrics]


# Optional: Register a proxy model for territory reporting
class TerritoryReport(Publication):
    class Meta:
        proxy = True
        verbose_name = 'Territory Report'
        verbose_name_plural = 'Territory Reports'


@admin.register(TerritoryReport)
class TerritoryReportAdmin(admin.ModelAdmin):
    change_list_template = 'admin/distribution/territory_report.html'

    def changelist_view(self, request, extra_context=None):
        """Custom view for territory reporting."""
        from django.db.models import Count

        # Get territory statistics
        territory_stats = Publication.objects.values('territory').annotate(
            count=Count('id')
        ).order_by('-count')

        # Get platform distribution by territory
        platform_by_territory = {}
        for territory in territory_stats[:10]:  # Top 10 territories
            platform_stats = Publication.objects.filter(
                territory=territory['territory']
            ).values('platform').annotate(
                count=Count('id')
            ).order_by('-count')[:5]  # Top 5 platforms
            platform_by_territory[territory['territory']] = list(platform_stats)

        extra_context = extra_context or {}
        extra_context.update({
            'territory_stats': territory_stats,
            'platform_by_territory': platform_by_territory,
            'total_publications': Publication.objects.count(),
            'live_count': Publication.objects.filter(status='live').count(),
        })

        return super().changelist_view(request, extra_context=extra_context)