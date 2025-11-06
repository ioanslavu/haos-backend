from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
from sequences import get_next_value

User = get_user_model()


class Brief(models.Model):
    """
    Brief intake model for tracking campaign requests from brands/agencies.
    Captures initial requirements before creating opportunities.
    """
    STATUS_CHOICES = [
        ('new', 'New'),
        ('qualified', 'Qualified'),
        ('pitched', 'Pitched'),
        ('lost', 'Lost'),
        ('won', 'Won'),
    ]

    # Relationships
    account = models.ForeignKey(
        'identity.Entity',
        on_delete=models.PROTECT,
        related_name='briefs',
        help_text="Brand or agency requesting the brief"
    )

    contact_person = models.ForeignKey(
        'identity.ContactPerson',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='briefs',
        help_text="Primary contact person at the account"
    )

    department = models.ForeignKey(
        'api.Department',
        on_delete=models.PROTECT,
        related_name='briefs',
        null=True,
        blank=True,
        help_text="Department this brief belongs to"
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='briefs_created',
        help_text="User who created this brief"
    )

    # Brief details
    campaign_title = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Title of the campaign"
    )

    brand_category = models.CharField(
        max_length=100,
        blank=True,
        help_text="Product/brand category (e.g., Beverage, Fashion, Tech)"
    )

    objectives = models.TextField(
        blank=True,
        help_text="Campaign objectives and goals"
    )

    target_audience = models.TextField(
        blank=True,
        help_text="Target audience description"
    )

    channels = models.JSONField(
        default=list,
        blank=True,
        help_text="Marketing channels (Paid/Owned/ATL/BTL/OOH/Packaging, etc.)"
    )

    # Timeline
    timing_start = models.DateField(
        null=True,
        blank=True,
        help_text="Desired campaign start date"
    )

    timing_end = models.DateField(
        null=True,
        blank=True,
        help_text="Desired campaign end date"
    )

    # Budget
    budget_range_min = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Minimum budget range"
    )

    budget_range_max = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Maximum budget range"
    )

    currency = models.CharField(
        max_length=3,
        default='EUR',
        help_text="Currency for budget"
    )

    # Requirements
    must_haves = models.TextField(
        blank=True,
        help_text="Must-have requirements"
    )

    nice_to_have = models.TextField(
        blank=True,
        help_text="Nice-to-have features"
    )

    # Status and dates
    brief_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='new',
        db_index=True,
        help_text="Current status of the brief"
    )

    received_date = models.DateField(
        auto_now_add=True,
        help_text="Date when brief was received"
    )

    sla_due_date = models.DateField(
        null=True,
        blank=True,
        help_text="SLA response deadline"
    )

    # Metadata
    notes = models.TextField(
        blank=True,
        help_text="Additional notes"
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['brief_status', 'created_at']),
            models.Index(fields=['account', 'brief_status']),
            models.Index(fields=['department', 'brief_status']),
            models.Index(fields=['sla_due_date']),
        ]
        verbose_name = 'Brief'
        verbose_name_plural = 'Briefs'

    def __str__(self):
        return f"{self.campaign_title} - {self.account.display_name}"


