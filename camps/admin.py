from django.contrib import admin
from .models import Camp, CampStudio, CampStudioArtist


class CampStudioArtistInline(admin.TabularInline):
    """Inline admin for studio artists"""
    model = CampStudioArtist
    extra = 1
    autocomplete_fields = ['artist']
    fields = ['artist', 'is_internal']


class CampStudioInline(admin.StackedInline):
    """Inline admin for studios within camps"""
    model = CampStudio
    extra = 0
    fields = ['name', 'location', 'city', 'country', 'hours', 'sessions', 'order']
    show_change_link = True


@admin.register(Camp)
class CampAdmin(admin.ModelAdmin):
    """Admin interface for Camp model"""
    list_display = ['name', 'start_date', 'end_date', 'status', 'studios_count', 'department', 'created_by', 'created_at', 'is_deleted']
    list_filter = ['status', 'department', 'deleted_at', 'start_date']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'studios_count']
    inlines = [CampStudioInline]
    date_hierarchy = 'start_date'

    fieldsets = [
        ('Basic Information', {
            'fields': ['name', 'start_date', 'end_date', 'status']
        }),
        ('Metadata', {
            'fields': ['department', 'created_by', 'created_at', 'updated_at']
        }),
        ('Soft Delete', {
            'fields': ['deleted_at'],
            'classes': ['collapse']
        }),
    ]

    def save_model(self, request, obj, form, change):
        if not change:  # If creating new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def is_deleted(self, obj):
        return obj.is_deleted
    is_deleted.boolean = True
    is_deleted.short_description = 'Deleted'


@admin.register(CampStudio)
class CampStudioAdmin(admin.ModelAdmin):
    """Admin interface for CampStudio model"""
    list_display = ['name', 'camp', 'location', 'city', 'country', 'hours', 'sessions', 'order']
    list_filter = ['camp', 'country']
    search_fields = ['name', 'location', 'city']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [CampStudioArtistInline]

    fieldsets = [
        ('Basic Information', {
            'fields': ['camp', 'name', 'order']
        }),
        ('Location', {
            'fields': ['location', 'city', 'country']
        }),
        ('Schedule', {
            'fields': ['hours', 'sessions']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]


@admin.register(CampStudioArtist)
class CampStudioArtistAdmin(admin.ModelAdmin):
    """Admin interface for CampStudioArtist model"""
    list_display = ['studio', 'artist', 'is_internal', 'created_at']
    list_filter = ['is_internal', 'studio__camp']
    search_fields = ['artist__display_name', 'studio__name']
    autocomplete_fields = ['artist']
    readonly_fields = ['created_at']

    fieldsets = [
        (None, {
            'fields': ['studio', 'artist', 'is_internal', 'created_at']
        }),
    ]
