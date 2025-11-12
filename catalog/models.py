from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth import get_user_model
from identity.models import Identifier

User = get_user_model()


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


# ============================================================================
# SONG WORKFLOW SYSTEM
# ============================================================================

WORKFLOW_STAGES = [
    ('draft', 'Draft'),
    ('publishing', 'Publishing'),
    ('label_recording', 'Label - Recording'),
    ('marketing_assets', 'Marketing - Assets'),
    ('label_review', 'Label - Review'),
    ('ready_for_digital', 'Ready for Digital'),
    ('digital_distribution', 'Digital Distribution'),
    ('released', 'Released'),
    ('archived', 'Archived'),
]


class Song(models.Model):
    """
    Song workflow orchestrator for HaHaHa Production's record label.
    Manages the business process across departments (Publishing, Label, Marketing, Digital).
    Wraps technical entities (Work, Recording, Release) with workflow state.
    """

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    # ============ BASIC INFO ============
    title = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Song title"
    )

    artist = models.ForeignKey(
        'identity.Entity',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='songs',
        help_text="Primary artist entity (can be TBD initially)"
    )

    genre = models.CharField(
        max_length=100,
        blank=True,
        help_text="Primary genre"
    )

    language = models.CharField(
        max_length=50,
        default='en',
        help_text="Primary language code"
    )

    duration = models.DurationField(
        null=True,
        blank=True,
        help_text="Song duration (computed from recording)"
    )

    # ============ WORKFLOW STATE ============
    stage = models.CharField(
        max_length=50,
        choices=WORKFLOW_STAGES,
        default='draft',
        db_index=True,
        help_text="Current workflow stage"
    )

    assigned_department = models.ForeignKey(
        'api.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_songs',
        help_text="Department currently responsible for this song"
    )

    assigned_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_songs',
        help_text="Specific user assigned to work on this song"
    )

    # ============ PRIORITIES & DEADLINES ============
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='normal',
        db_index=True,
        help_text="Song priority level"
    )

    target_release_date = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Target release date for this song"
    )

    stage_deadline = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Deadline for completing current stage"
    )

    # ============ RELATIONSHIPS ============
    # Per decision: 1 Song = 1 Work (no M2M for works)
    work = models.ForeignKey(
        Work,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='songs',
        help_text="Associated musical work (composition)"
    )

    # Per decision: 1 Song can have multiple Recordings (M2M)
    recordings = models.ManyToManyField(
        Recording,
        related_name='songs',
        blank=True,
        help_text="Associated recordings"
    )

    # 1 Song can have multiple Releases (M2M)
    releases = models.ManyToManyField(
        Release,
        related_name='songs',
        blank=True,
        help_text="Associated releases"
    )

    # Featured artists (M2M through SongArtist)
    featured_artists = models.ManyToManyField(
        'identity.Entity',
        through='SongArtist',
        related_name='featured_songs',
        blank=True,
        help_text="Featured artists with roles"
    )

    # ============ OWNERSHIP ============
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='songs_created',
        help_text="User who created this song"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ============ STAGE TRACKING ============
    stage_entered_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the song entered the current stage"
    )

    stage_updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='song_stage_updates',
        help_text="Last user to update the stage"
    )

    # ============ COMPUTED FIELDS ============
    checklist_progress = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Percentage of checklist items complete (0-100)"
    )

    is_overdue = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether the song is past its stage deadline"
    )

    days_in_current_stage = models.IntegerField(
        default=0,
        help_text="Number of days in current stage"
    )

    # ============ STATUS FLAGS ============
    is_archived = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether the song has been archived"
    )

    is_blocked = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether the song is manually flagged as blocked"
    )

    blocked_reason = models.TextField(
        blank=True,
        help_text="Reason why the song is blocked"
    )

    # ============ METADATA ============
    internal_notes = models.TextField(
        blank=True,
        help_text="Internal notes visible to all departments"
    )

    external_notes = models.TextField(
        blank=True,
        help_text="Notes for external partners"
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['stage', 'assigned_department']),
            models.Index(fields=['target_release_date']),
            models.Index(fields=['is_archived', 'stage']),
            models.Index(fields=['priority', 'stage']),
            models.Index(fields=['created_by']),
            models.Index(fields=['is_overdue']),
        ]
        verbose_name = "Song"
        verbose_name_plural = "Songs"

    def __str__(self):
        return f"{self.title} - {self.get_stage_display()}"

    def can_transition_to(self, target_stage, user):
        """
        Check if user can transition song to target stage.

        Args:
            target_stage (str): Target stage code
            user (User): User attempting the transition

        Returns:
            tuple: (can_transition: bool, reason: str)
        """
        from api.models import UserProfile

        # Admin override
        try:
            if user.profile.is_admin:
                return (True, "Admin override")
        except UserProfile.DoesNotExist:
            return (False, "User has no profile")

        # Check if transition is valid
        current_stage = self.stage or 'draft'  # Treat null stage as draft
        VALID_TRANSITIONS = {
            'draft': ['publishing', 'archived'],
            'publishing': ['label_recording', 'archived'],
            'label_recording': ['marketing_assets', 'archived'],
            'marketing_assets': ['label_review', 'archived'],
            'label_review': ['ready_for_digital', 'marketing_assets', 'archived'],
            'ready_for_digital': ['digital_distribution', 'archived'],
            'digital_distribution': ['released', 'archived'],
            'released': ['archived'],
        }

        allowed_next_stages = VALID_TRANSITIONS.get(current_stage, [])
        if target_stage not in allowed_next_stages:
            return (False, f"Cannot transition from {current_stage} to {target_stage}")

        # Check if checklist is complete
        checklist_progress = self.calculate_checklist_progress()
        if checklist_progress < 100:
            return (False, f"Checklist incomplete ({checklist_progress:.0f}% complete)")

        return (True, "Transition allowed")

    def get_current_checklist(self):
        """
        Get checklist items for current stage.

        Returns:
            QuerySet: SongChecklistItem queryset filtered by current stage
        """
        current_stage = self.stage or 'draft'  # Treat null stage as draft
        return self.checklist_items.filter(stage=current_stage)

    def calculate_checklist_progress(self):
        """
        Calculate percentage of required checklist items complete.

        Returns:
            float: Percentage complete (0-100)
        """
        items = self.get_current_checklist().filter(required=True)
        if not items.exists():
            return 100.0
        completed = items.filter(is_complete=True).count()
        return (completed / items.count()) * 100

    def update_computed_fields(self):
        """Update computed fields (checklist_progress, is_overdue, days_in_current_stage)."""
        # Update checklist progress
        self.checklist_progress = self.calculate_checklist_progress()

        # Update is_overdue
        if self.stage_deadline:
            self.is_overdue = timezone.now().date() > self.stage_deadline
        else:
            self.is_overdue = False

        # Update days in current stage
        if self.stage_entered_at:
            delta = timezone.now() - self.stage_entered_at
            self.days_in_current_stage = delta.days
        else:
            self.days_in_current_stage = 0

        self.save()

    def get_all_artists(self):
        """
        Return list of all artists (primary + featured).

        Returns:
            list: List of dicts with artist info {id, name, role, is_primary, order}
        """
        artists = []

        # Add primary artist first
        if self.artist:
            artists.append({
                'id': self.artist.id,
                'name': self.artist.display_name,
                'role': 'primary',
                'is_primary': True,
                'order': -1,
            })

        # Add featured artists
        for credit in self.artist_credits.select_related('artist').all():
            artists.append({
                'id': credit.artist.id,
                'name': credit.artist.display_name,
                'role': credit.role,
                'is_primary': False,
                'order': credit.order,
            })

        # Sort: primary first, then by order
        return sorted(artists, key=lambda x: (not x['is_primary'], x['order']))

    def add_featured_artist(self, artist, role='featured', order=None):
        """
        Add a featured artist to the song.

        Args:
            artist: Entity instance (artist)
            role: Artist role (featured, remixer, producer, etc.)
            order: Display order (None = auto-increment)

        Returns:
            SongArtist: Created artist credit instance
        """
        if order is None:
            # Auto-increment: get max order + 1
            max_order = self.artist_credits.aggregate(
                models.Max('order')
            )['order__max'] or 0
            order = max_order + 1

        return SongArtist.objects.create(
            song=self,
            artist=artist,
            role=role,
            order=order
        )

    @property
    def display_artists(self):
        """
        Return formatted artist string.

        Examples:
            "Artist A" (only primary)
            "Artist A feat. Artist B" (primary + 1 featured)
            "Artist A feat. Artist B, Artist C" (primary + 2 featured)

        Returns:
            str: Formatted artist string
        """
        all_artists = self.get_all_artists()

        if not all_artists:
            return "Unknown Artist"

        primary = next((a for a in all_artists if a['is_primary']), None)
        featured = [a for a in all_artists if not a['is_primary']]

        if not featured:
            return primary['name'] if primary else "Unknown Artist"

        primary_name = primary['name'] if primary else all_artists[0]['name']
        featured_names = ', '.join(a['name'] for a in featured)
        return f"{primary_name} feat. {featured_names}"