class Opportunity(models.Model):
    """
    Opportunity model for tracking sales pipeline from qualified briefs to deals.
    Represents a potential deal with probability and stage tracking.
    """

    STAGE_CHOICES = [
        ('qualified', 'Qualified'),
        ('proposal', 'Proposal Sent'),
        ('shortlist', 'Artist Shortlist'),
        ('negotiation', 'Negotiation'),
        ('contract_sent', 'Contract Sent'),
        ('po_received', 'PO Received'),
        ('in_execution', 'In Execution'),
        ('completed', 'Completed'),
        ('closed_lost', 'Closed - Lost'),
    ]

    # Relationships
    brief = models.ForeignKey(
        Brief,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='opportunities',
        help_text="Original brief (optional)"
    )

    account = models.ForeignKey(
        'identity.Entity',
        on_delete=models.PROTECT,
        related_name='opportunities',
        help_text="Brand or agency"
    )

    owner_user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='opportunities_owned',
        help_text="Sales owner responsible for this opportunity"
    )

    department = models.ForeignKey(
        'api.Department',
        on_delete=models.PROTECT,
        related_name='opportunities',
        null=True,
        blank=True,
        help_text="Department this opportunity belongs to"
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='opportunities_created',
        help_text="User who created this opportunity"
    )

    # Opportunity details
    opp_name = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Opportunity name"
    )

    stage = models.CharField(
        max_length=20,
        choices=STAGE_CHOICES,
        default='qualified',
        db_index=True,
        help_text="Current stage in sales pipeline"
    )

    amount_expected = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Expected deal value"
    )

    currency = models.CharField(
        max_length=3,
        default='EUR',
        help_text="Currency"
    )

    probability_percent = models.IntegerField(
        default=10,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Probability of closing (0-100%)"
    )

    expected_close_date = models.DateField(
        null=True,
        blank=True,
        help_text="Expected closing date"
    )

    actual_close_date = models.DateField(
        null=True,
        blank=True,
        help_text="Actual closing date"
    )

    next_step = models.TextField(
        blank=True,
        help_text="Next action or milestone"
    )

    lost_reason = models.TextField(
        blank=True,
        help_text="Reason if opportunity was lost"
    )

    # Metadata
    notes = models.TextField(
        blank=True,
        help_text="Additional notes"
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['stage', 'created_at']),
            models.Index(fields=['account', 'stage']),
            models.Index(fields=['owner_user', 'stage']),
            models.Index(fields=['department', 'stage']),
            models.Index(fields=['expected_close_date']),
        ]
        verbose_name = 'Opportunity'
        verbose_name_plural = 'Opportunities'

    def __str__(self):
        return f"{self.opp_name} - {self.account.display_name} ({self.get_stage_display()})"


