from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

User = get_user_model()


class Task(models.Model):
    """
    Task management for campaigns, entities, and contracts.
    Supports department-specific workflows and task types.
    """

    STATUS_CHOICES = [
        ('todo', 'To Do'),
        ('in_progress', 'In Progress'),
        ('blocked', 'Blocked'),
        ('review', 'In Review'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ]

    PRIORITY_CHOICES = [
        (1, 'Low'),
        (2, 'Normal'),
        (3, 'High'),
        (4, 'Urgent'),
    ]

    TASK_TYPE_CHOICES = [
        # General tasks
        ('general', 'General Task'),
        ('follow_up', 'Follow-up'),
        ('review', 'Review'),
        ('approval', 'Approval Required'),

        # Digital department tasks
        ('campaign_setup', 'Campaign Setup'),
        ('content_creation', 'Content Creation'),
        ('performance_review', 'Performance Review'),
        ('report_delivery', 'Report Delivery'),
        ('ad_optimization', 'Ad Optimization'),
        ('platform_setup', 'Platform Setup'),

        # Sales tasks
        ('proposal', 'Proposal Creation'),
        ('negotiation', 'Negotiation'),
        ('contract_prep', 'Contract Preparation'),
        ('closing', 'Deal Closing'),

        # Creative tasks
        ('recording', 'Recording Session'),
        ('mixing', 'Mixing/Mastering'),
        ('video_production', 'Video Production'),
        ('artwork', 'Artwork Design'),

        # Publishing tasks
        ('registration', 'Work Registration'),
        ('royalty_collection', 'Royalty Collection'),
        ('statement_review', 'Statement Review'),
    ]

    # Core fields
    title = models.CharField(
        max_length=200,
        help_text="Task title/description"
    )

    description = models.TextField(
        blank=True,
        help_text="Detailed task description and requirements"
    )

    task_type = models.CharField(
        max_length=50,
        choices=TASK_TYPE_CHOICES,
        default='general',
        db_index=True,
        help_text="Type of task for categorization and workflows"
    )

    # Polymorphic relationships - task can be linked to multiple entities
    campaign = models.ForeignKey(
        'campaigns.Campaign',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='tasks',
        help_text="Campaign this task is associated with"
    )

    entity = models.ForeignKey(
        'identity.Entity',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='tasks',
        help_text="Entity (client/artist/brand) this task is associated with"
    )

    contract = models.ForeignKey(
        'contracts.Contract',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='tasks',
        help_text="Contract this task is associated with"
    )

    # Assignment and ownership
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks',
        help_text="User assigned to this task"
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_tasks',
        help_text="User who created this task"
    )

    department = models.ForeignKey(
        'api.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks',
        help_text="Department this task belongs to"
    )

    # Status and priority
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='todo',
        db_index=True,
        help_text="Current status of the task"
    )

    priority = models.IntegerField(
        choices=PRIORITY_CHOICES,
        default=2,
        db_index=True,
        help_text="Task priority level"
    )

    # Dates and deadlines
    due_date = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Task deadline"
    )

    reminder_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When to send a reminder for this task"
    )

    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When work on this task began"
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this task was completed"
    )

    # Task dependencies
    parent_task = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subtasks',
        help_text="Parent task if this is a subtask"
    )

    blocks_tasks = models.ManyToManyField(
        'self',
        symmetrical=False,
        blank=True,
        related_name='blocked_by',
        help_text="Tasks that this task blocks"
    )

    # Additional metadata
    estimated_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Estimated hours to complete this task"
    )

    actual_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Actual hours spent on this task"
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Department or task-specific metadata"
    )

    notes = models.TextField(
        blank=True,
        help_text="Additional notes or comments"
    )

    # Tracking
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-priority', 'due_date', '-created_at']
        indexes = [
            models.Index(fields=['status', 'priority', 'due_date']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['department', 'status']),
            models.Index(fields=['campaign', 'status']),
            models.Index(fields=['entity', 'status']),
            models.Index(fields=['due_date', 'status']),
            models.Index(fields=['task_type', 'status']),
        ]
        verbose_name = 'Task'
        verbose_name_plural = 'Tasks'

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        """Auto-update timestamps based on status changes"""
        if self.status == 'in_progress' and not self.started_at:
            self.started_at = timezone.now()
        elif self.status == 'done' and not self.completed_at:
            self.completed_at = timezone.now()
        elif self.status not in ['done', 'cancelled'] and self.completed_at:
            self.completed_at = None

        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        """Check if task is overdue"""
        if self.due_date and self.status not in ['done', 'cancelled']:
            return timezone.now() > self.due_date
        return False

    @property
    def is_blocked(self):
        """Check if task is blocked by other tasks"""
        return self.blocked_by.filter(status__in=['todo', 'in_progress', 'blocked']).exists()


