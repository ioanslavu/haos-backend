"""
Artist Sales CRM - Unified Opportunity Models

Modern, scalable sales pipeline management with unified opportunity model.
Replaces the old Brief → Opportunity → Proposal → Deal flow.

Design: Single Opportunity object flows through all stages from brief intake to completion.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
from sequences import get_next_value

User = get_user_model()


class Opportunity(models.Model):
    """
    Unified sales opportunity - flows from initial brief through execution.

    This single model replaces:
    - Brief (old intake model)
    - Opportunity (old pipeline)
    - Proposal (now versioned within opportunity)
    - Deal (now later stages of same opportunity)

    Fields are progressively disclosed based on stage - early fields for brief,
    mid-stage fields for proposal, late-stage fields for contract/execution.
    """

    # === PIPELINE STAGES ===
    STAGE_CHOICES = [
        # Early stages (Brief/Qualification)
        ('brief', '📥 Brief Intake'),
        ('qualified', '✅ Qualified'),

        # Artist & Proposal stages
        ('shortlist', '🎤 Artist Shortlist'),
        ('proposal_draft', '📄 Proposal Draft'),
        ('proposal_sent', '📧 Proposal Sent'),
        ('negotiation', '💬 Negotiation'),

        # Contract stages
        ('contract_prep', '📝 Contract Prep'),
        ('contract_sent', '✍️ Contract Sent'),

        # Won & Execution
        ('won', '🎯 Won'),
        ('executing', '🚀 Executing'),
        ('completed', '✨ Completed'),

        # Closed
        ('closed_lost', '❌ Lost'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    # === CORE IDENTITY ===

    opportunity_number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        blank=True,
        help_text="Auto-generated: OPP-2025-00001"
    )

    title = models.CharField(
        max_length=255,
        db_index=True,
        help_text="e.g., 'Nike x Drake - Summer Campaign'"
    )

    # === STAGE & STATUS ===

    stage = models.CharField(
        max_length=20,
        choices=STAGE_CHOICES,
        default='brief',
        db_index=True,
        help_text="Current pipeline stage"
    )

    probability = models.IntegerField(
        default=10,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Probability of closing (%)"
    )

    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='medium',
        db_index=True,
        help_text="Opportunity priority"
    )

    # === RELATIONSHIPS ===

    account = models.ForeignKey(
        'identity.Entity',
        on_delete=models.PROTECT,
        related_name='opportunities',
        help_text="Brand or agency"
    )

    contact_person = models.ForeignKey(
        'identity.ContactPerson',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='opportunities',
        help_text="Primary contact at account"
    )

    owner = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='owned_opportunities',
        help_text="Sales owner responsible for this opportunity"
    )

    team = models.ForeignKey(
        'api.Department',
        on_delete=models.PROTECT,
        related_name='opportunities',
        null=True,
        blank=True,
        help_text="Department/team (e.g., Digital, Artist Sales)"
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_opportunities',
        help_text="User who created this opportunity"
    )

    # === FINANCIAL ===

    estimated_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Estimated deal value"
    )

    currency = models.CharField(
        max_length=3,
        default='EUR',
        help_text="Currency code"
    )

    # === DATES ===

    expected_close_date = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Expected closing date"
    )

    actual_close_date = models.DateField(
        null=True,
        blank=True,
        help_text="Actual close date (won or lost)"
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    # === BRIEF STAGE FIELDS (stages: brief, qualified) ===

    campaign_objectives = models.TextField(
        blank=True,
        help_text="Campaign goals and objectives"
    )

    target_audience = models.TextField(
        blank=True,
        help_text="Target audience description"
    )

    channels = ArrayField(
        models.CharField(max_length=50),
        default=list,
        blank=True,
        help_text="Marketing channels (social, tvc, ooh, print, etc.)"
    )

    brand_category = models.CharField(
        max_length=100,
        blank=True,
        help_text="Brand/product category (e.g., Beverage, Fashion, Tech)"
    )

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

    campaign_start_date = models.DateField(
        null=True,
        blank=True,
        help_text="Desired campaign start date"
    )

    campaign_end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Desired campaign end date"
    )

    # === PROPOSAL STAGE FIELDS (stages: proposal_draft+) ===

    proposal_version = models.IntegerField(
        default=0,
        help_text="Current proposal version number"
    )

    proposal_history = models.JSONField(
        default=list,
        blank=True,
        help_text="Proposal version history with timestamps"
    )

    fee_gross = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Gross fee before discounts"
    )

    agency_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Agency commission/fee"
    )

    discounts = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Total discounts"
    )

    fee_net = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Net fee (calculated: gross - discounts - agency_fee)"
    )

    proposal_sent_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When proposal was sent to client"
    )

    proposal_valid_until = models.DateField(
        null=True,
        blank=True,
        help_text="Proposal validity date"
    )

    # === CONTRACT STAGE FIELDS (stages: won+) ===

    contract_number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        blank=True,
        null=True,
        help_text="Auto-generated when won: AS-2025-00001"
    )

    po_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Client purchase order number"
    )

    contract_signed_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date contract was signed"
    )

    contract_start_date = models.DateField(
        null=True,
        blank=True,
        help_text="Contract start date"
    )

    contract_end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Contract end date"
    )

    contract_file = models.FileField(
        upload_to='opportunities/contracts/',
        null=True,
        blank=True,
        help_text="Signed contract document"
    )

    # === EXECUTION STAGE FIELDS ===

    deliverable_pack = models.ForeignKey(
        'DeliverablePack',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='opportunities',
        help_text="Deliverable pack template (optional)"
    )

    usage_terms = models.ForeignKey(
        'UsageTerms',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='opportunities',
        help_text="Image rights and usage terms (optional)"
    )

    # === LOST OPPORTUNITY FIELDS ===

    lost_reason = models.TextField(
        blank=True,
        help_text="Reason if opportunity was lost"
    )

    lost_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date marked as lost"
    )

    competitor = models.CharField(
        max_length=255,
        blank=True,
        help_text="Competitor who won (if known)"
    )

    # === METADATA ===

    notes = models.TextField(
        blank=True,
        help_text="Internal notes"
    )

    tags = ArrayField(
        models.CharField(max_length=50),
        default=list,
        blank=True,
        help_text="Tags for categorization"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Opportunity'
        verbose_name_plural = 'Opportunities'
        indexes = [
            models.Index(fields=['stage', '-created_at']),
            models.Index(fields=['owner', 'stage']),
            models.Index(fields=['team', 'stage']),
            models.Index(fields=['account', 'stage']),
            models.Index(fields=['expected_close_date']),
            models.Index(fields=['-estimated_value']),
            models.Index(fields=['priority', 'stage']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.opportunity_number or 'DRAFT'} - {self.title}"

    def save(self, *args, **kwargs):
        """Auto-generate numbers and calculate fields on save."""

        # Auto-generate opportunity number if not set
        if not self.opportunity_number:
            year = timezone.now().year
            sequence_name = f'opportunity_{year}'
            next_num = get_next_value(sequence_name)
            self.opportunity_number = f"OPP-{year}-{next_num:05d}"

        # Auto-generate contract number when moving to 'won' stage
        if self.stage == 'won' and not self.contract_number:
            year = timezone.now().year
            sequence_name = f'contract_{year}'
            next_num = get_next_value(sequence_name)
            self.contract_number = f"AS-{year}-{next_num:05d}"

        # Calculate net fee
        self.fee_net = self.fee_gross - self.discounts - self.agency_fee

        # Auto-set probability based on stage
        stage_probabilities = {
            'brief': 10,
            'qualified': 20,
            'shortlist': 30,
            'proposal_draft': 40,
            'proposal_sent': 50,
            'negotiation': 60,
            'contract_prep': 70,
            'contract_sent': 80,
            'won': 90,
            'executing': 100,
            'completed': 100,
            'closed_lost': 0,
        }
        if self.stage in stage_probabilities:
            self.probability = stage_probabilities[self.stage]

        super().save(*args, **kwargs)


class OpportunityArtist(models.Model):
    """
    Artists attached to this opportunity with roles and fees.
    M2M relationship with extra fields.
    """

    ROLE_CHOICES = [
        ('main', 'Main Artist'),
        ('featured', 'Featured'),
        ('guest', 'Guest'),
        ('ensemble', 'Ensemble'),
    ]

    CONTRACT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('signed', 'Signed'),
        ('active', 'Active'),
    ]

    opportunity = models.ForeignKey(
        Opportunity,
        on_delete=models.CASCADE,
        related_name='artists',
        help_text="Opportunity"
    )

    artist = models.ForeignKey(
        'identity.Entity',
        on_delete=models.PROTECT,
        related_name='opportunity_participations',
        limit_choices_to={'entity_roles__role': 'artist'},
        help_text="Artist entity"
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='main',
        help_text="Artist role in this opportunity"
    )

    proposed_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Proposed artist fee (in proposal stage)"
    )

    confirmed_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Confirmed artist fee (after negotiation)"
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
        help_text="Date artist signed contract"
    )

    notes = models.TextField(
        blank=True,
        help_text="Notes about this artist's participation"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['opportunity', 'artist']
        ordering = ['role', 'created_at']
        verbose_name = 'Opportunity Artist'
        verbose_name_plural = 'Opportunity Artists'

    def __str__(self):
        return f"{self.artist.display_name} - {self.opportunity.title} ({self.get_role_display()})"


class OpportunityTask(models.Model):
    """
    Tasks assigned to team members for this opportunity.
    Enables team collaboration and workload tracking.
    """

    TASK_TYPE_CHOICES = [
        ('artist_outreach', 'Artist Outreach'),
        ('proposal_creation', 'Proposal Creation'),
        ('contract_prep', 'Contract Preparation'),
        ('client_meeting', 'Client Meeting'),
        ('deliverable_review', 'Deliverable Review'),
        ('follow_up', 'Follow Up'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    opportunity = models.ForeignKey(
        Opportunity,
        on_delete=models.CASCADE,
        related_name='tasks',
        help_text="Opportunity"
    )

    title = models.CharField(
        max_length=255,
        help_text="Task title"
    )

    description = models.TextField(
        blank=True,
        help_text="Task description"
    )

    task_type = models.CharField(
        max_length=50,
        choices=TASK_TYPE_CHOICES,
        default='other',
        help_text="Type of task"
    )

    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='assigned_opportunity_tasks',
        help_text="User assigned to this task"
    )

    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_opportunity_tasks',
        help_text="User who created/assigned this task"
    )

    due_date = models.DateField(
        null=True,
        blank=True,
        help_text="Task due date"
    )

    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='medium',
        help_text="Task priority"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True,
        help_text="Task status"
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When task was completed"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['due_date', '-priority', 'created_at']
        indexes = [
            models.Index(fields=['opportunity', 'status']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['due_date']),
        ]
        verbose_name = 'Opportunity Task'
        verbose_name_plural = 'Opportunity Tasks'

    def __str__(self):
        return f"{self.title} - {self.opportunity.opportunity_number}"


class OpportunityActivity(models.Model):
    """
    Activity feed for opportunity timeline.
    Tracks all changes and interactions for audit trail and collaboration.
    """

    ACTIVITY_TYPE_CHOICES = [
        ('created', 'Created'),
        ('stage_changed', 'Stage Changed'),
        ('field_updated', 'Field Updated'),
        ('comment_added', 'Comment Added'),
        ('task_created', 'Task Created'),
        ('task_completed', 'Task Completed'),
        ('artist_added', 'Artist Added'),
        ('artist_removed', 'Artist Removed'),
        ('file_uploaded', 'File Uploaded'),
        ('email_sent', 'Email Sent'),
        ('meeting_logged', 'Meeting Logged'),
        ('proposal_sent', 'Proposal Sent'),
        ('contract_sent', 'Contract Sent'),
        ('won', 'Marked as Won'),
        ('lost', 'Marked as Lost'),
    ]

    opportunity = models.ForeignKey(
        Opportunity,
        on_delete=models.CASCADE,
        related_name='activities',
        help_text="Opportunity"
    )

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="User who performed the action (null for system activities)"
    )

    activity_type = models.CharField(
        max_length=50,
        choices=ACTIVITY_TYPE_CHOICES,
        db_index=True,
        help_text="Type of activity"
    )

    title = models.CharField(
        max_length=255,
        help_text="Activity title (e.g., 'Stage changed to Proposal Sent')"
    )

    description = models.TextField(
        blank=True,
        help_text="Detailed description"
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Structured data about the activity"
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['opportunity', '-created_at']),
            models.Index(fields=['activity_type', '-created_at']),
        ]
        verbose_name = 'Opportunity Activity'
        verbose_name_plural = 'Opportunity Activities'

    def __str__(self):
        return f"{self.title} - {self.opportunity.opportunity_number}"


class OpportunityComment(models.Model):
    """
    Comments and internal notes on opportunity.
    Supports team collaboration and communication.
    """

    opportunity = models.ForeignKey(
        Opportunity,
        on_delete=models.CASCADE,
        related_name='comments',
        help_text="Opportunity"
    )

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        help_text="User who created the comment"
    )

    comment = models.TextField(
        help_text="Comment text (supports mentions with @username)"
    )

    is_internal = models.BooleanField(
        default=True,
        help_text="Internal note (vs client-visible)"
    )

    mentions = ArrayField(
        models.IntegerField(),
        default=list,
        blank=True,
        help_text="User IDs mentioned in this comment"
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['opportunity', '-created_at']),
        ]
        verbose_name = 'Opportunity Comment'
        verbose_name_plural = 'Opportunity Comments'

    def __str__(self):
        return f"Comment by {self.user.get_full_name() if self.user else 'Unknown'} - {self.opportunity.opportunity_number}"


class OpportunityDeliverable(models.Model):
    """
    Specific deliverables for this opportunity.
    Tracks what needs to be created/delivered and its status.
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

    STATUS_CHOICES = [
        ('planned', 'Planned'),
        ('in_progress', 'In Progress'),
        ('submitted', 'Submitted for Approval'),
        ('approved', 'Approved'),
        ('revision_requested', 'Revision Requested'),
        ('completed', 'Completed'),
    ]

    opportunity = models.ForeignKey(
        Opportunity,
        on_delete=models.CASCADE,
        related_name='deliverables',
        help_text="Opportunity"
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
        help_text="Target KPIs (e.g., {views: 1000000, engagement_rate: 0.05})"
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
            models.Index(fields=['opportunity', 'status']),
            models.Index(fields=['due_date']),
            models.Index(fields=['status', 'due_date']),
        ]
        verbose_name = 'Opportunity Deliverable'
        verbose_name_plural = 'Opportunity Deliverables'

    def __str__(self):
        return f"{self.opportunity.title} - {self.get_deliverable_type_display()}"


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

    opportunity = models.ForeignKey(
        Opportunity,
        on_delete=models.CASCADE,
        related_name='approvals',
        help_text="Opportunity"
    )

    deliverable = models.ForeignKey(
        OpportunityDeliverable,
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

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True,
        help_text="Approval status"
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

    notes = models.TextField(
        blank=True,
        help_text="Approval notes/feedback"
    )

    file_url = models.URLField(
        max_length=500,
        blank=True,
        default='',
        help_text="URL to file for approval (Google Drive, Dropbox, etc.)"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['opportunity', 'status']),
            models.Index(fields=['deliverable', 'stage']),
            models.Index(fields=['status', 'submitted_at']),
        ]
        verbose_name = 'Approval'
        verbose_name_plural = 'Approvals'

    def __str__(self):
        return f"{self.opportunity.title} - {self.get_stage_display()} v{self.version} ({self.get_status_display()})"


