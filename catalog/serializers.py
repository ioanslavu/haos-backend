from rest_framework import serializers
from .models import (
    Work, Recording, Release, Track, Asset,
    Song, SongArtist, SongChecklistItem, SongStageTransition, SongStageStatus, SongAsset, SongNote, SongAlert,
    AlertConfiguration
)
import os
import re
import uuid
from django.utils import timezone
from identity.models import Identifier
from identity.serializers import IdentifierSerializer


class AssetSerializer(serializers.ModelSerializer):
    """Serializer for Asset model."""

    formatted_file_size = serializers.CharField(read_only=True)
    uploaded_by_name = serializers.CharField(source='uploaded_by.username', read_only=True)

    class Meta:
        model = Asset
        fields = [
            'id', 'recording', 'kind', 'file_name', 'file_path', 'file_size',
            'formatted_file_size', 'mime_type', 'checksum', 'sample_rate',
            'bit_depth', 'bitrate', 'resolution', 'frame_rate', 'is_master',
            'is_public', 'uploaded_by', 'uploaded_by_name', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'checksum']


class WorkListSerializer(serializers.ModelSerializer):
    """Light serializer for Work listing."""

    iswc = serializers.SerializerMethodField()
    recordings_count = serializers.IntegerField(read_only=True)
    has_complete_publishing_splits = serializers.BooleanField(read_only=True)

    class Meta:
        model = Work
        fields = [
            'id', 'title', 'iswc', 'language', 'genre', 'year_composed',
            'recordings_count', 'has_complete_publishing_splits', 'created_at'
        ]
        read_only_fields = ['created_at']

    def get_iswc(self, obj):
        """Get ISWC code if exists."""
        return obj.get_iswc()


class WorkDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for Work with related data."""

    iswc = serializers.SerializerMethodField()
    identifiers = serializers.SerializerMethodField()
    recordings_count = serializers.IntegerField(read_only=True)
    has_complete_publishing_splits = serializers.BooleanField(read_only=True)
    translation_of_title = serializers.CharField(
        source='translation_of.title',
        read_only=True,
        allow_null=True
    )
    adaptation_of_title = serializers.CharField(
        source='adaptation_of.title',
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = Work
        fields = [
            'id', 'title', 'alternate_titles', 'iswc', 'identifiers',
            'language', 'genre', 'sub_genre', 'year_composed',
            'translation_of', 'translation_of_title', 'adaptation_of',
            'adaptation_of_title', 'lyrics', 'notes', 'recordings_count',
            'has_complete_publishing_splits', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_iswc(self, obj):
        """Get ISWC code if exists."""
        return obj.get_iswc()

    def get_identifiers(self, obj):
        """Get all identifiers for this work."""
        identifiers = Identifier.objects.filter(
            owner_type='work',
            owner_id=obj.id
        )
        return IdentifierSerializer(identifiers, many=True).data


class WorkCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating Work."""

    class Meta:
        model = Work
        fields = [
            'title', 'alternate_titles', 'language', 'genre', 'sub_genre',
            'year_composed', 'translation_of', 'adaptation_of', 'lyrics', 'notes'
        ]


class RecordingListSerializer(serializers.ModelSerializer):
    """Light serializer for Recording listing."""

    isrc = serializers.SerializerMethodField()
    work_title = serializers.CharField(source='work.title', read_only=True)
    formatted_duration = serializers.CharField(read_only=True)
    has_complete_master_splits = serializers.BooleanField(read_only=True)
    release_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Recording
        fields = [
            'id', 'title', 'type', 'status', 'work', 'work_title', 'isrc',
            'duration_seconds', 'formatted_duration', 'bpm', 'key',
            'has_complete_master_splits', 'release_count', 'created_at'
        ]
        read_only_fields = ['created_at']

    def get_isrc(self, obj):
        """Get ISRC code if exists."""
        return obj.get_isrc()


class RecordingDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for Recording with related data."""

    isrc = serializers.SerializerMethodField()
    identifiers = serializers.SerializerMethodField()
    assets = AssetSerializer(many=True, read_only=True)
    work_title = serializers.CharField(source='work.title', read_only=True)
    formatted_duration = serializers.CharField(read_only=True)
    has_complete_master_splits = serializers.BooleanField(read_only=True)
    release_count = serializers.IntegerField(read_only=True)
    derived_from_title = serializers.CharField(
        source='derived_from.title',
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = Recording
        fields = [
            'id', 'title', 'type', 'status', 'work', 'work_title', 'isrc',
            'identifiers', 'duration_seconds', 'formatted_duration', 'bpm',
            'key', 'recording_date', 'studio', 'version', 'derived_from',
            'derived_from_title', 'notes', 'assets', 'has_complete_master_splits',
            'release_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_isrc(self, obj):
        """Get ISRC code if exists."""
        return obj.get_isrc()

    def get_identifiers(self, obj):
        """Get all identifiers for this recording."""
        identifiers = Identifier.objects.filter(
            owner_type='recording',
            owner_id=obj.id
        )
        return IdentifierSerializer(identifiers, many=True).data


class TrackSerializer(serializers.ModelSerializer):
    """Serializer for Track model."""

    recording_title = serializers.CharField(source='recording.title', read_only=True)
    recording_isrc = serializers.SerializerMethodField()
    duration_seconds = serializers.IntegerField(source='recording.duration_seconds', read_only=True)
    formatted_duration = serializers.CharField(source='recording.formatted_duration', read_only=True)

    class Meta:
        model = Track
        fields = [
            'id', 'release', 'recording', 'recording_title', 'recording_isrc',
            'track_number', 'disc_number', 'version', 'is_bonus', 'is_hidden',
            'duration_seconds', 'formatted_duration', 'created_at'
        ]
        read_only_fields = ['created_at']

    def get_recording_isrc(self, obj):
        """Get ISRC of the recording."""
        return obj.recording.get_isrc() if obj.recording else None


class RecordingCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating Recording."""

    class Meta:
        model = Recording
        fields = [
            'id', 'title', 'type', 'status', 'work', 'duration_seconds', 'bpm',
            'key', 'recording_date', 'studio', 'version', 'derived_from', 'notes'
        ]
        read_only_fields = ['id']


class ReleaseListSerializer(serializers.ModelSerializer):
    """Light serializer for Release listing."""

    upc = serializers.SerializerMethodField()
    track_count = serializers.IntegerField(read_only=True)
    formatted_total_duration = serializers.CharField(read_only=True)

    class Meta:
        model = Release
        fields = [
            'id', 'title', 'type', 'status', 'upc', 'release_date',
            'catalog_number', 'label_name', 'track_count',
            'formatted_total_duration', 'artwork_url', 'created_at'
        ]
        read_only_fields = ['created_at']

    def get_upc(self, obj):
        """Get UPC code if exists."""
        return obj.get_upc()


class ReleaseDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for Release with related data."""

    upc = serializers.SerializerMethodField()
    identifiers = serializers.SerializerMethodField()
    tracks = TrackSerializer(many=True, read_only=True)
    track_count = serializers.IntegerField(read_only=True)
    total_duration = serializers.IntegerField(read_only=True)
    formatted_total_duration = serializers.CharField(read_only=True)

    class Meta:
        model = Release
        fields = [
            'id', 'title', 'type', 'status', 'upc', 'identifiers',
            'release_date', 'catalog_number', 'label_name', 'artwork_url',
            'description', 'notes', 'tracks', 'track_count', 'total_duration',
            'formatted_total_duration', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_upc(self, obj):
        """Get UPC code if exists."""
        return obj.get_upc()

    def get_identifiers(self, obj):
        """Get all identifiers for this release."""
        identifiers = Identifier.objects.filter(
            owner_type='release',
            owner_id=obj.id
        )
        return IdentifierSerializer(identifiers, many=True).data


class ReleaseCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating Release with tracks."""

    tracks_data = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False,
        help_text="List of tracks with recording_id, track_number, disc_number, etc."
    )

    class Meta:
        model = Release
        fields = [
            'title', 'type', 'status', 'release_date', 'catalog_number',
            'label_name', 'artwork_url', 'description', 'notes', 'tracks_data'
        ]

    def create(self, validated_data):
        tracks_data = validated_data.pop('tracks_data', [])
        release = Release.objects.create(**validated_data)

        # Create tracks
        for track_data in tracks_data:
            Track.objects.create(
                release=release,
                **track_data
            )

        return release

    def update(self, instance, validated_data):
        tracks_data = validated_data.pop('tracks_data', None)

        # Update release fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update tracks if provided
        if tracks_data is not None:
            # Clear existing tracks and recreate
            instance.tracks.all().delete()
            for track_data in tracks_data:
                Track.objects.create(
                    release=instance,
                    **track_data
                )

        return instance


