from django.db import models
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from catalog.models import Recording, Release


class Publication(models.Model):
    """
    Represents the publication/distribution of a Recording or Release on external platforms.
    Tracks platform links, territories, and status for each publication.
    """

    OBJECT_TYPE_CHOICES = [
        ('recording', 'Recording'),
        ('release', 'Release'),
    ]

    # Platform choices (extensible)
    PLATFORM_CHOICES = [
        # YouTube
        ('youtube_video', 'YouTube Video'),
        ('youtube_music', 'YouTube Music'),
        ('youtube_shorts', 'YouTube Shorts'),
        ('youtube_topic', 'YouTube Topic Channel'),

        # Spotify
        ('spotify_track', 'Spotify Track'),
        ('spotify_album', 'Spotify Album'),
        ('spotify_podcast', 'Spotify Podcast'),

        # Apple
        ('apple_music_track', 'Apple Music Track'),
        ('apple_music_album', 'Apple Music Album'),
        ('itunes_track', 'iTunes Track'),
        ('itunes_album', 'iTunes Album'),

        # Amazon
        ('amazon_music_track', 'Amazon Music Track'),
        ('amazon_music_album', 'Amazon Music Album'),

        # Social Media
        ('tiktok_sound', 'TikTok Sound'),
        ('instagram_audio', 'Instagram Audio'),
        ('facebook_audio', 'Facebook Audio'),
        ('snapchat_sound', 'Snapchat Sound'),

        # Streaming Services
        ('deezer_track', 'Deezer Track'),
        ('deezer_album', 'Deezer Album'),
        ('tidal_track', 'Tidal Track'),
        ('tidal_album', 'Tidal Album'),
        ('soundcloud_track', 'SoundCloud Track'),
        ('bandcamp_track', 'Bandcamp Track'),
        ('bandcamp_album', 'Bandcamp Album'),

        # Other
        ('shazam', 'Shazam'),
        ('audiomack_track', 'Audiomack Track'),
        ('beatport_track', 'Beatport Track'),
        ('traxsource_track', 'Traxsource Track'),
    ]

    STATUS_CHOICES = [
        ('planned', 'Planned'),
        ('submitted', 'Submitted'),
        ('processing', 'Processing'),
        ('live', 'Live'),
        ('private', 'Private'),
        ('blocked', 'Blocked'),
        ('taken_down', 'Taken Down'),
        ('expired', 'Expired'),
    ]

    CHANNEL_CHOICES = [
        ('stream', 'Streaming'),
        ('download', 'Download'),
        ('sync', 'Sync License'),
        ('ugc', 'User Generated Content'),
        ('shorts', 'Shorts/Stories'),
        ('broadcast', 'Broadcast'),
        ('physical', 'Physical Sales'),
        ('other', 'Other'),
    ]

    # Object reference
    object_type = models.CharField(
        max_length=20,
        choices=OBJECT_TYPE_CHOICES,
        db_index=True
    )

    object_id = models.BigIntegerField(
        db_index=True,
        help_text="ID of the Recording or Release"
    )

    # Platform information
    platform = models.CharField(
        max_length=50,
        choices=PLATFORM_CHOICES,
        db_index=True
    )

    url = models.URLField(
        max_length=500,
        validators=[URLValidator()],
        help_text="Full URL to the content on the platform"
    )

    # External identifiers
    external_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_index=True,
        help_text="Platform-specific ID (e.g., Spotify URI, YouTube video ID)"
    )

    content_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Content ID for rights management"
    )

    # Territory and availability
    territory = models.CharField(
        max_length=10,
        default='GLOBAL',
        db_index=True,
        help_text="ISO country code or 'GLOBAL'"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='planned',
        db_index=True
    )

    # Publishing details
    published_at = models.DateTimeField(
        blank=True,
        null=True,
        db_index=True,
        help_text="When the content went live"
    )

    scheduled_for = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Scheduled publication date"
    )

    taken_down_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When the content was taken down"
    )

    # Channel and monetization
    channel = models.CharField(
        max_length=20,
        choices=CHANNEL_CHOICES,
        default='stream',
        help_text="Distribution channel type"
    )

    is_monetized = models.BooleanField(
        default=True,
        help_text="Is monetization enabled?"
    )

    # Ownership and management
    owner_account = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Account/channel that owns this publication"
    )

    distributor = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Distributor used (e.g., DistroKid, CD Baby)"
    )

    # Metrics (optional, can be updated periodically)
    metrics = models.JSONField(
        default=dict,
        blank=True,
        help_text="Platform metrics (views, streams, likes, etc.)"
    )

    last_metrics_update = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When metrics were last updated"
    )

    # Notes and metadata
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Internal notes"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-published_at', '-created_at']
        indexes = [
            models.Index(fields=['object_type', 'object_id']),
            models.Index(fields=['platform', 'territory', 'status']),
            models.Index(fields=['platform', 'external_id']),
            models.Index(fields=['status', 'published_at']),
        ]

    def __str__(self):
        platform_display = self.get_platform_display()
        if self.object_type == 'recording':
            obj = self.get_recording()
        else:
            obj = self.get_release()

        obj_title = obj.title if obj else f"{self.object_type} {self.object_id}"
        return f"{obj_title} on {platform_display} ({self.territory})"

    def clean(self):
        """Validate publication data."""
        # Ensure object exists
        if self.object_type == 'recording':
            if not Recording.objects.filter(id=self.object_id).exists():
                raise ValidationError(f"Recording with ID {self.object_id} does not exist")
        elif self.object_type == 'release':
            if not Release.objects.filter(id=self.object_id).exists():
                raise ValidationError(f"Release with ID {self.object_id} does not exist")

        # Validate platform/object_type combinations
        album_platforms = [
            'spotify_album', 'apple_music_album', 'itunes_album',
            'amazon_music_album', 'deezer_album', 'tidal_album', 'bandcamp_album'
        ]

        track_platforms = [
            'spotify_track', 'apple_music_track', 'itunes_track',
            'amazon_music_track', 'deezer_track', 'tidal_track',
            'soundcloud_track', 'bandcamp_track', 'audiomack_track',
            'beatport_track', 'traxsource_track'
        ]

        if self.object_type == 'release' and self.platform in track_platforms:
            raise ValidationError(f"Platform {self.platform} is for tracks, not releases")

        if self.object_type == 'recording' and self.platform in album_platforms:
            raise ValidationError(f"Platform {self.platform} is for albums/releases, not recordings")

        # Validate dates
        if self.published_at and self.scheduled_for:
            if self.published_at < self.scheduled_for:
                raise ValidationError("Published date cannot be before scheduled date")

    def save(self, *args, **kwargs):
        self.clean()

        # Auto-update status based on dates
        from django.utils import timezone
        now = timezone.now()

        if self.published_at and self.published_at <= now and self.status == 'scheduled':
            self.status = 'live'
        elif self.taken_down_at and self.taken_down_at <= now and self.status == 'live':
            self.status = 'taken_down'

        super().save(*args, **kwargs)

    @property
    def get_recording(self):
        """Get the associated Recording if object_type is 'recording'."""
        if self.object_type == 'recording':
            return Recording.objects.filter(id=self.object_id).first()
        return None

    @property
    def get_release(self):
        """Get the associated Release if object_type is 'release'."""
        if self.object_type == 'release':
            return Release.objects.filter(id=self.object_id).first()
        return None

    @property
    def is_active(self):
        """Check if publication is currently active."""
        return self.status == 'live' and not self.taken_down_at

    @property
    def platform_icon(self):
        """Get icon/emoji for the platform (for UI display)."""
        platform_icons = {
            'youtube_video': '🎬',
            'youtube_music': '🎵',
            'youtube_shorts': '📱',
            'spotify_track': '🟢',
            'spotify_album': '🟢',
            'apple_music_track': '🍎',
            'apple_music_album': '🍎',
            'tiktok_sound': '🎶',
            'instagram_audio': '📷',
            'soundcloud_track': '☁️',
            'bandcamp_track': '🎸',
            'deezer_track': '🎧',
            'tidal_track': '🌊',
        }
        return platform_icons.get(self.platform, '🔗')

    def get_platform_base_url(self):
        """Get the base URL for the platform."""
        platform_urls = {
            'youtube_video': 'https://youtube.com',
            'youtube_music': 'https://music.youtube.com',
            'spotify_track': 'https://open.spotify.com',
            'spotify_album': 'https://open.spotify.com',
            'apple_music_track': 'https://music.apple.com',
            'apple_music_album': 'https://music.apple.com',
            'tiktok_sound': 'https://www.tiktok.com',
            'instagram_audio': 'https://www.instagram.com',
            'soundcloud_track': 'https://soundcloud.com',
            'bandcamp_track': 'https://bandcamp.com',
            'deezer_track': 'https://www.deezer.com',
            'tidal_track': 'https://tidal.com',
        }
        return platform_urls.get(self.platform, '')

    def update_metrics(self, new_metrics):
        """Update metrics data."""
        from django.utils import timezone

        if not isinstance(new_metrics, dict):
            raise ValueError("Metrics must be a dictionary")

        # Merge with existing metrics
        self.metrics.update(new_metrics)
        self.last_metrics_update = timezone.now()
        self.save()

    @classmethod
    def get_active_publications(cls, object_type, object_id):
        """Get all active publications for an object."""
        return cls.objects.filter(
            object_type=object_type,
            object_id=object_id,
            status='live',
            taken_down_at__isnull=True
        )

    @classmethod
    def get_by_platform(cls, platform, territory='GLOBAL'):
        """Get all publications for a specific platform and territory."""
        return cls.objects.filter(
            platform=platform,
            territory__in=[territory, 'GLOBAL'],
            status='live'
        )


