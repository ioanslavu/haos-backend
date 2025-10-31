from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

User = get_user_model()


class Campaign(models.Model):
    """
    Campaign model for tracking brand deals with clients and artists.
    """

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
        help_text="Client entity (can be any business role entity)"
    )

    artist = models.ForeignKey(
        'identity.Entity',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='campaigns_as_artist',
        help_text="Artist entity (optional - use artist or song)"
    )

    brand = models.ForeignKey(
        'identity.Entity',
        on_delete=models.PROTECT,
        related_name='campaigns_as_brand',
        help_text="Brand entity (can be any business role entity)"
    )

    song = models.ForeignKey(
        'catalog.Recording',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='campaigns',
        help_text="Song/recording for this campaign (optional - use artist or song)"
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
    # Null = admin-only campaign (visible only to admins)
    department = models.ForeignKey(
        'api.Department',
        on_delete=models.PROTECT,
        related_name='campaigns',
        null=True,
        blank=True,
        help_text="Department this campaign belongs to. If null, only admins can see it."
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
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Campaign value in currency (optional, depends on pricing model)"
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

    # Department-specific fields for Digital campaigns
    SERVICE_TYPE_CHOICES = [
        ('ppc', 'PPC Campaign'),
        ('tiktok_ugc', 'TikTok UGC'),
        ('dsp_distribution', 'DSP Distribution'),
        ('radio_plugging', 'Radio Plugging'),
        ('playlist_pitching', 'Playlist Pitching'),
        ('youtube_cms', 'YouTube CMS'),
        ('social_media_mgmt', 'Social Media Management'),
        ('content_creation', 'Content Creation'),
        ('influencer_marketing', 'Influencer Marketing'),
        ('seo', 'SEO Optimization'),
        ('email_marketing', 'Email Marketing'),
    ]

    service_types = ArrayField(
        models.CharField(max_length=50, choices=SERVICE_TYPE_CHOICES),
        default=list,
        blank=True,
        db_index=True,
        help_text="Types of services for this campaign"
    )

    PLATFORM_CHOICES = [
        ('meta', 'Meta (Facebook/Instagram)'),
        ('google', 'Google Ads'),
        ('tiktok', 'TikTok'),
        ('spotify', 'Spotify'),
        ('youtube', 'YouTube'),
        ('apple_music', 'Apple Music'),
        ('deezer', 'Deezer'),
        ('amazon_music', 'Amazon Music'),
        ('soundcloud', 'SoundCloud'),
        ('twitter', 'Twitter/X'),
        ('linkedin', 'LinkedIn'),
        ('snapchat', 'Snapchat'),
        ('pinterest', 'Pinterest'),
        ('multi', 'Multi-Platform'),
    ]

    platforms = ArrayField(
        models.CharField(max_length=50, choices=PLATFORM_CHOICES),
        default=list,
        blank=True,
        db_index=True,
        help_text="Platforms for this campaign"
    )

    # Campaign timeline
    start_date = models.DateField(
        null=True,
        blank=True,
        help_text="Campaign start date"
    )

    end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Campaign end date"
    )

    # Budget tracking
    budget_allocated = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Budget allocated for this campaign"
    )

    budget_spent = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Budget spent so far"
    )

    currency = models.CharField(
        max_length=3,
        default='EUR',
        help_text="Currency for all monetary values"
    )

    # Financial tracking (for Digital department)
    profit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Auto-calculated profit: value - budget_spent"
    )

    internal_cost_estimate = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Estimated internal costs (labor, overhead, etc.)"
    )

    PRICING_MODEL_CHOICES = [
        ('service_fee', 'Service Fee'),
        ('revenue_share', 'Revenue Share'),
    ]

    pricing_model = models.CharField(
        max_length=20,
        choices=PRICING_MODEL_CHOICES,
        default='service_fee',
        db_index=True,
        help_text="Pricing model: service_fee (client pays us) or revenue_share (we generate revenue and share)"
    )

    # Revenue Share fields (only used when pricing_model='revenue_share')
    revenue_generated = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Total revenue generated (for revenue_share model)"
    )

    partner_share_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        help_text="Percentage of revenue shared with partner (0.00-100.00, for revenue_share model)"
    )

    INVOICE_STATUS_CHOICES = [
        ('not_issued', 'Not Issued (Neemisă)'),
        ('issued', 'Issued (Emisă)'),
        ('collected', 'Collected (Încasată)'),
        ('delayed', 'Delayed (Întârziată)'),
    ]

    invoice_status = models.CharField(
        max_length=20,
        choices=INVOICE_STATUS_CHOICES,
        default='not_issued',
        db_index=True,
        help_text="Invoice status for this campaign"
    )

    # KPI tracking
    kpi_targets = models.JSONField(
        default=dict,
        blank=True,
        help_text="Target KPIs for the campaign. Format: {'kpi_name': {'target': value, 'unit': 'unit'}}"
    )

    kpi_actuals = models.JSONField(
        default=dict,
        blank=True,
        help_text="Current/actual KPIs. Format: {'kpi_name': {'actual': value, 'unit': 'unit', 'last_updated': 'ISO datetime'}}"
    )

    # Department-specific metadata (flexible JSON storage)
    department_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Department-specific data and metadata"
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
            models.Index(fields=['song', 'status']),
            models.Index(fields=['department', 'status']),  # For RBAC filtering
            models.Index(fields=['department', 'created_at']),  # For department-based queries
            # Financial query optimization indexes
            models.Index(fields=['start_date']),  # For date range filtering
            models.Index(fields=['invoice_status', 'start_date']),  # For pending collections queries
            models.Index(fields=['pricing_model', 'status']),  # For pricing model filtering
        ]
        verbose_name = 'Campaign'
        verbose_name_plural = 'Campaigns'

    def __str__(self):
        return f"{self.campaign_name} - {self.brand.display_name} ({self.get_status_display()})"

    @property
    def partner_payout(self):
        """Calculate amount paid to partner (for revenue_share model)"""
        if self.pricing_model == 'revenue_share' and self.revenue_generated and self.partner_share_percentage:
            return (self.revenue_generated * self.partner_share_percentage) / Decimal('100.00')
        return None

    @property
    def our_revenue(self):
        """Calculate our share of revenue (for revenue_share model)"""
        if self.pricing_model == 'revenue_share' and self.revenue_generated:
            payout = self.partner_payout or Decimal('0.00')
            return self.revenue_generated - payout
        return None

    @property
    def calculated_profit(self):
        """Calculate profit based on pricing model"""
        if self.pricing_model == 'service_fee':
            # Service fee model: profit = value - budget_spent
            if self.value and self.budget_spent:
                return self.value - self.budget_spent
            return None
        elif self.pricing_model == 'revenue_share':
            # Revenue share model: profit = our_revenue - budget_allocated
            our_rev = self.our_revenue
            if our_rev and self.budget_allocated:
                return our_rev - self.budget_allocated
            return None
        return None

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