class Proposal(models.Model):
    """
    Proposal model with versioning support.
    Each opportunity can have multiple proposal versions.
    """

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('revised', 'Revised'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    # Relationships
    opportunity = models.ForeignKey(
        Opportunity,
        on_delete=models.CASCADE,
        related_name='proposals',
        help_text="Opportunity this proposal belongs to"
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='proposals_created',
        help_text="User who created this proposal"
    )

    # Versioning
    version = models.IntegerField(
        default=1,
        help_text="Proposal version number"
    )

    # Pricing
    fee_gross = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Gross fee before discounts"
    )

    discounts = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Total discounts"
    )

    agency_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Agency commission/fee"
    )

    fee_net = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Net fee (gross - discounts - agency_fee)"
    )

    currency = models.CharField(
        max_length=3,
        default='EUR',
        help_text="Currency"
    )

    # Status and dates
    proposal_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        db_index=True,
        help_text="Current status of the proposal"
    )

    sent_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When proposal was sent to client"
    )

    valid_until = models.DateField(
        null=True,
        blank=True,
        help_text="Proposal validity date"
    )

    # Metadata
    notes = models.TextField(
        blank=True,
        help_text="Additional notes"
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-version', '-created_at']
        unique_together = ['opportunity', 'version']
        indexes = [
            models.Index(fields=['opportunity', 'version']),
            models.Index(fields=['proposal_status', 'created_at']),
        ]
        verbose_name = 'Proposal'
        verbose_name_plural = 'Proposals'

    def __str__(self):
        return f"{self.opportunity.opp_name} - v{self.version} ({self.get_proposal_status_display()})"

    def save(self, *args, **kwargs):
        """Auto-calculate fee_net on save"""
        self.fee_net = self.fee_gross - self.discounts - self.agency_fee
        super().save(*args, **kwargs)


class ProposalArtist(models.Model):
    """
    M2M relationship between Proposal and Artist entities with extra fields.
    """

    ROLE_CHOICES = [
        ('main', 'Main Artist'),
        ('featured', 'Featured'),
        ('guest', 'Guest'),
        ('ensemble', 'Ensemble'),
    ]

    proposal = models.ForeignKey(
        Proposal,
        on_delete=models.CASCADE,
        related_name='proposal_artists',
        help_text="Proposal"
    )

    artist = models.ForeignKey(
        'identity.Entity',
        on_delete=models.PROTECT,
        related_name='artist_proposals',
        limit_choices_to={'entity_roles__role': 'artist'},
        help_text="Artist entity"
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='main',
        help_text="Artist role in this proposal"
    )

    proposed_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Proposed artist fee"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['proposal', 'artist']
        ordering = ['role', 'created_at']
        verbose_name = 'Proposal Artist'
        verbose_name_plural = 'Proposal Artists'

    def __str__(self):
        return f"{self.artist.display_name} - {self.proposal.opportunity.opp_name} ({self.get_role_display()})"


class DeliverablePack(models.Model):
    """
    Reusable deliverable package templates.
    """

    name = models.CharField(
        max_length=255,
        unique=True,
        help_text="Pack name (e.g., 'Standard IG Package', 'TVC + Digital Bundle')"
    )

    description = models.TextField(
        blank=True,
        help_text="Description of what's included"
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether this pack is active/available"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Deliverable Pack'
        verbose_name_plural = 'Deliverable Packs'

    def __str__(self):
        return self.name


class DeliverablePackItem(models.Model):
    """
    Items included in a deliverable pack.
    """

    DELIVERABLE_TYPE_CHOICES = [
        ('ig_post', 'Instagram Post'),
        ('ig_story', 'Instagram Story'),
        ('ig_reel', 'Instagram Reel'),
        ('tiktok_video', 'TikTok Video'),
        ('youtube_video', 'YouTube Video'),
        ('youtube_short', 'YouTube Short'),
        ('tvc', 'TV Commercial'),
        ('radio_spot', 'Radio Spot'),
        ('event', 'Event Appearance'),
        ('ooh', 'Out of Home (OOH)'),
        ('billboard', 'Billboard'),
        ('packaging', 'Product Packaging'),
        ('print_ad', 'Print Advertisement'),
        ('digital_banner', 'Digital Banner'),
        ('podcast', 'Podcast'),
        ('livestream', 'Livestream'),
        ('other', 'Other'),
    ]

    pack = models.ForeignKey(
        DeliverablePack,
        on_delete=models.CASCADE,
        related_name='items',
        help_text="Deliverable pack"
    )

    deliverable_type = models.CharField(
        max_length=50,
        choices=DELIVERABLE_TYPE_CHOICES,
        help_text="Type of deliverable"
    )

    quantity = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Quantity of this deliverable type"
    )

    description = models.TextField(
        blank=True,
        help_text="Additional description"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['deliverable_type', 'created_at']
        verbose_name = 'Deliverable Pack Item'
        verbose_name_plural = 'Deliverable Pack Items'

    def __str__(self):
        return f"{self.pack.name} - {self.get_deliverable_type_display()} (x{self.quantity})"


class UsageTerms(models.Model):
    """
    Image rights and licensing terms.
    Can be used as templates or custom per deal.
    """

    USAGE_SCOPE_CHOICES = [
        ('digital', 'Digital'),
        ('atl', 'ATL (Above The Line)'),
        ('btl', 'BTL (Below The Line)'),
        ('ooh', 'OOH (Out of Home)'),
        ('packaging', 'Product Packaging'),
        ('in_store', 'In-Store'),
        ('global', 'Global Rights'),
        ('print', 'Print Media'),
        ('broadcast', 'Broadcast (TV/Radio)'),
        ('cinema', 'Cinema'),
        ('events', 'Events'),
    ]

    name = models.CharField(
        max_length=255,
        help_text="Name of the usage terms (e.g., 'Digital Only - 12mo', 'Global ATL + BTL - 24mo')"
    )

    usage_scope = ArrayField(
        models.CharField(max_length=50, choices=USAGE_SCOPE_CHOICES),
        default=list,
        blank=True,
        help_text="Types of usage rights granted"
    )

    territories = models.JSONField(
        default=list,
        blank=True,
        help_text="List of ISO country codes for territories"
    )

    exclusivity_category = models.CharField(
        max_length=100,
        blank=True,
        help_text="Product category for exclusivity (e.g., 'Beverage', 'Automotive')"
    )

    exclusivity_duration_days = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Exclusivity duration in days"
    )

    usage_duration_days = models.IntegerField(
        default=365,
        validators=[MinValueValidator(1)],
        help_text="Usage rights duration in days"
    )

    extensions_allowed = models.BooleanField(
        default=False,
        help_text="Whether usage can be extended"
    )

    buyout = models.BooleanField(
        default=False,
        help_text="Whether this is a full buyout (perpetual rights)"
    )

    brand_list_blocked = models.JSONField(
        default=list,
        blank=True,
        help_text="List of competing brands blocked during exclusivity"
    )

    is_template = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether this is a reusable template"
    )

    # Metadata
    notes = models.TextField(
        blank=True,
        help_text="Additional notes"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Usage Terms'
        verbose_name_plural = 'Usage Terms'

    def __str__(self):
        return self.name


class Deal(models.Model):
    """
    Deal model representing a won opportunity with contract, deliverables, and artists.
    Enhanced version of contract for artist sales with PO, payment terms, etc.
    """

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending_signature', 'Pending Signature'),
        ('signed', 'Signed'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    PAYMENT_TERMS_CHOICES = [
        ('net_30', 'Net 30 Days'),
        ('net_60', 'Net 60 Days'),
        ('net_90', 'Net 90 Days'),
        ('advance_50', '50% Advance + 50% on Delivery'),
        ('advance_30', '30% Advance + 70% on Delivery'),
        ('milestone', 'Milestone-Based'),
        ('on_delivery', 'On Delivery'),
        ('custom', 'Custom Terms'),
    ]

    # Relationships
    opportunity = models.ForeignKey(
        Opportunity,
        on_delete=models.PROTECT,
        related_name='deals',
        help_text="Opportunity that was won"
    )

    account = models.ForeignKey(
        'identity.Entity',
        on_delete=models.PROTECT,
        related_name='deals',
        help_text="Brand or agency"
    )

    deliverable_pack = models.ForeignKey(
        DeliverablePack,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deals',
        help_text="Deliverable pack template used (optional)"
    )

    usage_terms = models.ForeignKey(
        UsageTerms,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deals',
        help_text="Usage terms and rights (optional)"
    )

    department = models.ForeignKey(
        'api.Department',
        on_delete=models.PROTECT,
        related_name='deals',
        null=True,
        blank=True,
        help_text="Department this deal belongs to"
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='deals_created',
        help_text="User who created this deal"
    )

    # Deal details
    contract_number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        blank=True,
        help_text="Auto-generated contract number"
    )

    po_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Purchase Order number from client"
    )

    deal_title = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Deal title"
    )

    # Dates
    start_date = models.DateField(
        null=True,
        blank=True,
        help_text="Deal start date"
    )

    end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Deal end date"
    )

    signed_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when contract was signed"
    )

    # Financial
    fee_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Total deal value"
    )

    currency = models.CharField(
        max_length=3,
        default='EUR',
        help_text="Currency"
    )

    payment_terms = models.CharField(
        max_length=20,
        choices=PAYMENT_TERMS_CHOICES,
        default='net_30',
        help_text="Payment terms"
    )

    # Status
    deal_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        db_index=True,
        help_text="Current status of the deal"
    )

    brand_safety_score = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Brand safety score (1-10)"
    )

    # Files
    contract_file = models.FileField(
        upload_to='deals/contracts/',
        null=True,
        blank=True,
        help_text="Signed contract file"
    )

    # Metadata
    notes = models.TextField(
        blank=True,
        help_text="Additional notes"
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['deal_status', 'created_at']),
            models.Index(fields=['account', 'deal_status']),
            models.Index(fields=['department', 'deal_status']),
            models.Index(fields=['start_date']),
            models.Index(fields=['end_date']),
        ]
        verbose_name = 'Deal'
        verbose_name_plural = 'Deals'

    def __str__(self):
        return f"{self.contract_number or 'DRAFT'} - {self.deal_title}"

    def save(self, *args, **kwargs):
        """Auto-generate contract number if not set"""
        if not self.contract_number:
            year = timezone.now().year
            sequence_name = f'deal_contract_{year}'
            next_num = get_next_value(sequence_name)
            self.contract_number = f"AS-{year}-{next_num:05d}"
        super().save(*args, **kwargs)


