from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex

User = get_user_model()


class Tag(models.Model):
    """
    Tag model for organizing notes.
    Each user has their own tag namespace.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='note_tags',
        help_text="Owner of this tag"
    )

    name = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Tag name"
    )

    color = models.CharField(
        max_length=7,
        default='#3b82f6',  # Default blue color
        help_text="Hex color code for the tag"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'name']
        ordering = ['name']
        indexes = [
            models.Index(fields=['user', 'name']),
        ]
        verbose_name = "Tag"
        verbose_name_plural = "Tags"

    def __str__(self):
        return f"{self.user.email} - {self.name}"

    @property
    def note_count(self):
        """Get count of notes with this tag."""
        return self.notes.count()


class Note(models.Model):
    """
    Note model for storing user notes with rich text content.
    Each note belongs to a single user and can have multiple tags.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notes',
        help_text="Owner of this note"
    )

    title = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Note title"
    )

    # Store rich text content as JSON (Tiptap format)
    content = models.JSONField(
        default=dict,
        blank=True,
        help_text="Rich text content in JSON format (Tiptap)"
    )

    # Plain text content for search purposes
    content_text = models.TextField(
        blank=True,
        help_text="Plain text version of content for search"
    )

    tags = models.ManyToManyField(
        Tag,
        related_name='notes',
        blank=True,
        help_text="Tags for this note"
    )

    is_pinned = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether this note is pinned to the top"
    )

    is_archived = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether this note is archived"
    )

    color = models.CharField(
        max_length=7,
        blank=True,
        null=True,
        help_text="Optional hex color code for the note"
    )

    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        db_index=True
    )

    last_accessed = models.DateTimeField(
        auto_now=True,
        help_text="Last time the note was viewed or edited"
    )

    # Full-text search vector
    search_vector = SearchVectorField(null=True, blank=True)

    class Meta:
        ordering = ['-is_pinned', '-updated_at']
        indexes = [
            models.Index(fields=['user', '-is_pinned', '-updated_at']),
            models.Index(fields=['user', 'is_archived']),
            models.Index(fields=['user', '-created_at']),
            GinIndex(fields=['search_vector']),  # Full-text search index
        ]
        verbose_name = "Note"
        verbose_name_plural = "Notes"

    def __str__(self):
        return f"{self.user.email} - {self.title}"

    def save(self, *args, **kwargs):
        """Override save to extract plain text from content for search."""
        # Extract plain text from JSON content for search
        if self.content:
            self.content_text = self._extract_text_from_content(self.content)
        super().save(*args, **kwargs)

    def _extract_text_from_content(self, content):
        """
        Extract plain text from Tiptap JSON content.
        This is a simple extraction - you can enhance it later.
        """
        def extract_text(node):
            if isinstance(node, dict):
                text_parts = []
                if node.get('type') == 'text':
                    return node.get('text', '')
                if 'content' in node:
                    for child in node['content']:
                        text_parts.append(extract_text(child))
                return ' '.join(text_parts)
            elif isinstance(node, list):
                return ' '.join(extract_text(item) for item in node)
            return ''

        return extract_text(content)
