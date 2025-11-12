"""
Serializers for Camps app
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from identity.models import Entity
from api.models import Department
from .models import Camp, CampStudio, CampStudioArtist

User = get_user_model()


# === NESTED SERIALIZERS (for related objects) ===

class UserNestedSerializer(serializers.ModelSerializer):
    """Lightweight user serializer for nested use"""
    name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'name']

    def get_name(self, obj):
        return obj.get_full_name() or obj.email


class DepartmentNestedSerializer(serializers.ModelSerializer):
    """Lightweight department serializer"""
    class Meta:
        model = Department
        fields = ['id', 'name', 'code']


class ArtistNestedSerializer(serializers.ModelSerializer):
    """Lightweight artist serializer for nested use"""
    profile_picture = serializers.SerializerMethodField()

    class Meta:
        model = Entity
        fields = ['id', 'display_name', 'profile_picture']

    def get_profile_picture(self, obj):
        if obj.profile_photo:
            return obj.profile_photo.url
        return None


# === CAMP STUDIO ARTIST SERIALIZER ===

class CampStudioArtistSerializer(serializers.ModelSerializer):
    """Serializer for CampStudioArtist with nested artist details"""
    artist = ArtistNestedSerializer(read_only=True)
    artist_id = serializers.PrimaryKeyRelatedField(
        queryset=Entity.objects.filter(
            entity_roles__role__in=['artist', 'producer', 'composer', 'lyricist', 'audio_editor']
        ).distinct(),
        source='artist',
        write_only=True
    )

    class Meta:
        model = CampStudioArtist
        fields = ['id', 'artist', 'artist_id', 'is_internal', 'created_at']
        read_only_fields = ['created_at']


# === CAMP STUDIO SERIALIZER ===

class CampStudioSerializer(serializers.ModelSerializer):
    """Serializer for CampStudio with nested artists"""
    # For reading: group artists by internal/external
    internal_artists = serializers.SerializerMethodField()
    external_artists = serializers.SerializerMethodField()

    # For writing: accept lists of artist IDs
    internal_artist_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        allow_empty=True
    )
    external_artist_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        allow_empty=True
    )

    class Meta:
        model = CampStudio
        fields = [
            'id', 'name', 'location', 'city', 'country',
            'hours', 'sessions', 'order',
            'internal_artists', 'external_artists',
            'internal_artist_ids', 'external_artist_ids',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_internal_artists(self, obj):
        """Get internal artists for this studio"""
        artists = obj.studio_artists.filter(is_internal=True).select_related('artist')
        return [ArtistNestedSerializer(sa.artist).data for sa in artists]

    def get_external_artists(self, obj):
        """Get external artists for this studio"""
        artists = obj.studio_artists.filter(is_internal=False).select_related('artist')
        return [ArtistNestedSerializer(sa.artist).data for sa in artists]


# === CAMP SERIALIZERS ===

class CampListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for camp list view"""
    created_by = UserNestedSerializer(read_only=True)
    department = DepartmentNestedSerializer(read_only=True)
    studios_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Camp
        fields = [
            'id', 'name', 'start_date', 'end_date', 'status',
            'studios_count', 'department', 'created_by',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['studios_count', 'created_at', 'updated_at']


class CampDetailSerializer(serializers.ModelSerializer):
    """Full serializer for camp detail view with nested studios"""
    created_by = UserNestedSerializer(read_only=True)
    department = DepartmentNestedSerializer(read_only=True)
    studios = CampStudioSerializer(many=True, read_only=True)
    studios_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Camp
        fields = [
            'id', 'name', 'start_date', 'end_date', 'status',
            'studios', 'studios_count', 'department', 'created_by',
            'created_at', 'updated_at', 'deleted_at'
        ]
        read_only_fields = ['studios_count', 'created_at', 'updated_at', 'deleted_at']


class CampWriteSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating camps with nested studios"""
    studios = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False,
        allow_empty=True
    )

    class Meta:
        model = Camp
        fields = [
            'id', 'name', 'start_date', 'end_date', 'status',
            'studios',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate(self, data):
        """Validate camp data"""
        # Validate date range if both provided
        start_date = data.get('start_date')
        end_date = data.get('end_date')

        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({
                'end_date': 'End date must be greater than or equal to start date.'
            })

        return data

    def create(self, validated_data):
        """Create camp with nested studios and artists"""
        studios_data = validated_data.pop('studios', [])

        # Set department and created_by from request context
        request = self.context.get('request')
        if request and request.user:
            validated_data['created_by'] = request.user
            validated_data['department'] = request.user.profile.department

        # Create camp
        camp = Camp.objects.create(**validated_data)

        # Create studios
        self._create_studios(camp, studios_data)

        return camp

    def update(self, instance, validated_data):
        """Update camp with nested studios and artists"""
        studios_data = validated_data.pop('studios', None)

        # Update camp fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update studios if provided
        if studios_data is not None:
            # Delete existing studios (CASCADE will delete artists)
            instance.studios.all().delete()
            # Create new studios
            self._create_studios(instance, studios_data)

        return instance

    def _create_studios(self, camp, studios_data):
        """Helper method to create studios with artists"""
        for studio_data in studios_data:
            # Extract artist IDs (write-only fields)
            internal_artist_ids = studio_data.pop('internal_artist_ids', [])
            external_artist_ids = studio_data.pop('external_artist_ids', [])
            artist_ids = studio_data.pop('artist_ids', [])  # Handle unified artist_ids field

            # Handle read-only artist arrays (from existing studios being re-sent)
            # Extract IDs from artist objects if ID lists not provided
            internal_artists = studio_data.pop('internal_artists', [])
            external_artists = studio_data.pop('external_artists', [])

            if not internal_artist_ids and internal_artists:
                # Extract IDs from artist objects
                internal_artist_ids = [a['id'] if isinstance(a, dict) else a.id for a in internal_artists]

            if not external_artist_ids and external_artists:
                # Extract IDs from artist objects
                external_artist_ids = [a['id'] if isinstance(a, dict) else a.id for a in external_artists]

            # Remove other read-only fields
            studio_data.pop('id', None)  # Remove ID for new studios
            studio_data.pop('created_at', None)
            studio_data.pop('updated_at', None)

            # Create studio
            studio = CampStudio.objects.create(
                camp=camp,
                **studio_data
            )

            # Create internal artist assignments
            for artist_id in internal_artist_ids:
                CampStudioArtist.objects.create(
                    studio=studio,
                    artist_id=artist_id,
                    is_internal=True
                )

            # Create external artist assignments
            for artist_id in external_artist_ids:
                CampStudioArtist.objects.create(
                    studio=studio,
                    artist_id=artist_id,
                    is_internal=False
                )