class PublicationReport:
    """
    Utility class for generating publication reports.
    """

    @staticmethod
    def get_coverage_report(object_type, object_id):
        """
        Get a coverage report showing which platforms have publications.
        """
        all_platforms = [p[0] for p in Publication.PLATFORM_CHOICES]
        publications = Publication.objects.filter(
            object_type=object_type,
            object_id=object_id
        )

        covered_platforms = set(publications.values_list('platform', flat=True))
        missing_platforms = set(all_platforms) - covered_platforms

        return {
            'total_platforms': len(all_platforms),
            'covered_count': len(covered_platforms),
            'missing_count': len(missing_platforms),
            'coverage_percentage': (len(covered_platforms) / len(all_platforms)) * 100,
            'covered_platforms': list(covered_platforms),
            'missing_platforms': list(missing_platforms),
            'by_status': {
                status: publications.filter(status=status).count()
                for status, _ in Publication.STATUS_CHOICES
            }
        }

    @staticmethod
    def get_territory_report():
        """
        Get a report of publications by territory.
        """
        from django.db.models import Count

        territory_counts = Publication.objects.values('territory').annotate(
            count=Count('id')
        ).order_by('-count')

        return {
            'territories': list(territory_counts),
            'total_territories': territory_counts.count(),
            'global_count': Publication.objects.filter(territory='GLOBAL').count(),
        }