class Activity(models.Model):
    """
    Activity and communication log for CRM entities.
    Tracks all interactions with clients, artists, and other entities.
    """

    TYPE_CHOICES = [
        ('email', 'Email'),
        ('call', 'Phone Call'),
        ('meeting', 'Meeting'),
        ('video_call', 'Video Call'),
        ('note', 'Internal Note'),
        ('follow_up', 'Follow-up'),
        ('task_created', 'Task Created'),
        ('status_change', 'Status Change'),
        ('document', 'Document Shared'),
        ('social_media', 'Social Media Interaction'),
        ('event', 'Event/Show'),
        ('negotiation', 'Negotiation'),
    ]

    SENTIMENT_CHOICES = [
        ('very_positive', 'Very Positive'),
        ('positive', 'Positive'),
        ('neutral', 'Neutral'),
        ('negative', 'Negative'),
        ('very_negative', 'Very Negative'),
    ]

    # Core fields
    type = models.CharField(
        max_length=30,
        choices=TYPE_CHOICES,
        db_index=True,
        help_text="Type of activity or communication"
    )

    subject = models.CharField(
        max_length=200,
        help_text="Subject or title of the activity"
    )

    content = models.TextField(
        blank=True,
        help_text="Detailed content or notes from the activity"
    )

    # Polymorphic relationships
    entity = models.ForeignKey(
        'identity.Entity',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='activities',
        help_text="Entity this activity is related to"
    )

    contact_person = models.ForeignKey(
        'identity.ContactPerson',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activities',
        help_text="Specific contact person involved"
    )

    campaign = models.ForeignKey(
        'campaigns.Campaign',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='activities',
        help_text="Campaign this activity is related to"
    )

    contract = models.ForeignKey(
        'contracts.Contract',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='activities',
        help_text="Contract this activity is related to"
    )

    # Participants
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='activities_created',
        help_text="User who logged this activity"
    )

    participants = models.ManyToManyField(
        User,
        blank=True,
        related_name='activities_participated',
        help_text="Internal users who participated in this activity"
    )

    external_participants = models.JSONField(
        default=list,
        blank=True,
        help_text="List of external participants (names and emails)"
    )

    # Communication details
    direction = models.CharField(
        max_length=10,
        choices=[
            ('inbound', 'Inbound'),
            ('outbound', 'Outbound'),
            ('internal', 'Internal'),
        ],
        default='internal',
        help_text="Direction of communication"
    )

    sentiment = models.CharField(
        max_length=20,
        choices=SENTIMENT_CHOICES,
        null=True,
        blank=True,
        help_text="Sentiment or tone of the interaction"
    )

    # Activity metadata
    activity_date = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="When this activity occurred"
    )

    duration_minutes = models.IntegerField(
        null=True,
        blank=True,
        help_text="Duration of the activity in minutes"
    )

    location = models.CharField(
        max_length=200,
        blank=True,
        help_text="Location where the activity took place"
    )

    # Follow-up tracking
    follow_up_required = models.BooleanField(
        default=False,
        help_text="Whether this activity requires a follow-up"
    )

    follow_up_date = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="When to follow up on this activity"
    )

    follow_up_completed = models.BooleanField(
        default=False,
        help_text="Whether the follow-up has been completed"
    )

    follow_up_task = models.ForeignKey(
        Task,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activity_follow_ups',
        help_text="Task created for follow-up"
    )

    # Attachments and links
    attachments = models.JSONField(
        default=list,
        blank=True,
        help_text="List of attachment URLs or file references"
    )

    related_url = models.URLField(
        blank=True,
        help_text="Related URL (e.g., calendar link, document link)"
    )

    # Department association
    department = models.ForeignKey(
        'api.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activities',
        help_text="Department this activity belongs to"
    )

    # Additional metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional activity-specific metadata"
    )

    # Tracking
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-activity_date', '-created_at']
        indexes = [
            models.Index(fields=['type', 'activity_date']),
            models.Index(fields=['entity', 'activity_date']),
            models.Index(fields=['campaign', 'activity_date']),
            models.Index(fields=['contact_person', 'activity_date']),
            models.Index(fields=['created_by', 'activity_date']),
            models.Index(fields=['follow_up_date', 'follow_up_completed']),
            models.Index(fields=['department', 'activity_date']),
            models.Index(fields=['sentiment', 'activity_date']),
        ]
        verbose_name = 'Activity'
        verbose_name_plural = 'Activities'

    def __str__(self):
        return f"{self.get_type_display()} - {self.subject} ({self.activity_date.date()})"

    def create_follow_up_task(self):
        """Create a follow-up task for this activity"""
        if not self.follow_up_required or self.follow_up_task:
            return None

        task = Task.objects.create(
            title=f"Follow up: {self.subject}",
            description=f"Follow up on {self.get_type_display()} from {self.activity_date.date()}\n\n{self.content}",
            task_type='follow_up',
            campaign=self.campaign,
            entity=self.entity,
            contract=self.contract,
            assigned_to=self.created_by,
            created_by=self.created_by,
            department=self.department,
            due_date=self.follow_up_date,
            priority=2,
            metadata={
                'activity_id': self.id,
                'activity_type': self.type,
                'original_date': self.activity_date.isoformat(),
            }
        )

        self.follow_up_task = task
        self.save(update_fields=['follow_up_task'])

        return task


class CampaignMetrics(models.Model):
    """
    Time-series metrics tracking for campaigns.
    Stores historical KPI data for reporting and analysis.
    """

    campaign = models.ForeignKey(
        'campaigns.Campaign',
        on_delete=models.CASCADE,
        related_name='metrics_history'
    )

    recorded_date = models.DateField(
        db_index=True,
        help_text="Date when these metrics were recorded"
    )

    # Common digital marketing metrics
    impressions = models.IntegerField(null=True, blank=True)
    clicks = models.IntegerField(null=True, blank=True)
    ctr = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Click-through rate %")

    conversions = models.IntegerField(null=True, blank=True)
    conversion_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Conversion rate %")

    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    cpc = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="Cost per click")
    cpa = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="Cost per acquisition")

    # Social media metrics
    reach = models.IntegerField(null=True, blank=True)
    engagement = models.IntegerField(null=True, blank=True)
    engagement_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Engagement rate %")

    followers_gained = models.IntegerField(null=True, blank=True)
    followers_lost = models.IntegerField(null=True, blank=True)

    # Content metrics
    views = models.IntegerField(null=True, blank=True)
    watch_time_minutes = models.IntegerField(null=True, blank=True)
    shares = models.IntegerField(null=True, blank=True)
    comments = models.IntegerField(null=True, blank=True)
    likes = models.IntegerField(null=True, blank=True)

    # Music-specific metrics
    streams = models.IntegerField(null=True, blank=True)
    downloads = models.IntegerField(null=True, blank=True)
    playlist_adds = models.IntegerField(null=True, blank=True)
    radio_plays = models.IntegerField(null=True, blank=True)

    # Revenue metrics
    revenue = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    roi = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="Return on investment %")

    # Custom metrics (flexible JSON storage)
    custom_metrics = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional platform or service-specific metrics"
    )

    # Metadata
    source = models.CharField(
        max_length=50,
        blank=True,
        help_text="Source of the metrics (e.g., 'facebook_ads', 'google_analytics')"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-recorded_date']
        unique_together = ['campaign', 'recorded_date', 'source']
        indexes = [
            models.Index(fields=['campaign', 'recorded_date']),
            models.Index(fields=['recorded_date']),
        ]
        verbose_name = 'Campaign Metrics'
        verbose_name_plural = 'Campaign Metrics'

    def __str__(self):
        return f"{self.campaign.campaign_name} - Metrics for {self.recorded_date}"