class SongArtist(models.Model):
    """
    Through model for featured artists on songs.
    Allows songs to have multiple artists with roles and ordering.
    """

    ROLE_CHOICES = [
        ('featured', 'Featured Artist'),
        ('remixer', 'Remixer'),
        ('producer', 'Producer'),
        ('composer', 'Composer'),
        ('featuring', 'Featuring'),
    ]

    song = models.ForeignKey(
        Song,
        on_delete=models.CASCADE,
        related_name='artist_credits',
        help_text="Song this artist credit belongs to"
    )

    artist = models.ForeignKey(
        'identity.Entity',
        on_delete=models.CASCADE,
        related_name='song_credits',
        help_text="Artist entity"
    )

    role = models.CharField(
        max_length=50,
        choices=ROLE_CHOICES,
        default='featured',
        help_text="Artist role on this song"
    )

    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order for featured artist billing (0 = first)"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'id']
        unique_together = ['song', 'artist', 'role']
        verbose_name = "Song Artist"
        verbose_name_plural = "Song Artists"
        indexes = [
            models.Index(fields=['song', 'order']),
        ]

    def __str__(self):
        return f"{self.artist.name} - {self.get_role_display()} on {self.song.title}"


class SongChecklistItem(models.Model):
    """
    Checklist items for song workflow validation.
    Defines requirements that must be met before stage transitions.
    """

    VALIDATION_TYPE_CHOICES = [
        ('manual', 'Manual Check'),
        ('auto_field_exists', 'Auto - Field Exists'),
        ('auto_file_exists', 'Auto - File Uploaded'),
        ('auto_split_validated', 'Auto - Splits = 100%'),
        ('auto_entity_exists', 'Auto - Entity Created'),
        ('auto_count_minimum', 'Auto - Minimum Count'),
        ('auto_custom', 'Auto - Custom Function'),
    ]

    # ============ RELATIONSHIPS ============
    song = models.ForeignKey(
        Song,
        on_delete=models.CASCADE,
        related_name='checklist_items',
        help_text="Associated song"
    )

    recording = models.ForeignKey(
        'Recording',
        on_delete=models.CASCADE,
        related_name='checklist_items',
        null=True,
        blank=True,
        help_text="Associated recording (if this is a recording-specific checklist item)"
    )

    # ============ CHECKLIST DEFINITION ============
    stage = models.CharField(
        max_length=50,
        choices=WORKFLOW_STAGES,
        db_index=True,
        help_text="Workflow stage this item belongs to"
    )

    category = models.CharField(
        max_length=100,
        help_text="Category (e.g., 'Legal', 'Audio', 'Metadata')"
    )

    item_name = models.CharField(
        max_length=255,
        help_text="Name of the checklist item"
    )

    description = models.TextField(
        help_text="Detailed description of the requirement"
    )

    order = models.IntegerField(
        default=0,
        help_text="Display order within stage"
    )

    # ============ VALIDATION RULES ============
    required = models.BooleanField(
        default=True,
        help_text="Must complete to transition to next stage"
    )

    validation_type = models.CharField(
        max_length=50,
        choices=VALIDATION_TYPE_CHOICES,
        default='manual',
        help_text="How to validate this item"
    )

    validation_rule = models.JSONField(
        null=True,
        blank=True,
        help_text="Configuration for auto validators (JSON)"
    )

    # ============ COMPLETION STATUS ============
    is_complete = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether this item is complete"
    )

    completed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='completed_checklist_items',
        help_text="User who completed this item"
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this item was completed"
    )

    # ============ HELP & GUIDANCE ============
    help_text = models.TextField(
        blank=True,
        help_text="Instructions on how to complete this item"
    )

    help_link = models.URLField(
        blank=True,
        help_text="Link to documentation or tutorial"
    )

    # ============ ASSIGNMENT ============
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_checklist_items',
        help_text="User assigned to complete this item"
    )

    # ============ BLOCKING ============
    is_blocker = models.BooleanField(
        default=False,
        help_text="Blocks stage transition if incomplete"
    )

    depends_on = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dependent_items',
        help_text="This item depends on another item being complete"
    )

    class Meta:
        ordering = ['order', 'id']
        indexes = [
            models.Index(fields=['song', 'stage', 'required']),
            models.Index(fields=['is_complete']),
        ]
        verbose_name = "Song Checklist Item"
        verbose_name_plural = "Song Checklist Items"

    def __str__(self):
        return f"{self.song.title} - {self.stage} - {self.item_name}"

    def validate(self):
        """
        Run validation based on validation_type.

        Returns:
            bool: True if validation passes
        """
        if self.validation_type == 'manual':
            return self.is_complete

        elif self.validation_type == 'auto_entity_exists':
            # Check if Work/Recording/Release exists
            entity = self.validation_rule.get('entity') if self.validation_rule else None
            if entity == 'work':
                return self.song.work is not None
            elif entity == 'recording':
                return self.song.recordings.exists()
            elif entity == 'release':
                return self.song.releases.exists()

        elif self.validation_type == 'auto_field_exists':
            # Check if specified field has value
            if self.validation_rule:
                entity = self.validation_rule.get('entity')
                field = self.validation_rule.get('field')
                if entity and field:
                    if entity == 'work' and self.song.work:
                        return bool(getattr(self.song.work, field, None))
                    elif entity == 'recording':
                        for recording in self.song.recordings.all():
                            if getattr(recording, field, None):
                                return True

        elif self.validation_type == 'auto_split_validated':
            # Check if splits = 100%
            if self.validation_rule:
                entity = self.validation_rule.get('entity')
                if entity == 'work' and self.song.work:
                    return self.song.work.has_complete_publishing_splits
                elif entity == 'recording':
                    # Check if at least one recording has complete splits
                    for recording in self.song.recordings.all():
                        if recording.has_complete_master_splits:
                            return True

        elif self.validation_type == 'auto_count_minimum':
            # Check minimum count
            if self.validation_rule:
                entity = self.validation_rule.get('entity')
                min_count = self.validation_rule.get('min_count', 1)
                if entity == 'recording':
                    return self.song.recordings.count() >= min_count
                elif entity == 'release':
                    return self.song.releases.count() >= min_count

        return False


