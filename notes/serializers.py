from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Note, Tag

User = get_user_model()


class TagSerializer(serializers.ModelSerializer):
    """Serializer for Tag model"""
    note_count = serializers.SerializerMethodField()

    class Meta:
        model = Tag
        fields = ['id', 'name', 'color', 'note_count', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def get_note_count(self, obj):
        """Get note count from annotation or property"""
        # Try annotated value first (from queryset.annotate(notes_count=...))
        if hasattr(obj, 'notes_count'):
            return obj.notes_count
        # Fall back to property (less efficient but works)
        return obj.note_count

    def validate_name(self, value):
        """Ensure tag names are unique per user"""
        user = self.context['request'].user
        # Check if tag with this name exists for this user (excluding current instance for updates)
        queryset = Tag.objects.filter(user=user, name__iexact=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("You already have a tag with this name.")
        return value

    def validate_color(self, value):
        """Validate hex color format"""
        if value and not value.startswith('#'):
            value = f'#{value}'
        # Basic hex color validation
        if value and len(value) not in [4, 7]:  # #RGB or #RRGGBB
            raise serializers.ValidationError("Invalid color format. Use hex color code (e.g., #3b82f6)")
        return value


class TagListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for tag lists"""
    note_count = serializers.SerializerMethodField()

    class Meta:
        model = Tag
        fields = ['id', 'name', 'color', 'note_count']

    def get_note_count(self, obj):
        """Get note count from annotation or property"""
        # Try annotated value first (from queryset.annotate(notes_count=...))
        if hasattr(obj, 'notes_count'):
            return obj.notes_count
        # Fall back to property (less efficient but works)
        return obj.note_count


class NoteListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for note listings"""
    tags = TagListSerializer(many=True, read_only=True)
    tag_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all(),
        write_only=True,
        required=False,
        source='tags'
    )
    preview = serializers.SerializerMethodField()

    class Meta:
        model = Note
        fields = [
            'id',
            'title',
            'preview',
            'tags',
            'tag_ids',
            'is_pinned',
            'is_archived',
            'color',
            'created_at',
            'updated_at',
            'last_accessed',
        ]
        read_only_fields = ['created_at', 'updated_at', 'last_accessed']

    def get_preview(self, obj):
        """Generate a text preview of the note content"""
        if not obj.content_text:
            return ""
        # Return first 150 characters
        preview = obj.content_text[:150]
        if len(obj.content_text) > 150:
            preview += "..."
        return preview

    def validate_tag_ids(self, tags):
        """Ensure tags belong to the current user"""
        user = self.context['request'].user
        for tag in tags:
            if tag.user != user:
                raise serializers.ValidationError(f"Tag '{tag.name}' does not belong to you.")
        return tags


class NoteDetailSerializer(serializers.ModelSerializer):
    """Full serializer for note details with content"""
    tags = TagListSerializer(many=True, read_only=True)
    tag_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all(),
        write_only=True,
        required=False,
        source='tags'
    )

    class Meta:
        model = Note
        fields = [
            'id',
            'title',
            'content',
            'content_text',
            'tags',
            'tag_ids',
            'is_pinned',
            'is_archived',
            'color',
            'created_at',
            'updated_at',
            'last_accessed',
        ]
        read_only_fields = ['content_text', 'created_at', 'updated_at', 'last_accessed']

    def validate_tag_ids(self, tags):
        """Ensure tags belong to the current user"""
        user = self.context['request'].user
        for tag in tags:
            if tag.user != user:
                raise serializers.ValidationError(f"Tag '{tag.name}' does not belong to you.")
        return tags

    def validate_title(self, value):
        """Ensure title is not empty"""
        if not value or not value.strip():
            raise serializers.ValidationError("Title cannot be empty.")
        return value.strip()


class NoteCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating notes"""
    tag_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all(),
        write_only=True,
        required=False,
        source='tags'
    )

    class Meta:
        model = Note
        fields = [
            'title',
            'content',
            'tag_ids',
            'is_pinned',
            'is_archived',
            'color',
        ]

    def validate_tag_ids(self, tags):
        """Ensure tags belong to the current user"""
        user = self.context['request'].user
        for tag in tags:
            if tag.user != user:
                raise serializers.ValidationError(f"Tag '{tag.name}' does not belong to you.")
        return tags

    def validate_title(self, value):
        """Ensure title is not empty"""
        if not value or not value.strip():
            raise serializers.ValidationError("Title cannot be empty.")
        return value.strip()

    def create(self, validated_data):
        """Create note with user from context"""
        user = self.context['request'].user
        validated_data['user'] = user
        return super().create(validated_data)
