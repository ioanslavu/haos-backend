from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from identity.models import Identifier


class Work(models.Model):
    """
    Musical work (composition).
    The underlying song that can have multiple recordings.
    Identified by ISWC (International Standard Musical Work Code).
    """

    # Core fields
    title = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Title of the musical work"
    )

    # Optional metadata
    alternate_titles = models.JSONField(
        default=list,
        blank=True,
        help_text="List of alternate titles"
    )

    language = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="Primary language code (ISO 639-1)"
    )

    genre = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Primary genre"
    )

    sub_genre = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Sub-genre"
    )

    year_composed = models.PositiveIntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(1000), MaxValueValidator(9999)],
        help_text="Year the work was composed"
    )

    # Relations to other works (optional)
    translation_of = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='translations',
        help_text="Original work if this is a translation"
    )

    adaptation_of = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='adaptations',
        help_text="Original work if this is an adaptation"
    )

    # Publishing information
    lyrics = models.TextField(
        blank=True,
        null=True,
        help_text="Full lyrics of the work"
    )

    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Internal notes about the work"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['title']
        indexes = [
            models.Index(fields=['title']),
            models.Index(fields=['year_composed']),
            models.Index(fields=['genre']),
        ]

    def __str__(self):
        iswc = self.get_iswc()
        if iswc:
            return f"{self.title} ({iswc})"
        return self.title

    def get_iswc(self):
        """Get ISWC identifier if exists."""
        try:
            identifier = Identifier.objects.get(
                owner_type='work',
                owner_id=self.id,
                scheme='ISWC'
            )
            return identifier.value
        except Identifier.DoesNotExist:
            return None

    @property
    def has_complete_publishing_splits(self):
        """Check if publishing splits (writer/publisher) are complete."""
        from rights.models import Split

        # Check writer splits
        writer_splits = Split.objects.filter(
            scope='work',
            object_id=self.id,
            right_type='writer'
        )
        writer_total = sum(s.share for s in writer_splits)

        # Check publisher splits (only if publishers exist)
        publisher_splits = Split.objects.filter(
            scope='work',
            object_id=self.id,
            right_type='publisher'
        )
        publisher_total = sum(s.share for s in publisher_splits) if publisher_splits.exists() else 0

        # Writers must equal 100%, publishers must equal 100% if they exist
        writer_complete = abs(writer_total - 100) < 0.01
        publisher_complete = not publisher_splits.exists() or abs(publisher_total - 100) < 0.01

        return writer_complete and publisher_complete