class SongStageTransition(models.Model):
    """
    Audit log for song stage transitions.
    Tracks all changes to song workflow stage for accountability.
    """

    TRANSITION_TYPE_CHOICES = [
        ('forward', 'Forward Progress'),
        ('backward', 'Sent Back'),
        ('skip', 'Skipped Stage'),
        ('forced', 'Admin Override'),
    ]

    song = models.ForeignKey(
        Song,
        on_delete=models.CASCADE,
        related_name='stage_transitions',
        help_text="Associated song"
    )

    from_stage = models.CharField(
        max_length=50,
        choices=WORKFLOW_STAGES,
        help_text="Previous stage"
    )

    to_stage = models.CharField(
        max_length=50,
        choices=WORKFLOW_STAGES,
        help_text="New stage"
    )

    transitioned_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='song_transitions',
        help_text="User who performed the transition"
    )

    transitioned_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the transition occurred"
    )

    transition_type = models.CharField(
        max_length=50,
        choices=TRANSITION_TYPE_CHOICES,
        default='forward',
        help_text="Type of transition"
    )

    notes = models.TextField(
        blank=True,
        help_text="Notes about why transition happened"
    )

    checklist_completion_at_transition = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Checklist completion percentage at time of transition"
    )

    # If rejection/sent back
    rejection_reason = models.TextField(
        blank=True,
        help_text="Reason for rejection (if applicable)"
    )

    rejection_category = models.CharField(
        max_length=100,
        blank=True,
        help_text="Category of rejection (e.g., 'Audio Quality', 'Legal Issue')"
    )

    class Meta:
        ordering = ['-transitioned_at']
        indexes = [
            models.Index(fields=['song', 'transitioned_at']),
            models.Index(fields=['transition_type']),
        ]
        verbose_name = "Song Stage Transition"
        verbose_name_plural = "Song Stage Transitions"

    def __str__(self):
        return f"{self.song.title} - {self.from_stage} → {self.to_stage}"


