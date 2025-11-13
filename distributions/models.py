from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.db.models import Sum
from decimal import Decimal

User = get_user_model()


# Shared platform choices (consistent with campaigns.models.PLATFORM_CHOICES)
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


class Distribution(models.Model):
    """
    Long-term distribution deals with artists, labels, or aggregators.
    Similar to Campaign but focused on ongoing revenue sharing.
    """

    DEAL_TYPE_CHOICES = [
        ('artist', 'Artist'),
        ('label', 'Label'),
        ('aggregator', 'Aggregator'),
        ('company', 'Company'),
    ]

    DEAL_STATUS_CHOICES = [
        ('active', 'Active'),
        ('in_negotiation', 'In Negotiation'),
        ('expired', 'Expired'),
    ]

    # Entity relationship
    entity = models.ForeignKey(
        'identity.Entity',
        on_delete=models.PROTECT,
        related_name='distributions',
        help_text="The artist, label, or aggregator entity for this distribution deal"
    )

    deal_type = models.CharField(
        max_length=20,
        choices=DEAL_TYPE_CHOICES,
        db_index=True,
        help_text="Type of distribution deal (auto-populated from entity roles, but editable)"
    )

    includes_dsps_youtube = models.BooleanField(
        default=False,
        help_text="Whether this distribution includes DSPs and/or YouTube"
    )

    # Optional contract reference
    contract = models.ForeignKey(
        'contracts.Contract',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='distributions',
        help_text="Optional link to the contract for this distribution deal"
    )

    # RBAC - Digital department only
    department = models.ForeignKey(
        'api.Department',
        on_delete=models.PROTECT,
        related_name='distributions',
        null=True,
        blank=True,
        help_text="Department this distribution belongs to (digital team)"
    )

    # Financial terms
    global_revenue_share_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        help_text="Global revenue share percentage for the artist/entity (0.00-100.00)"
    )

    # Timeline (long-term, no required end date)
    signing_date = models.DateField(
        help_text="Date when the distribution deal was signed"
    )

    # Status
    deal_status = models.CharField(
        max_length=20,
        choices=DEAL_STATUS_CHOICES,
        default='in_negotiation',
        db_index=True,
        help_text="Current status of the distribution deal"
    )

    # Contact
    contact_person = models.ForeignKey(
        'identity.ContactPerson',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='distributions',
        help_text="Primary contact person for this distribution deal"
    )

    # Metadata
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about the distribution deal"
    )

    special_terms = models.TextField(
        blank=True,
        help_text="Special terms or conditions for this distribution deal"
    )

    # Audit fields
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_distributions',
        help_text="User who created this distribution"
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['deal_status', 'department']),
            models.Index(fields=['entity', 'deal_status']),
            models.Index(fields=['deal_type', 'deal_status']),
            models.Index(fields=['signing_date']),
        ]
        verbose_name = 'Distribution'
        verbose_name_plural = 'Distributions'

    def __str__(self):
        return f"{self.entity.display_name} - {self.get_deal_type_display()} ({self.get_deal_status_display()})"