class Invoice(models.Model):
    """
    Invoice tracking for opportunities.
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

    opportunity = models.ForeignKey(
        Opportunity,
        on_delete=models.CASCADE,
        related_name='invoices',
        help_text="Opportunity"
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
            models.Index(fields=['opportunity', 'status']),
            models.Index(fields=['status', 'due_date']),
            models.Index(fields=['issue_date']),
        ]
        verbose_name = 'Invoice'
        verbose_name_plural = 'Invoices'

    def __str__(self):
        return f"{self.invoice_number or 'DRAFT'} - {self.opportunity.title}"

    def save(self, *args, **kwargs):
        """Auto-generate invoice number if not set"""
        if not self.invoice_number:
            year = timezone.now().year
            sequence_name = f'invoice_{year}'
            next_num = get_next_value(sequence_name)
            self.invoice_number = f"INV-AS-{year}-{next_num:05d}"
        super().save(*args, **kwargs)


# === SUPPORTING MODELS (Deliverable Packs & Usage Terms) ===

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

    pack = models.ForeignKey(
        DeliverablePack,
        on_delete=models.CASCADE,
        related_name='items',
        help_text="Deliverable pack"
    )

    deliverable_type = models.CharField(
        max_length=50,
        choices=OpportunityDeliverable.DELIVERABLE_TYPE_CHOICES,
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
    Can be used as templates or custom per opportunity.
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
