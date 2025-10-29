from django.contrib import admin
from .models import Campaign, CampaignHandler


class CampaignHandlerInline(admin.TabularInline):
    model = CampaignHandler
    extra = 1
    fields = ['user', 'role', 'assigned_at']
    readonly_fields = ['assigned_at']
    autocomplete_fields = ['user']


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = [
        'campaign_name',
        'client',
        'artist',
        'brand',
        'value',
        'status',
        'confirmed_at',
        'created_at',
    ]
    list_filter = ['status', 'created_at', 'confirmed_at']
    search_fields = [
        'campaign_name',
        'client__display_name',
        'artist__display_name',
        'brand__display_name',
        'notes',
    ]
    readonly_fields = ['created_at', 'updated_at', 'created_by']

    fieldsets = (
        ('Campaign Information', {
            'fields': ('campaign_name', 'value', 'status', 'confirmed_at')
        }),
        ('Relationships', {
            'fields': ('client', 'artist', 'brand')
        }),
        ('Additional Information', {
            'fields': ('notes',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    inlines = [CampaignHandlerInline]

    def save_model(self, request, obj, form, change):
        if not change:  # Only set created_by on creation
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