class Recording(models.Model):
    """
    A specific recorded version of a Work.
    Identified by ISRC (International Standard Recording Code).
    """

    TYPE_CHOICES = [
        ('audio_master', 'Audio Master'),
        ('music_video', 'Music Video'),
        ('live_audio', 'Live Audio'),
        ('live_video', 'Live Video'),
        ('remix', 'Remix'),
        ('radio_edit', 'Radio Edit'),
        ('acoustic', 'Acoustic Version'),
        ('instrumental', 'Instrumental'),
        ('acapella', 'A Cappella'),
        ('extended', 'Extended Version'),
        ('demo', 'Demo'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('ready', 'Ready'),
        ('approved', 'Approved'),
        ('released', 'Released'),
        ('archived', 'Archived'),
    ]

    # Core fields
    title = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Title of the recording (may differ from work title)"
    )

    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='audio_master',
        db_index=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        db_index=True
    )

    # Link to work (nullable during early creation)
    work = models.ForeignKey(
        Work,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recordings'
    )

    # Technical metadata
    duration_seconds = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Duration in seconds"
    )

    bpm = models.PositiveIntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(20), MaxValueValidator(300)],
        help_text="Beats per minute"
    )

    key = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="Musical key (e.g., C major, A minor)"
    )

    # Recording details
    recording_date = models.DateField(
        blank=True,
        null=True,
        help_text="Date of recording"
    )

    studio = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Recording studio"
    )

    # Version information
    version = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Version description (e.g., 'Radio Edit', 'Extended Mix')"
    )

    # Derivation (for remixes, covers, etc.)
    derived_from = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='derivatives',
        help_text="Original recording if this is derived"
    )

    # Additional metadata
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Internal notes about the recording"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['work', 'type']),
            models.Index(fields=['type', 'status']),
            models.Index(fields=['title']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        isrc = self.get_isrc()
        if isrc:
            return f"{self.title} - {self.get_type_display()} ({isrc})"
        return f"{self.title} - {self.get_type_display()}"

    def get_isrc(self):
        """Get ISRC identifier if exists."""
        try:
            identifier = Identifier.objects.get(
                owner_type='recording',
                owner_id=self.id,
                scheme='ISRC'
            )
            return identifier.value
        except Identifier.DoesNotExist:
            return None

    @property
    def formatted_duration(self):
        """Get duration formatted as MM:SS."""
        if not self.duration_seconds:
            return None
        minutes = self.duration_seconds // 60
        seconds = self.duration_seconds % 60
        return f"{minutes}:{seconds:02d}"

    @property
    def has_complete_master_splits(self):
        """Check if master splits are complete (100%)."""
        from rights.models import Split

        master_splits = Split.objects.filter(
            scope='recording',
            object_id=self.id,
            right_type='master'
        )
        total = sum(s.share for s in master_splits)
        return abs(total - 100) < 0.01


class Release(models.Model):
    """
    A commercial release (album, EP, single).
    Identified by UPC (Universal Product Code).
    """

    TYPE_CHOICES = [
        ('single', 'Single'),
        ('ep', 'EP'),
        ('album', 'Album'),
        ('compilation', 'Compilation'),
        ('live_album', 'Live Album'),
        ('mixtape', 'Mixtape'),
        ('soundtrack', 'Soundtrack'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('released', 'Released'),
        ('cancelled', 'Cancelled'),
    ]

    # Core fields
    title = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Release title"
    )

    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='album',
        db_index=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        db_index=True
    )

    # Release information
    release_date = models.DateField(
        blank=True,
        null=True,
        db_index=True,
        help_text="Official release date"
    )

    catalog_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Label catalog number"
    )

    # Label information
    label_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Label name for this release"
    )

    # Cover art
    artwork_url = models.URLField(
        blank=True,
        null=True,
        help_text="URL to cover artwork"
    )

    # Additional metadata
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Release description"
    )

    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Internal notes"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-release_date', '-created_at']
        indexes = [
            models.Index(fields=['release_date']),
            models.Index(fields=['type', 'status']),
            models.Index(fields=['title']),
        ]

    def __str__(self):
        upc = self.get_upc()
        if upc:
            return f"{self.title} ({upc})"
        return self.title

    def get_upc(self):
        """Get UPC identifier if exists."""
        try:
            identifier = Identifier.objects.get(
                owner_type='release',
                owner_id=self.id,
                scheme='UPC'
            )
            return identifier.value
        except Identifier.DoesNotExist:
            return None

    @property
    def total_duration(self):
        """Total duration of all tracks in seconds."""
        total = self.tracks.aggregate(
            total=models.Sum('recording__duration_seconds')
        )['total']
        return total or 0

    @property
    def formatted_total_duration(self):
        """Total duration formatted as HH:MM:SS or MM:SS."""
        total = self.total_duration
        if not total:
            return None

        hours = total // 3600
        minutes = (total % 3600) // 60
        seconds = total % 60

        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"


