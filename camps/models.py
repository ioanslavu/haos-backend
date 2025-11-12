from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class Camp(models.Model):
    """
    Camp represents a recording camp event with multiple studios and artists.
    Supports soft deletion for preserving history.
    """

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    # Basic Info
    name = models.CharField(
        max_length=255,
        help_text="Camp name"
    )

    start_date = models.DateField(
        null=True,
        blank=True,
        help_text="Camp start date (optional)"
    )

    end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Camp end date (optional)"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        db_index=True,
        help_text="Current status of the camp"
    )

    # Metadata
    department = models.ForeignKey(
        'api.Department',
        on_delete=models.PROTECT,
        related_name='camps',
        null=True,
        blank=True,
        help_text="Department managing this camp (optional)"
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='camps_created',
        help_text="User who created this camp"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the camp was created"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When the camp was last updated"
    )

    # Soft Delete
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="When the camp was soft-deleted (null = active)"
    )

    class Meta:
        verbose_name = "Camp"
        verbose_name_plural = "Camps"
        ordering = ['-start_date', '-created_at']
        indexes = [
            models.Index(fields=['deleted_at']),
            models.Index(fields=['start_date']),
            models.Index(fields=['status']),
            models.Index(fields=['department', '-start_date']),
        ]

    def __str__(self):
        return self.name

    def soft_delete(self):
        """Soft delete this camp"""
        self.deleted_at = timezone.now()
        self.save()

    @property
    def is_deleted(self):
        """Check if camp is soft-deleted"""
        return self.deleted_at is not None

    @property
    def studios_count(self):
        """Get count of studios in this camp"""
        return self.studios.count()


class CampStudio(models.Model):
    """
    Studio within a camp. Studios are not global entities,
    they exist only within the context of a specific camp.
    """

    camp = models.ForeignKey(
        Camp,
        on_delete=models.CASCADE,
        related_name='studios',
        help_text="Parent camp"
    )

    # Basic Studio Info
    name = models.CharField(
        max_length=255,
        help_text="Studio name (e.g., 'Studio A', 'Mastering Room')"
    )

    # Location (all optional)
    location = models.CharField(
        max_length=255,
        blank=True,
        help_text="Studio location name (e.g., 'Abbey Road Studios')"
    )

    city = models.CharField(
        max_length=100,
        blank=True,
        help_text="City where studio is located"
    )

    country = models.CharField(
        max_length=100,
        default='Romania',
        blank=True,
        help_text="Country where studio is located"
    )

    # Schedule (all optional)
    hours = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        help_text="Total hours scheduled (e.g., 8.5)"
    )

    sessions = models.IntegerField(
        null=True,
        blank=True,
        help_text="Number of sessions scheduled"
    )

    # Order for display
    order = models.IntegerField(
        default=0,
        help_text="Order for sorting studios within camp"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Camp Studio"
        verbose_name_plural = "Camp Studios"
        ordering = ['order', 'id']
        indexes = [
            models.Index(fields=['camp', 'order']),
        ]

    def __str__(self):
        return f"{self.camp.name} - {self.name}"


class CampStudioArtist(models.Model):
    """
    Junction table connecting studios to artists (entities).
    Tracks whether artist is internal or external.
    """

    studio = models.ForeignKey(
        CampStudio,
        on_delete=models.CASCADE,
        related_name='studio_artists',
        help_text="Studio this artist is assigned to"
    )

    artist = models.ForeignKey(
        'identity.Entity',
        on_delete=models.PROTECT,
        related_name='camp_studios',
        help_text="Artist entity"
    )

    is_internal = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Is this artist internal (signed) or external (contractor)?"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Camp Studio Artist"
        verbose_name_plural = "Camp Studio Artists"
        unique_together = ['studio', 'artist']
        ordering = ['-is_internal', 'artist__display_name']
        indexes = [
            models.Index(fields=['studio', 'is_internal']),
        ]

    def __str__(self):
        artist_type = "Internal" if self.is_internal else "External"
        return f"{self.studio} - {self.artist.display_name} ({artist_type})"
