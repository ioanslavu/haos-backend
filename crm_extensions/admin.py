from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.db.models import Count
from django.core.validators import MaxValueValidator
from .models import (
    Task, Activity, CampaignMetrics,
    FlowTrigger, ManualTrigger
)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'task_type',
        'status_badge',
        'priority_badge',
        'assigned_to',
        'campaign_link',
        'entity_link',
        'due_date',
        'is_overdue_badge',
        'created_at'
    ]

    list_filter = [
        'status',
        'priority',
        'task_type',
        'department',
        'created_at',
        'due_date',
        ('assigned_to', admin.RelatedOnlyFieldListFilter),
        ('created_by', admin.RelatedOnlyFieldListFilter),
    ]

    search_fields = [
        'title',
        'description',
        'notes',
        'campaign__campaign_name',
        'entity__display_name',
        'contract__title',
    ]

    readonly_fields = [
        'created_at',
        'updated_at',
        'started_at',
        'completed_at',
        'is_overdue',
        'is_blocked'
    ]

    fieldsets = (
        ('Task Information', {
            'fields': ('title', 'description', 'task_type', 'notes')
        }),
        ('Status & Priority', {
            'fields': ('status', 'priority', 'department')
        }),
        ('Associations', {
            'fields': ('campaign', 'entity', 'contract')
        }),
        ('Assignment', {
            'fields': ('assigned_to', 'created_by')
        }),
        ('Timeline', {
            'fields': ('due_date', 'reminder_date', 'started_at', 'completed_at', 'is_overdue')
        }),
        ('Dependencies', {
            'fields': ('parent_task', 'blocks_tasks', 'is_blocked'),
            'classes': ('collapse',)
        }),
        ('Time Tracking', {
            'fields': ('estimated_hours', 'actual_hours'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    autocomplete_fields = ['campaign', 'entity', 'contract', 'assigned_to', 'parent_task']

    def status_badge(self, obj):
        colors = {
            'todo': 'gray',
            'in_progress': 'blue',
            'blocked': 'red',
            'review': 'orange',
            'done': 'green',
            'cancelled': 'gray',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 7px; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'

    def priority_badge(self, obj):
        colors = {1: '#gray', 2: '#blue', 3: '#orange', 4: '#red'}
        color = colors.get(obj.priority, '#gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 7px; border-radius: 3px;">{}</span>',
            color, obj.get_priority_display()
        )
    priority_badge.short_description = 'Priority'
    priority_badge.admin_order_field = 'priority'

    def is_overdue_badge(self, obj):
        if obj.is_overdue:
            return format_html(
                '<span style="color: red; font-weight: bold;">⚠ Overdue</span>'
            )
        return '-'
    is_overdue_badge.short_description = 'Overdue'

    def campaign_link(self, obj):
        if obj.campaign:
            return format_html(
                '<a href="/admin/campaigns/campaign/{}/change/">{}</a>',
                obj.campaign.id, obj.campaign.campaign_name
            )
        return '-'
    campaign_link.short_description = 'Campaign'

    def entity_link(self, obj):
        if obj.entity:
            return format_html(
                '<a href="/admin/identity/entity/{}/change/">{}</a>',
                obj.entity.id, obj.entity.display_name
            )
        return '-'
    entity_link.short_description = 'Entity'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            'campaign', 'entity', 'contract',
            'assigned_to', 'created_by', 'department'
        )


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = [
        'subject',
        'type_badge',
        'entity_link',
        'campaign_link',
        'contact_person',
        'sentiment_badge',
        'activity_date',
        'created_by',
        'follow_up_required',
    ]

    list_filter = [
        'type',
        'sentiment',
        'direction',
        'follow_up_required',
        'follow_up_completed',
        'department',
        'activity_date',
        ('created_by', admin.RelatedOnlyFieldListFilter),
    ]

    search_fields = [
        'subject',
        'content',
        'entity__display_name',
        'campaign__campaign_name',
        'contact_person__name',
        'location',
    ]

    readonly_fields = [
        'created_at',
        'updated_at',
        'follow_up_task',
    ]

    fieldsets = (
        ('Activity Information', {
            'fields': ('type', 'subject', 'content', 'activity_date', 'duration_minutes', 'location')
        }),
        ('Associations', {
            'fields': ('entity', 'contact_person', 'campaign', 'contract', 'department')
        }),
        ('Communication Details', {
            'fields': ('direction', 'sentiment')
        }),
        ('Participants', {
            'fields': ('created_by', 'participants', 'external_participants')
        }),
        ('Follow-up', {
            'fields': ('follow_up_required', 'follow_up_date', 'follow_up_completed', 'follow_up_task')
        }),
        ('Attachments & Links', {
            'fields': ('attachments', 'related_url'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    autocomplete_fields = ['entity', 'contact_person', 'campaign', 'contract', 'created_by']
    filter_horizontal = ['participants']

    def type_badge(self, obj):
        icons = {
            'email': '✉',
            'call': '📞',
            'meeting': '🤝',
            'video_call': '📹',
            'note': '📝',
            'follow_up': '🔔',
            'task_created': '✅',
            'status_change': '🔄',
            'document': '📄',
            'social_media': '💬',
            'event': '🎤',
            'negotiation': '💰',
        }
        icon = icons.get(obj.type, '📌')
        return format_html(
            '{} {}',
            icon, obj.get_type_display()
        )
    type_badge.short_description = 'Type'
    type_badge.admin_order_field = 'type'

    def sentiment_badge(self, obj):
        if not obj.sentiment:
            return '-'

        colors = {
            'very_positive': 'green',
            'positive': 'lightgreen',
            'neutral': 'gray',
            'negative': 'orange',
            'very_negative': 'red',
        }
        color = colors.get(obj.sentiment, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 7px; border-radius: 3px;">{}</span>',
            color, obj.get_sentiment_display()
        )
    sentiment_badge.short_description = 'Sentiment'

    def entity_link(self, obj):
        if obj.entity:
            return format_html(
                '<a href="/admin/identity/entity/{}/change/">{}</a>',
                obj.entity.id, obj.entity.display_name
            )
        return '-'
    entity_link.short_description = 'Entity'

    def campaign_link(self, obj):
        if obj.campaign:
            return format_html(
                '<a href="/admin/campaigns/campaign/{}/change/">{}</a>',
                obj.campaign.id, obj.campaign.campaign_name
            )
        return '-'
    campaign_link.short_description = 'Campaign'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            'entity', 'contact_person', 'campaign',
            'contract', 'created_by', 'department', 'follow_up_task'
        ).prefetch_related('participants')

    actions = ['create_follow_up_tasks']

    def create_follow_up_tasks(self, request, queryset):
        created_count = 0
        for activity in queryset.filter(follow_up_required=True, follow_up_task__isnull=True):
            task = activity.create_follow_up_task()
            if task:
                created_count += 1

        self.message_user(request, f"Created {created_count} follow-up task(s).")
    create_follow_up_tasks.short_description = "Create follow-up tasks for selected activities"


@admin.register(CampaignMetrics)
class CampaignMetricsAdmin(admin.ModelAdmin):
    list_display = [
        'campaign',
        'recorded_date',
        'source',
        'impressions',
        'clicks',
        'ctr',
        'conversions',
        'cost',
        'roi',
    ]

    list_filter = [
        'recorded_date',
        'source',
        ('campaign', admin.RelatedOnlyFieldListFilter),
    ]

    search_fields = [
        'campaign__campaign_name',
        'source',
    ]

    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Campaign & Date', {
            'fields': ('campaign', 'recorded_date', 'source')
        }),
        ('Performance Metrics', {
            'fields': (
                ('impressions', 'clicks', 'ctr'),
                ('conversions', 'conversion_rate'),
                ('cost', 'cpc', 'cpa'),
            )
        }),
        ('Social Media Metrics', {
            'fields': (
                ('reach', 'engagement', 'engagement_rate'),
                ('followers_gained', 'followers_lost'),
            ),
            'classes': ('collapse',)
        }),
        ('Content Metrics', {
            'fields': (
                ('views', 'watch_time_minutes'),
                ('shares', 'comments', 'likes'),
            ),
            'classes': ('collapse',)
        }),
        ('Music Metrics', {
            'fields': (
                ('streams', 'downloads'),
                ('playlist_adds', 'radio_plays'),
            ),
            'classes': ('collapse',)
        }),
        ('Revenue Metrics', {
            'fields': ('revenue', 'roi'),
        }),
        ('Custom Metrics', {
            'fields': ('custom_metrics',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    autocomplete_fields = ['campaign']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('campaign')


@admin.register(FlowTrigger)
class FlowTriggerAdmin(admin.ModelAdmin):
    list_display = ['name', 'trigger_entity_type', 'trigger_event', 'creates_task', 'is_active']
    list_filter = ['trigger_entity_type', 'trigger_event', 'is_active', 'creates_task']
    search_fields = ['name', 'description', 'trigger_entity_type']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Trigger Information', {
            'fields': ('name', 'description')
        }),
        ('Trigger Configuration', {
            'fields': ('trigger_entity_type', 'trigger_event', 'trigger_conditions')
        }),
        ('Task Creation', {
            'fields': ('creates_task', 'task_config')
        }),
        ('Configuration', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(ManualTrigger)
class ManualTriggerAdmin(admin.ModelAdmin):
    list_display = ['button_label', 'entity_type', 'context', 'action_type', 'button_style', 'is_active']
    list_filter = ['entity_type', 'action_type', 'button_style', 'is_active']
    search_fields = ['name', 'button_label', 'entity_type', 'context']
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = ['visible_to_departments']

    fieldsets = (
        ('Trigger Information', {
            'fields': ('name', 'button_label', 'button_style')
        }),
        ('Context', {
            'fields': ('entity_type', 'context')
        }),
        ('Action Configuration', {
            'fields': ('action_type', 'action_config')
        }),
        ('Permissions', {
            'fields': ('visible_to_departments', 'required_permissions')
        }),
        ('Configuration', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )