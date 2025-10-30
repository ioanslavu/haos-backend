from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()


class Notification(models.Model):
    """
    Notification model for in-app notifications.
    Supports generic relations to any model for flexibility.
    """

    NOTIFICATION_TYPES = [
        ('assignment', 'Assignment'),
        ('mention', 'Mention'),
        ('status_change', 'Status Change'),
        ('contract_signed', 'Contract Signed'),
        ('contract_created', 'Contract Created'),
        ('comment', 'Comment'),
        ('system', 'System'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        help_text="User who receives this notification",
        db_index=True
    )

    message = models.TextField(
        help_text="Notification message text"
    )

    notification_type = models.CharField(
        max_length=50,
        choices=NOTIFICATION_TYPES,
        default='system',
        help_text="Type of notification",
        db_index=True
    )

    is_read = models.BooleanField(
        default=False,
        help_text="Whether the user has read this notification",
        db_index=True
    )

    # Generic relation to any model
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Content type of the related object"
    )
    object_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="ID of the related object"
    )
    content_object = GenericForeignKey('content_type', 'object_id')

    # Optional action URL for frontend navigation
    action_url = models.CharField(
        max_length=500,
        blank=True,
        help_text="Frontend URL to navigate to when clicking notification"
    )

    # Additional metadata (JSON)
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metadata for the notification"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_read', '-created_at']),
        ]
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'

    def __str__(self):
        return f"{self.notification_type} for {self.user.email}: {self.message[:50]}"

    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.save(update_fields=['is_read', 'updated_at'])

    def mark_as_unread(self):
        """Mark notification as unread"""
        if self.is_read:
            self.is_read = False
            self.save(update_fields=['is_read', 'updated_at'])


class NotificationPreferences(models.Model):
    """
    User preferences for notification alerts.
    Controls which alerts to receive and custom thresholds.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='notification_preferences',
        help_text="User these preferences belong to"
    )

    # Alert type toggles
    deadline_tomorrow_enabled = models.BooleanField(
        default=True,
        help_text="Receive alerts for tasks due tomorrow"
    )

    deadline_urgent_enabled = models.BooleanField(
        default=True,
        help_text="Receive alerts for tasks due in next few hours"
    )

    task_inactivity_enabled = models.BooleanField(
        default=True,
        help_text="Receive alerts for tasks without updates"
    )

    task_overdue_enabled = models.BooleanField(
        default=True,
        help_text="Receive alerts for overdue tasks"
    )

    campaign_ending_enabled = models.BooleanField(
        default=True,
        help_text="Receive alerts for campaigns ending soon"
    )

    # Custom thresholds
    urgent_deadline_hours = models.IntegerField(
        default=4,
        validators=[MinValueValidator(1), MaxValueValidator(24)],
        help_text="Hours before deadline to receive urgent alert (1-24)"
    )

    inactivity_days = models.IntegerField(
        default=7,
        validators=[MinValueValidator(1), MaxValueValidator(30)],
        help_text="Days without update to trigger inactivity alert (1-30)"
    )

    campaign_ending_days = models.IntegerField(
        default=7,
        validators=[MinValueValidator(1), MaxValueValidator(30)],
        help_text="Days before campaign end to receive alert (1-30)"
    )

    # Notification timing preferences
    QUIET_HOURS_CHOICES = [
        ('none', 'No Quiet Hours'),
        ('evening', 'Evening (6 PM - 9 AM)'),
        ('night', 'Night (8 PM - 8 AM)'),
        ('weekend', 'Weekends'),
        ('custom', 'Custom Hours'),
    ]

    quiet_hours = models.CharField(
        max_length=20,
        choices=QUIET_HOURS_CHOICES,
        default='none',
        help_text="When to pause non-urgent notifications"
    )

    quiet_hours_start = models.TimeField(
        null=True,
        blank=True,
        help_text="Start time for custom quiet hours"
    )

    quiet_hours_end = models.TimeField(
        null=True,
        blank=True,
        help_text="End time for custom quiet hours"
    )

    # Digest preferences
    enable_daily_digest = models.BooleanField(
        default=False,
        help_text="Receive a daily digest instead of individual alerts"
    )

    digest_time = models.TimeField(
        default='09:00:00',
        help_text="Time to send daily digest (if enabled)"
    )

    # Additional preferences
    mute_all_alerts = models.BooleanField(
        default=False,
        help_text="Temporarily mute all automated alerts"
    )

    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Notification Preferences'
        verbose_name_plural = 'Notification Preferences'

    def __str__(self):
        return f"Notification preferences for {self.user.email}"

    @classmethod
    def get_or_create_for_user(cls, user):
        """Get or create preferences for a user"""
        preferences, created = cls.objects.get_or_create(user=user)
        return preferences
