from django.contrib import admin
from django.utils.html import format_html
from .models import Work, Recording, Release, Track, Asset


class RecordingInline(admin.TabularInline):
    model = Recording
    extra = 0
    fields = ['title', 'type', 'status', 'duration_seconds', 'bpm', 'key']
    readonly_fields = ['get_isrc']
    show_change_link = True

    def get_isrc(self, obj):
        return obj.get_isrc() or '-'
    get_isrc.short_description = 'ISRC'


class TrackInline(admin.TabularInline):
    model = Track
    extra = 1
    fields = ['track_number', 'disc_number', 'recording', 'version', 'is_bonus', 'is_hidden']
    autocomplete_fields = ['recording']


class AssetInline(admin.TabularInline):
    model = Asset
    extra = 0
    fields = ['kind', 'file_name', 'file_path', 'file_size', 'is_master', 'is_public']
    readonly_fields = ['formatted_file_size']

    def formatted_file_size(self, obj):
        return obj.formatted_file_size or '-'
    formatted_file_size.short_description = 'Size'


@admin.register(Work)
class WorkAdmin(admin.ModelAdmin):
    list_display = ['title', 'get_iswc', 'language', 'genre', 'year_composed',
                    'recordings_count', 'has_complete_publishing_splits', 'created_at']
    list_filter = ['genre', 'language', 'year_composed', 'created_at']
    search_fields = ['title', 'lyrics']
    readonly_fields = ['created_at', 'updated_at', 'get_iswc', 'recordings_count',
                       'has_complete_publishing_splits']

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'alternate_titles', 'get_iswc')
        }),
        ('Details', {
            'fields': ('language', 'genre', 'sub_genre', 'year_composed')
        }),
        ('Relations', {
            'fields': ('translation_of', 'adaptation_of'),
            'classes': ('collapse',)
        }),
        ('Content', {
            'fields': ('lyrics', 'notes'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('recordings_count', 'has_complete_publishing_splits'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    inlines = [RecordingInline]

    def get_iswc(self, obj):
        return obj.get_iswc() or '-'
    get_iswc.short_description = 'ISWC'

    def recordings_count(self, obj):
        return obj.recordings.count()
    recordings_count.short_description = '# Recordings'

    def has_complete_publishing_splits(self, obj):
        return obj.has_complete_publishing_splits
    has_complete_publishing_splits.boolean = True
    has_complete_publishing_splits.short_description = 'Splits OK'


@admin.register(Recording)
class RecordingAdmin(admin.ModelAdmin):
    list_display = ['title', 'type', 'status', 'work', 'get_isrc', 'duration_display',
                    'bpm', 'key', 'has_complete_master_splits', 'release_count', 'created_at']
    list_filter = ['type', 'status', 'created_at', 'recording_date']
    search_fields = ['title', 'notes', 'work__title']
    autocomplete_fields = ['work', 'derived_from']
    readonly_fields = ['created_at', 'updated_at', 'get_isrc', 'formatted_duration',
                       'has_complete_master_splits', 'release_count']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'type', 'status', 'work', 'get_isrc')
        }),
        ('Technical Details', {
            'fields': ('duration_seconds', 'formatted_duration', 'bpm', 'key')
        }),
        ('Recording Information', {
            'fields': ('recording_date', 'studio', 'version', 'derived_from'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('has_complete_master_splits', 'release_count'),
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

    inlines = [AssetInline]

    def get_isrc(self, obj):
        return obj.get_isrc() or '-'
    get_isrc.short_description = 'ISRC'

    def duration_display(self, obj):
        return obj.formatted_duration or '-'
    duration_display.short_description = 'Duration'

    def release_count(self, obj):
        return obj.tracks.values('release').distinct().count()
    release_count.short_description = '# Releases'

    def has_complete_master_splits(self, obj):
        return obj.has_complete_master_splits
    has_complete_master_splits.boolean = True
    has_complete_master_splits.short_description = 'Master Splits OK'


@admin.register(Release)
class ReleaseAdmin(admin.ModelAdmin):
    list_display = ['title', 'type', 'status', 'get_upc', 'release_date',
                    'label_name', 'track_count', 'total_duration_display', 'created_at']
    list_filter = ['type', 'status', 'release_date', 'created_at']
    search_fields = ['title', 'description', 'catalog_number', 'label_name']
    readonly_fields = ['created_at', 'updated_at', 'get_upc', 'track_count',
                       'total_duration', 'formatted_total_duration']
    date_hierarchy = 'release_date'

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'type', 'status', 'get_upc')
        }),
        ('Release Details', {
            'fields': ('release_date', 'catalog_number', 'label_name')
        }),
        ('Media', {
            'fields': ('artwork_url',),
            'classes': ('collapse',)
        }),
        ('Content', {
            'fields': ('description', 'notes'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('track_count', 'total_duration', 'formatted_total_duration'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    inlines = [TrackInline]

    def get_upc(self, obj):
        return obj.get_upc() or '-'
    get_upc.short_description = 'UPC'

    def track_count(self, obj):
        return obj.tracks.count()
    track_count.short_description = '# Tracks'

    def total_duration_display(self, obj):
        return obj.formatted_total_duration or '-'
    total_duration_display.short_description = 'Total Duration'


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'release', 'recording', 'track_number', 'disc_number',
                    'version', 'is_bonus', 'is_hidden']
    list_filter = ['disc_number', 'is_bonus', 'is_hidden', 'created_at']
    search_fields = ['release__title', 'recording__title', 'version']
    autocomplete_fields = ['release', 'recording']


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ['recording', 'kind', 'file_name', 'formatted_file_size_display',
                    'is_master', 'is_public', 'uploaded_by', 'created_at']
    list_filter = ['kind', 'is_master', 'is_public', 'created_at']
    search_fields = ['recording__title', 'file_name', 'notes']
    autocomplete_fields = ['recording', 'uploaded_by']
    readonly_fields = ['created_at', 'updated_at', 'formatted_file_size']

    fieldsets = (
        ('Recording', {
            'fields': ('recording',)
        }),
        ('File Information', {
            'fields': ('kind', 'file_name', 'file_path', 'file_size', 'formatted_file_size', 'mime_type')
        }),
        ('Integrity', {
            'fields': ('checksum',),
            'classes': ('collapse',)
        }),
        ('Audio Quality', {
            'fields': ('sample_rate', 'bit_depth', 'bitrate'),
            'classes': ('collapse',)
        }),
        ('Video Quality', {
            'fields': ('resolution', 'frame_rate'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_master', 'is_public')
        }),
        ('Metadata', {
            'fields': ('uploaded_by', 'notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def formatted_file_size_display(self, obj):
        return obj.formatted_file_size or '-'
    formatted_file_size_display.short_description = 'Size'