class AssetUploadSerializer(serializers.ModelSerializer):
    """Serializer for uploading assets."""

    file = serializers.FileField(write_only=True)

    class Meta:
        model = Asset
        fields = [
            'recording', 'kind', 'file', 'is_master', 'is_public', 'notes'
        ]

    def create(self, validated_data):
        file = validated_data.pop('file')

        # Sanitize file name to prevent path traversal or unsafe chars
        raw_name = getattr(file, 'name', 'upload.bin') or 'upload.bin'
        base_name = os.path.basename(raw_name)
        name, ext = os.path.splitext(base_name)
        safe_stem = re.sub(r'[^A-Za-z0-9._-]', '_', name)[:100] or 'file'
        if safe_stem.startswith('.'):
            safe_stem = safe_stem.lstrip('.') or 'file'
        suffix = uuid.uuid4().hex[:8]
        safe_name = f"{safe_stem}-{suffix}{ext[:10]}"

        # Get file metadata
        validated_data['file_name'] = safe_name
        validated_data['file_size'] = file.size
        validated_data['mime_type'] = file.content_type or 'application/octet-stream'

        # Set uploaded_by from request
        if 'request' in self.context:
            validated_data['uploaded_by'] = self.context['request'].user

        # Save file and create asset
        # In production, this would save to cloud storage
        # For now, we'll just save the sanitized path reference
        validated_data['file_path'] = f"assets/{safe_name}"

        # Calculate checksum
        import hashlib
        hasher = hashlib.sha256()
        for chunk in file.chunks():
            hasher.update(chunk)
        validated_data['checksum'] = hasher.hexdigest()

        return Asset.objects.create(**validated_data)


# ============================================================================
# SONG WORKFLOW SERIALIZERS
# ============================================================================


