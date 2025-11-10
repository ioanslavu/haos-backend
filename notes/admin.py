from django.contrib import admin
from .models import Note, Tag


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'color', 'note_count', 'created_at']
    list_filter = ['created_at', 'user']
    search_fields = ['name', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['user', 'name']


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'is_pinned', 'is_archived', 'created_at', 'updated_at']
    list_filter = ['is_pinned', 'is_archived', 'created_at', 'user', 'tags']
    search_fields = ['title', 'content_text', 'user__email']
    readonly_fields = ['created_at', 'updated_at', 'last_accessed', 'content_text']
    filter_horizontal = ['tags']
    ordering = ['-created_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'title', 'content', 'content_text')
        }),
        ('Organization', {
            'fields': ('tags', 'color', 'is_pinned', 'is_archived')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'last_accessed'),
            'classes': ('collapse',)
        }),
    )
