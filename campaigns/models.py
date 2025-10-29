from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from decimal import Decimal

User = get_user_model()


class Campaign(models.Model):
    """
    Campaign model for tracking brand deals with clients and artists.
    """

    DEPARTMENT_CHOICES = [
        ('digital', 'Digital'),
        ('sales', 'Sales'),
    ]

    STATUS_CHOICES = [
        ('lead', 'Lead'),
        ('negotiation', 'Negotiation'),
        ('confirmed', 'Confirmed'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('lost', 'Lost'),
    ]

    # Core relationships (all reference Entity model from identity app)
    client = models.ForeignKey(
        'identity.Entity',
        on_delete=models.PROTECT,
        related_name='campaigns_as_client',
        help_text="Client entity (must have 'client' role)"
    )

    artist = models.ForeignKey(
        'identity.Entity',
        on_delete=models.PROTECT,
        related_name='campaigns_as_artist',
        help_text="Artist entity (must have 'artist' role)"
    )

    brand = models.ForeignKey(
        'identity.Entity',
        on_delete=models.PROTECT,
        related_name='campaigns_as_brand',
        help_text="Brand entity (must have 'brand' role)"
    )

    contact_person = models.ForeignKey(
        'identity.ContactPerson',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='campaigns',
        help_text="Primary contact person at the client for this campaign"
    )

    # Department for RBAC
    department = models.CharField(
        max_length=50,
        choices=DEPARTMENT_CHOICES,
        default='digital',  # Temporary default for migration
        db_index=True,
        help_text="Department this campaign belongs to (auto-set from creator)"
    )

    # Campaign details
    campaign_name = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Name of the campaign"
    )

    value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Campaign value in currency"
    )

    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='lead',
        db_index=True,
        help_text="Current status of the campaign"
    )

    confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the campaign was confirmed"
    )

    # Metadata
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about the campaign"
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='campaigns_created',
        help_text="User who created this campaign"
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['brand', 'status']),
            models.Index(fields=['client', 'status']),
            models.Index(fields=['artist', 'status']),
            models.Index(fields=['department', 'status']),  # For RBAC filtering
            models.Index(fields=['department', 'created_at']),  # For department-based queries
        ]
        verbose_name = 'Campaign'
        verbose_name_plural = 'Campaigns'

    def __str__(self):
        return f"{self.campaign_name} - {self.brand.display_name} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        """Auto-set confirmed_at when status changes to confirmed"""
        if self.status in ['confirmed', 'active', 'completed'] and not self.confirmed_at:
            from django.utils import timezone
            self.confirmed_at = timezone.now()
        super().save(*args, **kwargs)


class CampaignHandler(models.Model):
    """
    Tracks which users are handling/assigned to a campaign.
    Supports multiple handlers with different roles.
    """

    ROLE_CHOICES = [
        ('lead', 'Lead'),
        ('support', 'Support'),
        ('observer', 'Observer'),
    ]

    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name='handlers'
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='campaign_assignments'
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='support',
        help_text="Role of this handler in the campaign"
    )

    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['campaign', 'user']
        ordering = ['role', 'assigned_at']
        indexes = [
            models.Index(fields=['campaign', 'role']),
            models.Index(fields=['user', 'role']),
        ]
        verbose_name = 'Campaign Handler'
        verbose_name_plural = 'Campaign Handlers'

    def __str__(self):
        return f"{self.user.email} - {self.campaign.campaign_name} ({self.get_role_display()})"