class SongStageStatus(models.Model):
    """
    Tracks the status of each workflow stage for a song.
    Every song has exactly 8 SongStageStatus records (one per stage).
    Supports multiple stages being 'in_progress' simultaneously for parallel workflows.
    """

    STAGE_STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('blocked', 'Blocked'),
    ]

    song = models.ForeignKey(
        Song,
        on_delete=models.CASCADE,
        related_name='stage_statuses',
        help_text="Associated song"
    )

    stage = models.CharField(
        max_length=50,
        choices=WORKFLOW_STAGES,
        help_text="Workflow stage"
    )

    status = models.CharField(
        max_length=20,
        choices=STAGE_STATUS_CHOICES,
        default='not_started',
        db_index=True,
        help_text="Current status of this stage"
    )

    # Timestamps for analytics and time tracking
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When work on this stage began"
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this stage was completed"
    )

    # Blocking information
    blocked_reason = models.TextField(
        blank=True,
        help_text="Why this stage is blocked (if status=blocked)"
    )

    # Stage-specific notes
    notes = models.TextField(
        blank=True,
        help_text="Notes about work in this stage"
    )

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('song', 'stage')
        ordering = ['song', 'stage']
        indexes = [
            models.Index(fields=['song', 'status']),
            models.Index(fields=['status']),
        ]
        verbose_name = "Song Stage Status"
        verbose_name_plural = "Song Stage Statuses"

    def __str__(self):
        return f"{self.song.title} - {self.get_stage_display()} ({self.get_status_display()})"

    @property
    def days_in_status(self):
        """Calculate days in current status"""
        if self.status == 'in_progress' and self.started_at:
            return (timezone.now() - self.started_at).days
        elif self.status == 'completed' and self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).days
        return None