class DealArtist(models.Model):
    """
    M2M relationship between Deal and Artist entities with fees and revenue share.
    """

    ROLE_CHOICES = [
        ('main', 'Main Artist'),
        ('featured', 'Featured'),
        ('guest', 'Guest'),
        ('ensemble', 'Ensemble'),
    ]

    CONTRACT_STATUS_CHOICES = [
        ('pending', 'Pending Signature'),
        ('signed', 'Signed'),
        ('active', 'Active'),
    ]

    deal = models.ForeignKey(
        Deal,
        on_delete=models.CASCADE,
        related_name='deal_artists',
        help_text="Deal"
    )

    artist = models.ForeignKey(
        'identity.Entity',
        on_delete=models.PROTECT,
        related_name='artist_deals',
        limit_choices_to={'entity_roles__role': 'artist'},
        help_text="Artist entity"
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='main',
        help_text="Artist role in this deal"
    )

    artist_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Artist fee for this deal"
    )

    revenue_share_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        help_text="Revenue share percentage (for performance-based deals)"
    )

    contract_status = models.CharField(
        max_length=20,
        choices=CONTRACT_STATUS_CHOICES,
        default='pending',
        help_text="Artist contract status"
    )

    signed_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when artist signed"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['deal', 'artist']
        ordering = ['role', 'created_at']
        verbose_name = 'Deal Artist'
        verbose_name_plural = 'Deal Artists'

    def __str__(self):
        return f"{self.artist.display_name} - {self.deal.deal_title} ({self.get_role_display()})"


