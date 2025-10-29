from rest_framework import serializers
from .models import Work, Recording, Release, Track, Asset
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

        # Get file metadata
        validated_data['file_name'] = file.name
        validated_data['file_size'] = file.size
        validated_data['mime_type'] = file.content_type or 'application/octet-stream'

        # Set uploaded_by from request
        if 'request' in self.context:
            validated_data['uploaded_by'] = self.context['request'].user

        # Save file and create asset
        # In production, this would save to cloud storage
        # For now, we'll just save the path reference
        validated_data['file_path'] = f"assets/{file.name}"

        # Calculate checksum
        import hashlib
        hasher = hashlib.sha256()
        for chunk in file.chunks():
            hasher.update(chunk)
        validated_data['checksum'] = hasher.hexdigest()

        return Asset.objects.create(**validated_data)