class SongAsset(models.Model):
    """
    Marketing assets for songs (artwork, promotional materials).
    Per decision: Uses Google Drive URLs instead of file uploads.
    """

    ASSET_TYPE_CHOICES = [
        ('cover_art', 'Cover Artwork'),
        ('back_cover', 'Back Cover'),
        ('press_photo', 'Press Photo'),
        ('promo_graphic', 'Promotional Graphic'),
        ('social_media', 'Social Media Asset'),
        ('lyric_video', 'Lyric Video'),
        ('visualizer', 'Visualizer'),
        ('other', 'Other'),
    ]

    REVIEW_STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('revision_requested', 'Needs Revision'),
    ]

    song = models.ForeignKey(
        Song,
        on_delete=models.CASCADE,
        related_name='assets',
        help_text="Associated song"
    )

    asset_type = models.CharField(
        max_length=50,
        choices=ASSET_TYPE_CHOICES,
        db_index=True,
        help_text="Type of asset"
    )

    # Per decision: Google Drive URL instead of FileField
    google_drive_url = models.URLField(
        help_text="Google Drive URL to the asset file"
    )

    # Still track file metadata
    file_format = models.CharField(
        max_length=20,
        blank=True,
        help_text="File format (jpg, png, mp4, etc.)"
    )

    # Image-specific dimensions
    width = models.IntegerField(
        null=True,
        blank=True,
        help_text="Width in pixels (for images)"
    )

    height = models.IntegerField(
        null=True,
        blank=True,
        help_text="Height in pixels (for images)"
    )

    # Metadata
    title = models.CharField(
        max_length=255,
        blank=True,
        help_text="Asset title"
    )

    description = models.TextField(
        blank=True,
        help_text="Asset description"
    )

    # Upload info
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='uploaded_song_assets',
        help_text="User who uploaded this asset"
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the asset was uploaded"
    )

    # Review status
    review_status = models.CharField(
        max_length=20,
        choices=REVIEW_STATUS_CHOICES,
        default='pending',
        db_index=True,
        help_text="Review status"
    )

    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_song_assets',
        help_text="User who reviewed this asset"
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the asset was reviewed"
    )

    review_notes = models.TextField(
        blank=True,
        help_text="Review feedback or notes"
    )

    # Usage
    is_primary = models.BooleanField(
        default=False,
        help_text="Primary asset for this type (e.g., primary cover art)"
    )

    class Meta:
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['song', 'asset_type']),
            models.Index(fields=['review_status']),
        ]
        verbose_name = "Song Asset"
        verbose_name_plural = "Song Assets"

    def __str__(self):
        return f"{self.song.title} - {self.get_asset_type_display()}"

    @property
    def dimensions(self):
        """Return dimensions as WxH string."""
        if self.width and self.height:
            return f"{self.width}x{self.height}"
        return None