class DistributionCatalogItem(models.Model):
    """
    Links catalog items (recordings or releases) to distribution deals.
    Allows per-item revenue overrides and platform tracking.
    """

    DISTRIBUTION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('live', 'Live'),
        ('taken_down', 'Taken Down'),
    ]

    distribution = models.ForeignKey(
        Distribution,
        on_delete=models.CASCADE,
        related_name='catalog_items',
        help_text="The distribution deal this catalog item belongs to"
    )

    # Catalog item - exactly one required (recording OR release)
    recording = models.ForeignKey(
        'catalog.Recording',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='distribution_items',
        help_text="Recording (single track) for this distribution"
    )

    release = models.ForeignKey(
        'catalog.Release',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='distribution_items',
        help_text="Release (album/EP) for this distribution"
    )

    # Platform distribution (ArrayField with choices - consistent with Campaign)
    platforms = ArrayField(
        models.CharField(max_length=50, choices=PLATFORM_CHOICES),
        default=list,
        blank=True,
        help_text="Platforms where this item is distributed (Spotify, Apple Music, etc.)"
    )

    # Revenue override (optional - per-item override of global percentage)
    individual_revenue_share = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        help_text="Override global revenue share for this specific item (optional)"
    )

    # Status
    distribution_status = models.CharField(
        max_length=20,
        choices=DISTRIBUTION_STATUS_CHOICES,
        default='pending',
        db_index=True,
        help_text="Distribution status for this catalog item"
    )

    # Dates
    release_date = models.DateField(
        null=True,
        blank=True,
        help_text="Release date for this catalog item"
    )

    added_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this item was added to the distribution"
    )

    # Notes
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about this catalog item's distribution"
    )

    class Meta:
        unique_together = [
            ['distribution', 'recording'],
            ['distribution', 'release']
        ]
        ordering = ['-added_at']
        indexes = [
            models.Index(fields=['distribution', 'distribution_status']),
            models.Index(fields=['recording', 'distribution_status']),
            models.Index(fields=['release', 'distribution_status']),
        ]
        verbose_name = 'Distribution Catalog Item'
        verbose_name_plural = 'Distribution Catalog Items'

    def __str__(self):
        item_title = self.catalog_item_title
        return f"{self.distribution.entity.display_name} - {item_title}"

    def clean(self):
        """Validate that exactly one of recording or release is set"""
        if not self.recording and not self.release:
            raise ValidationError("Must have either a recording or a release")
        if self.recording and self.release:
            raise ValidationError("Cannot have both a recording and a release")

    def save(self, *args, **kwargs):
        """Validate before saving"""
        self.clean()
        super().save(*args, **kwargs)

    @property
    def catalog_item_title(self):
        """Get title from recording or release"""
        if self.recording:
            return self.recording.title
        elif self.release:
            return self.release.title
        return "Unknown"

    @property
    def catalog_item_type(self):
        """Get type of catalog item (recording or release)"""
        if self.recording:
            return "recording"
        elif self.release:
            return "release"
        return "unknown"

    @property
    def effective_revenue_share(self):
        """Return individual override or fall back to global percentage"""
        if self.individual_revenue_share is not None:
            return self.individual_revenue_share
        return self.distribution.global_revenue_share_percentage

    @property
    def total_revenue(self):
        """Sum all revenue reports for this catalog item"""
        result = self.revenue_reports.aggregate(total=Sum('revenue_amount'))
        return result['total'] or Decimal('0.00')


class DistributionRevenueReport(models.Model):
    """
    Monthly revenue reports per platform for distributed catalog items.
    Separate from finance department's general revenue tracking.
    """

    catalog_item = models.ForeignKey(
        DistributionCatalogItem,
        on_delete=models.CASCADE,
        related_name='revenue_reports',
        help_text="The catalog item this revenue report belongs to"
    )

    # Platform (singular CharField with choices - one report per platform per month)
    platform = models.CharField(
        max_length=50,
        choices=PLATFORM_CHOICES,
        db_index=True,
        help_text="Platform this revenue report is for"
    )

    # Reporting period (month/year)
    reporting_period = models.DateField(
        db_index=True,
        help_text="First day of the month for this reporting period (YYYY-MM-01)"
    )

    # Revenue data
    revenue_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Revenue amount for this period"
    )

    currency = models.CharField(
        max_length=3,
        default='EUR',
        help_text="Currency for the revenue amount"
    )

    # Engagement metrics (optional)
    streams = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Number of streams for this period (optional)"
    )

    downloads = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Number of downloads for this period (optional)"
    )

    # Metadata
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about this revenue report"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_distribution_revenue_reports',
        help_text="User who created this revenue report"
    )

    class Meta:
        unique_together = ['catalog_item', 'platform', 'reporting_period']
        ordering = ['-reporting_period', 'platform']
        indexes = [
            models.Index(fields=['reporting_period', 'platform']),
            models.Index(fields=['catalog_item', 'reporting_period']),
            models.Index(fields=['platform', 'reporting_period']),
        ]
        verbose_name = 'Distribution Revenue Report'
        verbose_name_plural = 'Distribution Revenue Reports'

    def __str__(self):
        return f"{self.catalog_item.catalog_item_title} - {self.get_platform_display()} - {self.reporting_period.strftime('%Y-%m')} - {self.revenue_amount} {self.currency}"