class Track(models.Model):
    """
    Represents a recording's position in a release.
    Links Recording to Release with ordering.
    """

    release = models.ForeignKey(
        Release,
        on_delete=models.CASCADE,
        related_name='tracks'
    )

    recording = models.ForeignKey(
        Recording,
        on_delete=models.CASCADE,
        related_name='tracks'
    )

    # Track information
    track_number = models.PositiveIntegerField(
        help_text="Track number in the release"
    )

    disc_number = models.PositiveIntegerField(
        default=1,
        help_text="Disc number (for multi-disc releases)"
    )

    # Version information
    version = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Track-specific version info (e.g., 'Album Version')"
    )

    is_bonus = models.BooleanField(
        default=False,
        help_text="Is this a bonus track?"
    )

    is_hidden = models.BooleanField(
        default=False,
        help_text="Is this a hidden track?"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['release', 'disc_number', 'track_number']
        ordering = ['disc_number', 'track_number']
        indexes = [
            models.Index(fields=['recording', 'release']),
            models.Index(fields=['release', 'disc_number', 'track_number']),
        ]

    def __str__(self):
        if self.disc_number > 1:
            return f"{self.release.title} - {self.disc_number}-{self.track_number:02d}. {self.recording.title}"
        return f"{self.release.title} - {self.track_number:02d}. {self.recording.title}"


class Asset(models.Model):
    """
    Files associated with recordings (audio, video, artwork, etc.).
    """

    KIND_CHOICES = [
        # Audio files
        ('audio_wav', 'WAV File'),
        ('audio_mp3', 'MP3 File'),
        ('audio_flac', 'FLAC File'),
        ('audio_aiff', 'AIFF File'),

        # Video files
        ('video_mov', 'MOV Video'),
        ('video_mp4', 'MP4 Video'),
        ('video_mkv', 'MKV Video'),

        # Supplementary files
        ('artwork', 'Artwork'),
        ('stems', 'Stems'),
        ('lyrics', 'Lyrics'),
        ('subtitles', 'Subtitles'),
        ('sheet_music', 'Sheet Music'),
        ('project_file', 'Project File'),
    ]

    recording = models.ForeignKey(
        Recording,
        on_delete=models.CASCADE,
        related_name='assets'
    )

    kind = models.CharField(
        max_length=20,
        choices=KIND_CHOICES,
        db_index=True
    )

    # File information
    file_name = models.CharField(
        max_length=255,
        help_text="Original file name"
    )

    file_path = models.CharField(
        max_length=500,
        help_text="Path to file (S3, local, etc.)"
    )

    file_size = models.BigIntegerField(
        blank=True,
        null=True,
        help_text="File size in bytes"
    )

    mime_type = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="MIME type of the file"
    )

    # Integrity
    checksum = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text="SHA-256 checksum"
    )

    # Quality information
    sample_rate = models.IntegerField(
        blank=True,
        null=True,
        help_text="Sample rate in Hz (for audio)"
    )

    bit_depth = models.IntegerField(
        blank=True,
        null=True,
        help_text="Bit depth (for audio)"
    )

    bitrate = models.IntegerField(
        blank=True,
        null=True,
        help_text="Bitrate in kbps"
    )

    # Video specific
    resolution = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Video resolution (e.g., 1920x1080)"
    )

    frame_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Frame rate (for video)"
    )

    # Status
    is_master = models.BooleanField(
        default=False,
        help_text="Is this the master file?"
    )

    is_public = models.BooleanField(
        default=False,
        help_text="Can this file be publicly accessed?"
    )

    # Metadata
    uploaded_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_assets'
    )

    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Notes about the asset"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_master', 'kind', 'created_at']
        indexes = [
            models.Index(fields=['recording', 'kind']),
            models.Index(fields=['kind', 'is_master']),
        ]

    def __str__(self):
        return f"{self.recording.title} - {self.get_kind_display()} ({self.file_name})"

    @property
    def formatted_file_size(self):
        """Return human-readable file size."""
        if not self.file_size:
            return None

        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if self.file_size < 1024.0:
                return f"{self.file_size:.2f} {unit}"
            self.file_size /= 1024.0
        return f"{self.file_size:.2f} PB"