class SongNote(models.Model):
    """
    Activity log and notes for songs.
    Supports sales pitch tracking and department-specific visibility.
    """

    NOTE_TYPE_CHOICES = [
        ('comment', 'Comment'),
        ('status_update', 'Status Update'),
        ('sales_pitch', 'Sales Pitch'),
        ('feedback', 'Feedback'),
        ('system', 'System Note'),
    ]

    PITCH_OUTCOME_CHOICES = [
        ('interested', 'Interested'),
        ('passed', 'Passed'),
        ('pending', 'Pending'),
        ('deal_made', 'Deal Made'),
    ]

    song = models.ForeignKey(
        Song,
        on_delete=models.CASCADE,
        related_name='notes',
        help_text="Associated song"
    )

    author = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='song_notes',
        help_text="Author of the note"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When the note was created"
    )

    note_type = models.CharField(
        max_length=50,
        choices=NOTE_TYPE_CHOICES,
        default='comment',
        db_index=True,
        help_text="Type of note"
    )

    content = models.TextField(
        help_text="Note content"
    )

    # Sales-specific fields
    pitched_to_artist = models.CharField(
        max_length=255,
        blank=True,
        help_text="Artist the work was pitched to"
    )

    pitch_outcome = models.CharField(
        max_length=50,
        choices=PITCH_OUTCOME_CHOICES,
        blank=True,
        help_text="Outcome of the sales pitch"
    )

    # Visibility
    visible_to_departments = models.ManyToManyField(
        'api.Department',
        blank=True,
        related_name='visible_song_notes',
        help_text="Departments that can see this note (empty = all)"
    )

    is_internal = models.BooleanField(
        default=True,
        help_text="Internal vs external note"
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['song', 'created_at']),
            models.Index(fields=['note_type']),
        ]
        verbose_name = "Song Note"
        verbose_name_plural = "Song Notes"

    def __str__(self):
        return f"{self.song.title} - {self.get_note_type_display()} by {self.author.email}"