class SongChecklistItemSerializer(serializers.ModelSerializer):
    """Serializer for SongChecklistItem."""

    assigned_to_name = serializers.CharField(
        source='assigned_to.get_full_name',
        read_only=True,
        allow_null=True
    )
    completed_by_name = serializers.CharField(
        source='completed_by.get_full_name',
        read_only=True,
        allow_null=True
    )
    recording_title = serializers.CharField(
        source='recording.title',
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = SongChecklistItem
        fields = [
            'id', 'song', 'recording', 'recording_title', 'stage', 'category',
            'item_name', 'description', 'order', 'required', 'validation_type',
            'validation_rule', 'is_complete', 'completed_by', 'completed_by_name',
            'completed_at', 'help_text', 'help_link', 'assigned_to', 'assigned_to_name',
            'is_blocker', 'depends_on'
        ]
        read_only_fields = ['completed_at', 'recording_title']


class SongStageTransitionSerializer(serializers.ModelSerializer):
    """Serializer for SongStageTransition audit log."""

    transitioned_by_name = serializers.CharField(
        source='transitioned_by.get_full_name',
        read_only=True
    )
    from_stage_display = serializers.CharField(
        source='get_from_stage_display',
        read_only=True
    )
    to_stage_display = serializers.CharField(
        source='get_to_stage_display',
        read_only=True
    )

    class Meta:
        model = SongStageTransition
        fields = [
            'id', 'song', 'from_stage', 'from_stage_display', 'to_stage',
            'to_stage_display', 'transitioned_by', 'transitioned_by_name',
            'transitioned_at', 'transition_type', 'notes',
            'checklist_completion_at_transition', 'rejection_reason',
            'rejection_category'
        ]
        read_only_fields = ['transitioned_at']


class SongStageStatusSerializer(serializers.ModelSerializer):
    """Serializer for SongStageStatus."""

    stage_display = serializers.CharField(
        source='get_stage_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    days_in_status = serializers.IntegerField(read_only=True)

    class Meta:
        model = SongStageStatus
        fields = [
            'id',
            'stage',
            'stage_display',
            'status',
            'status_display',
            'started_at',
            'completed_at',
            'blocked_reason',
            'notes',
            'days_in_status',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at', 'days_in_status']


class SongAssetSerializer(serializers.ModelSerializer):
    """Serializer for SongAsset (marketing assets)."""

    uploaded_by_name = serializers.CharField(
        source='uploaded_by.get_full_name',
        read_only=True
    )
    reviewed_by_name = serializers.CharField(
        source='reviewed_by.get_full_name',
        read_only=True,
        allow_null=True
    )
    dimensions = serializers.CharField(read_only=True)

    class Meta:
        model = SongAsset
        fields = [
            'id', 'song', 'asset_type', 'google_drive_url', 'file_format',
            'width', 'height', 'dimensions', 'title', 'description',
            'uploaded_by', 'uploaded_by_name', 'uploaded_at',
            'review_status', 'reviewed_by', 'reviewed_by_name',
            'reviewed_at', 'review_notes', 'is_primary'
        ]
        read_only_fields = ['uploaded_at', 'reviewed_at']


class SongNoteSerializer(serializers.ModelSerializer):
    """Serializer for SongNote."""

    author_name = serializers.CharField(
        source='author.get_full_name',
        read_only=True
    )
    visible_to_department_names = serializers.SerializerMethodField()

    class Meta:
        model = SongNote
        fields = [
            'id', 'song', 'author', 'author_name', 'created_at',
            'note_type', 'content', 'pitched_to_artist', 'pitch_outcome',
            'visible_to_departments', 'visible_to_department_names',
            'is_internal'
        ]
        read_only_fields = ['created_at']

    def get_visible_to_department_names(self, obj):
        """Get names of departments that can see this note."""
        return [dept.name for dept in obj.visible_to_departments.all()]


class SongAlertSerializer(serializers.ModelSerializer):
    """Serializer for SongAlert."""

    song_title = serializers.CharField(source='song.title', read_only=True)
    target_department_name = serializers.CharField(
        source='target_department.name',
        read_only=True,
        allow_null=True
    )
    target_user_name = serializers.CharField(
        source='target_user.get_full_name',
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = SongAlert
        fields = [
            'id', 'song', 'song_title', 'alert_type', 'target_department',
            'target_department_name', 'target_user', 'target_user_name',
            'title', 'message', 'action_url', 'action_label', 'created_at',
            'is_read', 'read_at', 'priority'
        ]
        read_only_fields = ['created_at', 'read_at']


class SongListSerializer(serializers.ModelSerializer):
    """Minimal Song serializer for list view."""

    artist = serializers.SerializerMethodField()
    current_stage = serializers.SerializerMethodField()
    stage_display = serializers.SerializerMethodField()
    assigned_department_name = serializers.CharField(
        source='assigned_department.name',
        read_only=True,
        allow_null=True
    )
    assigned_user_name = serializers.CharField(
        source='assigned_user.get_full_name',
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = Song
        fields = [
            'id', 'title', 'artist', 'current_stage', 'stage_display',
            'checklist_progress', 'target_release_date', 'priority',
            'is_overdue', 'assigned_department', 'assigned_department_name',
            'assigned_user', 'assigned_user_name', 'created_at', 'days_in_current_stage'
        ]
        read_only_fields = ['checklist_progress', 'is_overdue', 'created_at', 'days_in_current_stage']

    def get_artist(self, obj):
        """Return artist as nested object with id and display_name."""
        if obj.artist:
            return {
                'id': obj.artist.id,
                'display_name': obj.artist.display_name
            }
        return None

    def get_current_stage(self, obj):
        """Return stage, defaulting to 'draft' if null."""
        return obj.stage or 'draft'

    def get_stage_display(self, obj):
        """Return stage display name, defaulting to 'Draft' if null."""
        if obj.stage:
            return obj.get_stage_display()
        return 'Draft'


class SongArtistSerializer(serializers.ModelSerializer):
    """Serializer for featured artists on songs."""

    artist_id = serializers.IntegerField(source='artist.id', read_only=True)
    artist_name = serializers.CharField(source='artist.name', read_only=True)
    artist_display_name = serializers.CharField(source='artist.display_name', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = SongArtist
        fields = ['id', 'artist_id', 'artist_name', 'artist_display_name', 'role', 'role_display', 'order', 'created_at']
        read_only_fields = ['id', 'created_at']


class SongDetailSerializer(serializers.ModelSerializer):
    """
    Detailed Song serializer with permission-aware field hiding.

    Hides sensitive data based on user's department:
    - Marketing: Cannot see splits, work details, recording technical details
    - Digital: Cannot see splits (only names)
    - Sales: Cannot see splits
    """

    artist = serializers.SerializerMethodField()
    current_stage = serializers.SerializerMethodField()
    stage_display = serializers.SerializerMethodField()
    assigned_department_name = serializers.CharField(
        source='assigned_department.name',
        read_only=True,
        allow_null=True
    )
    assigned_user_name = serializers.CharField(
        source='assigned_user.get_full_name',
        read_only=True,
        allow_null=True
    )
    created_by = serializers.SerializerMethodField()
    stage_updated_by_name = serializers.CharField(
        source='stage_updated_by.get_full_name',
        read_only=True,
        allow_null=True
    )

    # Related data
    work = serializers.SerializerMethodField()
    recording = serializers.SerializerMethodField()
    release = serializers.SerializerMethodField()
    recordings_count = serializers.SerializerMethodField()
    releases_count = serializers.SerializerMethodField()

    # Featured artists
    featured_artists = SongArtistSerializer(source='artist_credits', many=True, read_only=True)
    all_artists = serializers.SerializerMethodField()
    display_artists = serializers.CharField(read_only=True)

    # Stage statuses (NEW - for parallel workflows)
    stage_statuses = SongStageStatusSerializer(many=True, read_only=True)

    class Meta:
        model = Song
        fields = [
            'id', 'title', 'artist', 'genre', 'language', 'duration',
            'current_stage', 'stage_display', 'assigned_department', 'assigned_department_name',
            'assigned_user', 'assigned_user_name', 'priority', 'target_release_date',
            'stage_deadline', 'work', 'recording', 'release', 'recordings_count', 'releases_count',
            'created_by', 'created_at', 'updated_at',
            'stage_entered_at', 'stage_updated_by', 'stage_updated_by_name',
            'checklist_progress', 'is_overdue', 'days_in_current_stage',
            'is_archived', 'is_blocked', 'blocked_reason', 'internal_notes',
            'external_notes',
            'featured_artists', 'all_artists', 'display_artists',
            'stage_statuses'
        ]
        read_only_fields = [
            'checklist_progress', 'is_overdue', 'days_in_current_stage',
            'created_at', 'updated_at', 'stage_entered_at'
        ]

    def get_artist(self, obj):
        """Return artist as nested object with id and display_name."""
        if obj.artist:
            return {
                'id': obj.artist.id,
                'display_name': obj.artist.display_name
            }
        return None

    def get_current_stage(self, obj):
        """Return stage, defaulting to 'draft' if null."""
        return obj.stage or 'draft'

    def get_stage_display(self, obj):
        """Return stage display name, defaulting to 'Draft' if null."""
        if obj.stage:
            return obj.get_stage_display()
        return 'Draft'

    def get_created_by(self, obj):
        """Return created_by as nested object with id, email, and full_name."""
        if obj.created_by:
            return {
                'id': obj.created_by.id,
                'email': obj.created_by.email,
                'full_name': obj.created_by.get_full_name()
            }
        return None

    def get_recordings_count(self, obj):
        """Count of recordings linked to this song."""
        return obj.recordings.count()

    def get_releases_count(self, obj):
        """Count of releases linked to this song."""
        return obj.releases.count()

    def get_work(self, obj):
        """Return work as nested object with id and iswc."""
        if obj.work:
            # Get ISWC from identifiers
            iswc = None
            try:
                from identity.models import Identifier
                identifier = Identifier.objects.filter(
                    owner_type='catalog.work',
                    owner_id=obj.work.id,
                    scheme='iswc'
                ).first()
                if identifier:
                    iswc = identifier.value
            except:
                pass

            return {
                'id': obj.work.id,
                'iswc': iswc
            }
        return None

    def get_recording(self, obj):
        """Return recording as nested object with id and isrc."""
        if hasattr(obj, 'recording') and obj.recording:
            # Get ISRC from identifiers
            isrc = None
            try:
                from identity.models import Identifier
                identifier = Identifier.objects.filter(
                    owner_type='catalog.recording',
                    owner_id=obj.recording.id,
                    scheme='isrc'
                ).first()
                if identifier:
                    isrc = identifier.value
            except:
                pass

            return {
                'id': obj.recording.id,
                'isrc': isrc
            }
        return None

    def get_release(self, obj):
        """Return release as nested object with id and upc."""
        if hasattr(obj, 'release') and obj.release:
            # Get UPC from identifiers
            upc = None
            try:
                from identity.models import Identifier
                identifier = Identifier.objects.filter(
                    owner_type='catalog.release',
                    owner_id=obj.release.id,
                    scheme='upc'
                ).first()
                if identifier:
                    upc = identifier.value
            except:
                pass

            return {
                'id': obj.release.id,
                'upc': upc
            }
        return None

    def get_all_artists(self, obj):
        """Return all artists (primary + featured) as list."""
        return obj.get_all_artists()

    def get_fields(self):
        """
        Dynamically remove fields based on user's department permissions.

        Permission rules:
        - Marketing: Hide work, work_title, internal_notes, blocked info
        - Digital: Hide internal_notes, blocked info
        - Sales: Hide internal_notes, blocked info
        """
        fields = super().get_fields()
        request = self.context.get('request')

        if not request or not request.user or not hasattr(request.user, 'profile'):
            return fields

        user_profile = request.user.profile

        # Admin can see everything
        if user_profile.role.level >= 1000:
            return fields

        if not user_profile.department:
            return fields

        user_dept = user_profile.department.code.lower()

        # Marketing sees limited info - no Work details, no internal notes
        if user_dept == 'marketing':
            fields_to_hide = ['work', 'work_title', 'internal_notes', 'is_blocked', 'blocked_reason']
            for field_name in fields_to_hide:
                fields.pop(field_name, None)

        # Digital cannot see internal notes or blocking info
        elif user_dept == 'digital':
            fields_to_hide = ['internal_notes', 'is_blocked', 'blocked_reason']
            for field_name in fields_to_hide:
                fields.pop(field_name, None)

        # Sales cannot see internal notes or blocking info
        elif user_dept == 'sales':
            fields_to_hide = ['internal_notes', 'is_blocked', 'blocked_reason']
            for field_name in fields_to_hide:
                fields.pop(field_name, None)

        return fields


class SongCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating Songs."""

    class Meta:
        model = Song
        fields = [
            'title', 'artist', 'genre', 'language', 'duration',
            'priority', 'target_release_date', 'stage_deadline',
            'work', 'assigned_department', 'assigned_user',
            'internal_notes', 'external_notes'
        ]

    def create(self, validated_data):
        """Create song with created_by from request user."""
        request = self.context.get('request')
        validated_data['created_by'] = request.user

        # Set initial stage
        validated_data['stage'] = 'draft'
        validated_data['stage_entered_at'] = timezone.now()

        song = Song.objects.create(**validated_data)

        # Generate checklist for draft stage if needed
        # (Draft has no checklist by default, checklist generated on first transition)

        return song

    def update(self, instance, validated_data):
        """Update song fields."""
        # Don't allow direct stage updates via this serializer
        # Stage updates must go through transition() action
        validated_data.pop('stage', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


class AlertConfigurationSerializer(serializers.ModelSerializer):
    """
    Serializer for Alert Configuration settings.

    Allows admins to manage alert configurations from the frontend.
    """

    alert_type_display = serializers.CharField(
        source='get_alert_type_display',
        read_only=True
    )

    priority_display = serializers.CharField(
        source='get_priority_display',
        read_only=True
    )

    updated_by_name = serializers.CharField(
        source='updated_by.get_full_name',
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = AlertConfiguration
        fields = [
            'id', 'alert_type', 'alert_type_display', 'enabled',
            'days_threshold', 'schedule_description',
            'notify_assigned_user', 'notify_department_managers', 'notify_song_creator',
            'priority', 'priority_display',
            'title_template', 'message_template',
            'created_at', 'updated_at', 'updated_by', 'updated_by_name'
        ]
        read_only_fields = ['created_at', 'updated_at', 'updated_by', 'updated_by_name']

    def validate_days_threshold(self, value):
        """Ensure days_threshold is positive if provided."""
        if value is not None and value < 0:
            raise serializers.ValidationError("Days threshold must be a positive number")
        return value

    def validate_title_template(self, value):
        """Ensure title template is not empty."""
        if not value or not value.strip():
            raise serializers.ValidationError("Title template cannot be empty")
        return value

    def validate_message_template(self, value):
        """Ensure message template is not empty."""
        if not value or not value.strip():
            raise serializers.ValidationError("Message template cannot be empty")
        return value