class DealDeliverable(models.Model):
    """
    Specific deliverables for a deal with approval tracking and KPIs.
    """

    STATUS_CHOICES = [
        ('planned', 'Planned'),
        ('in_progress', 'In Progress'),
        ('submitted', 'Submitted for Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('revision_requested', 'Revision Requested'),
        ('completed', 'Completed'),
    ]

    DELIVERABLE_TYPE_CHOICES = DeliverablePackItem.DELIVERABLE_TYPE_CHOICES

    deal = models.ForeignKey(
        Deal,
        on_delete=models.CASCADE,
        related_name='deliverables',
        help_text="Deal"
    )

    deliverable_type = models.CharField(
        max_length=50,
        choices=DELIVERABLE_TYPE_CHOICES,
        help_text="Type of deliverable"
    )

    quantity = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Quantity"
    )

    description = models.TextField(
        blank=True,
        help_text="Description"
    )

    due_date = models.DateField(
        null=True,
        blank=True,
        help_text="Due date"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='planned',
        db_index=True,
        help_text="Current status"
    )

    asset_url = models.URLField(
        blank=True,
        max_length=500,
        help_text="URL to asset (S3, Google Drive, etc.)"
    )

    kpi_target = models.JSONField(
        default=dict,
        blank=True,
        help_text="Target KPIs (e.g., {views: 100000, engagement_rate: 0.05})"
    )

    kpi_actual = models.JSONField(
        default=dict,
        blank=True,
        help_text="Actual KPIs achieved"
    )

    cost_center = models.CharField(
        max_length=100,
        blank=True,
        help_text="Internal cost center code"
    )

    notes = models.TextField(
        blank=True,
        help_text="Additional notes"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['due_date', 'created_at']
        indexes = [
            models.Index(fields=['deal', 'status']),
            models.Index(fields=['due_date']),
            models.Index(fields=['status', 'due_date']),
        ]
        verbose_name = 'Deal Deliverable'
        verbose_name_plural = 'Deal Deliverables'

    def __str__(self):
        return f"{self.deal.deal_title} - {self.get_deliverable_type_display()}"


class Approval(models.Model):
    """
    Multi-stage approval workflow for deliverables.
    """

    STAGE_CHOICES = [
        ('concept', 'Concept'),
        ('script', 'Script'),
        ('storyboard', 'Storyboard'),
        ('rough_cut', 'Rough Cut'),
        ('final_cut', 'Final Cut'),
        ('caption', 'Caption/Copy'),
        ('static_kv', 'Static Key Visual'),
        ('usage_extension', 'Usage Extension Request'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('changes_requested', 'Changes Requested'),
        ('rejected', 'Rejected'),
    ]

    deal = models.ForeignKey(
        Deal,
        on_delete=models.CASCADE,
        related_name='approvals',
        help_text="Deal"
    )

    deliverable = models.ForeignKey(
        DealDeliverable,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='approvals',
        help_text="Specific deliverable (optional)"
    )

    stage = models.CharField(
        max_length=20,
        choices=STAGE_CHOICES,
        help_text="Approval stage"
    )

    version = models.IntegerField(
        default=1,
        help_text="Version number for this stage"
    )

    submitted_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When submitted for approval"
    )

    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When approved/rejected"
    )

    approver_contact = models.ForeignKey(
        'identity.ContactPerson',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approvals_given',
        help_text="Client-side approver"
    )

    approver_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approvals_given',
        help_text="Internal approver"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True,
        help_text="Approval status"
    )

    notes = models.TextField(
        blank=True,
        help_text="Approval notes/feedback"
    )

    file_url = models.FileField(
        upload_to='approvals/',
        null=True,
        blank=True,
        help_text="File to be approved"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['deal', 'status']),
            models.Index(fields=['deliverable', 'stage']),
            models.Index(fields=['status', 'submitted_at']),
        ]
        verbose_name = 'Approval'
        verbose_name_plural = 'Approvals'

    def __str__(self):
        return f"{self.deal.deal_title} - {self.get_stage_display()} v{self.version} ({self.get_status_display()})"