class SongAlert(models.Model):
    """
    In-app notifications for song workflow events.
    Per decision: In-app only (no email/SMS).
    """

    ALERT_TYPE_CHOICES = [
        ('stage_transition', 'Stage Transition'),
        ('assignment', 'Assigned to You'),
        ('deadline_approaching', 'Deadline Approaching'),
        ('overdue', 'Overdue'),
        ('asset_submitted', 'Assets Submitted'),
        ('asset_approved', 'Assets Approved'),
        ('asset_rejected', 'Assets Rejected'),
        ('ready_for_review', 'Ready for Review'),
        ('sent_to_digital', 'Sent to Digital'),
        ('checklist_incomplete', 'Checklist Item Incomplete'),
        ('blocking_issue', 'Blocking Issue'),
    ]

    PRIORITY_CHOICES = [
        ('info', 'Info'),
        ('important', 'Important'),
        ('urgent', 'Urgent'),
    ]

    song = models.ForeignKey(
        Song,
        on_delete=models.CASCADE,
        related_name='alerts',
        help_text="Associated song"
    )

    alert_type = models.CharField(
        max_length=50,
        choices=ALERT_TYPE_CHOICES,
        db_index=True,
        help_text="Type of alert"
    )

    target_department = models.ForeignKey(
        'api.Department',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='song_alerts',
        help_text="Target department (if applicable)"
    )

    target_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='song_alerts',
        help_text="Target user (if applicable)"
    )

    title = models.CharField(
        max_length=255,
        help_text="Alert title"
    )

    message = models.TextField(
        help_text="Alert message"
    )

    action_url = models.CharField(
        max_length=500,
        blank=True,
        help_text="Link to song detail page"
    )

    action_label = models.CharField(
        max_length=100,
        blank=True,
        help_text="Action button label (e.g., 'Review Now')"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When the alert was created"
    )

    is_read = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether the alert has been read"
    )

    read_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the alert was read"
    )

    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='info',
        db_index=True,
        help_text="Alert priority level"
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['target_department', 'is_read']),
            models.Index(fields=['target_user', 'is_read']),
            models.Index(fields=['alert_type', 'created_at']),
        ]
        verbose_name = "Song Alert"
        verbose_name_plural = "Song Alerts"

    def __str__(self):
        target = self.target_user or self.target_department or "No target"
        return f"{self.song.title} - {self.get_alert_type_display()} → {target}"


class AlertConfiguration(models.Model):
    """
    Configurable settings for Song Workflow alerts.

    Allows admins to control when and how alerts are generated,
    without needing to modify code or Celery schedules.
    """

    ALERT_TYPE_CHOICES = [
        ('overdue', 'Overdue Songs'),
        ('deadline_approaching', 'Deadline Approaching'),
        ('release_approaching', 'Release Approaching'),
        ('checklist_incomplete', 'Checklist Incomplete'),
    ]

    alert_type = models.CharField(
        max_length=50,
        choices=ALERT_TYPE_CHOICES,
        unique=True,
        help_text="Type of alert to configure"
    )

    enabled = models.BooleanField(
        default=True,
        help_text="Enable or disable this alert type"
    )

    # Timing configuration
    days_threshold = models.IntegerField(
        null=True,
        blank=True,
        help_text="Number of days threshold (e.g., 2 for 'deadline in 2 days', 7 for 'release in 7 days')"
    )

    schedule_description = models.CharField(
        max_length=255,
        blank=True,
        help_text="Human-readable schedule description (e.g., 'Daily at midnight')"
    )

    # Notification targets
    notify_assigned_user = models.BooleanField(
        default=True,
        help_text="Send alert to the assigned user"
    )

    notify_department_managers = models.BooleanField(
        default=True,
        help_text="Send alert to department managers"
    )

    notify_song_creator = models.BooleanField(
        default=False,
        help_text="Send alert to song creator"
    )

    # Alert properties
    priority = models.CharField(
        max_length=20,
        choices=[
            ('info', 'Info'),
            ('important', 'Important'),
            ('urgent', 'Urgent'),
        ],
        default='important',
        help_text="Alert priority level"
    )

    # Customizable message templates
    title_template = models.CharField(
        max_length=255,
        help_text="Alert title template (supports {song_title}, {days}, {deadline}, etc.)"
    )

    message_template = models.TextField(
        help_text="Alert message template (supports same variables as title)"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alert_configs_updated',
        help_text="Last user who updated this configuration"
    )

    class Meta:
        ordering = ['alert_type']
        verbose_name = "Alert Configuration"
        verbose_name_plural = "Alert Configurations"

    def __str__(self):
        status = "Enabled" if self.enabled else "Disabled"
        return f"{self.get_alert_type_display()} - {status}"