class Invoice(models.Model):
    """
    Invoice tracking for deals.
    """

    TYPE_CHOICES = [
        ('advance', 'Advance Payment'),
        ('milestone', 'Milestone Payment'),
        ('final', 'Final Payment'),
        ('full', 'Full Payment'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('sent', 'Sent to Client'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]

    deal = models.ForeignKey(
        Deal,
        on_delete=models.CASCADE,
        related_name='invoices',
        help_text="Deal"
    )

    invoice_number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        blank=True,
        help_text="Auto-generated invoice number"
    )

    invoice_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='full',
        help_text="Invoice type"
    )

    issue_date = models.DateField(
        help_text="Invoice issue date"
    )

    due_date = models.DateField(
        help_text="Payment due date"
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Invoice amount"
    )

    currency = models.CharField(
        max_length=3,
        default='EUR',
        help_text="Currency"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        db_index=True,
        help_text="Invoice status"
    )

    paid_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when payment was received"
    )

    pdf_url = models.FileField(
        upload_to='invoices/',
        null=True,
        blank=True,
        help_text="Invoice PDF file"
    )

    notes = models.TextField(
        blank=True,
        help_text="Additional notes"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-issue_date', '-created_at']
        indexes = [
            models.Index(fields=['deal', 'status']),
            models.Index(fields=['status', 'due_date']),
            models.Index(fields=['issue_date']),
        ]
        verbose_name = 'Invoice'
        verbose_name_plural = 'Invoices'

    def __str__(self):
        return f"{self.invoice_number or 'DRAFT'} - {self.deal.deal_title}"

    def save(self, *args, **kwargs):
        """Auto-generate invoice number if not set"""
        if not self.invoice_number:
            year = timezone.now().year
            sequence_name = f'deal_invoice_{year}'
            next_num = get_next_value(sequence_name)
            self.invoice_number = f"INV-AS-{year}-{next_num:05d}"
        super().save(*args, **kwargs)
