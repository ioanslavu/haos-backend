from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from identity.models import Entity
from catalog.models import Work, Recording, Release

User = get_user_model()


class ContractTemplate(models.Model):
    """
    Contract template stored in Google Drive.
    Templates contain placeholders that get filled when generating contracts.
    """
    name = models.CharField(max_length=255, help_text="Template name")
    description = models.TextField(blank=True, help_text="Template description")

    # Series identifier for contract numbering (e.g., "1", "2", "A", "2025")
    series = models.CharField(
        max_length=50,
        unique=True,
        help_text="Series identifier for contract numbering (e.g., 1, 2, A, 2025). Must be unique."
    )

    # Google Drive file ID of the current active template
    gdrive_template_file_id = models.CharField(
        max_length=255,
        help_text="Google Drive file ID of the template document"
    )

    # Placeholders definition - JSON array of placeholder objects
    # Example: [{"key": "client_name", "label": "Client Name", "type": "text", "required": true}]
    placeholders = models.JSONField(
        default=list,
        help_text="Array of placeholder definitions"
    )

    # Google Drive folder where generated contracts will be saved
    gdrive_output_folder_id = models.CharField(
        max_length=255,
        help_text="Google Drive folder ID for generated contracts"
    )

    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_templates')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def get_next_contract_number(self):
        """
        Generate the next contract number for this template's series.
        Format: {SERIES}-{number} (e.g., "HAHM-1", "HAND-15")
        Numbers have no leading zeros and reset every year on January 1st.
        """
        from sequences import get_next_value
        from django.utils import timezone

        # Get current year
        current_year = timezone.now().year

        # Use a sequence specific to this template's series AND year
        # This automatically resets the counter when the year changes
        sequence_name = f'contract_series_{self.series}_{current_year}'
        next_number = get_next_value(sequence_name)

        return f"{self.series}-{next_number}"

    def get_last_contract_number(self):
        """
        Get the last contract number generated for this series.
        Returns None if no contracts exist yet.
        """
        last_contract = self.contracts.order_by('-created_at').first()
        if last_contract:
            return last_contract.contract_number
        return None


class ContractTemplateVersion(models.Model):
    """
    Version control for contract templates.
    Tracks changes to templates over time.
    """
    template = models.ForeignKey(ContractTemplate, on_delete=models.CASCADE, related_name='versions')
    version_number = models.PositiveIntegerField(help_text="Sequential version number")

    # Google Drive file ID of this version
    gdrive_file_id = models.CharField(max_length=255, help_text="Google Drive file ID of this version")

    # Snapshot of placeholders at this version
    placeholders_snapshot = models.JSONField(default=list)

    # Change description
    change_description = models.TextField(blank=True, help_text="What changed in this version")

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-version_number']
        unique_together = ['template', 'version_number']

    def __str__(self):
        return f"{self.template.name} v{self.version_number}"


class Contract(models.Model):
    """
    Individual contract generated from a template.
    """
    STATUS_CHOICES = [
        ('processing', 'Processing'),
        ('draft', 'Draft'),
        ('pending_signature', 'Pending Signature'),
        ('signed', 'Signed'),
        ('cancelled', 'Cancelled'),
        ('failed', 'Failed'),
    ]

    CONTRACT_TYPE_CHOICES = [
        ('artist_master', 'Artist Master Agreement'),
        ('producer_service', 'Producer Service Agreement'),
        ('publishing_writer', 'Publishing Writer Agreement'),
        ('publishing_admin', 'Publishing Administration'),
        ('co_pub', 'Co-Publishing Agreement'),
        ('license_sync', 'Synchronization License'),
        ('co_label', 'Co-Label Agreement'),
        ('video_production', 'Video Production Agreement'),
        ('digital_dist', 'Digital Distribution Agreement'),
    ]

    # Department ownership for access control (nullable for legacy rows)
    department = models.ForeignKey(
        'api.Department',
        on_delete=models.PROTECT,
        related_name='contracts',
        blank=True,
        null=True,
        help_text="Owning department for access control"
    )

    # Template fields
    template = models.ForeignKey(
        ContractTemplate,
        on_delete=models.PROTECT,
        related_name='contracts'
    )
    template_version = models.ForeignKey(
        ContractTemplateVersion,
        on_delete=models.PROTECT,
        related_name='contracts',
        null=True,
        blank=True
    )

    # Contract identification
    contract_number = models.CharField(max_length=100, unique=True, help_text="Unique contract identifier")
    title = models.CharField(max_length=255, help_text="Contract title")

    # Contract type
    contract_type = models.CharField(
        max_length=30,
        choices=CONTRACT_TYPE_CHOICES,
        blank=True,
        null=True,
        help_text="Type of contract"
    )

    # Parties (Entity-based)
    label_entity = models.ForeignKey(
        Entity,
        on_delete=models.PROTECT,
        related_name='contracts_as_label',
        blank=True,
        null=True,
        help_text="Your label/company entity"
    )

    counterparty_entity = models.ForeignKey(
        Entity,
        on_delete=models.PROTECT,
        related_name='contracts_as_counterparty',
        blank=True,
        null=True,
        help_text="The other party (artist, producer, etc.)"
    )

    # Contract terms
    term_start = models.DateField(
        blank=True,
        null=True,
        help_text="Contract start date"
    )

    term_end = models.DateField(
        blank=True,
        null=True,
        help_text="Contract end date"
    )

    territory = models.CharField(
        max_length=100,
        default="World",
        blank=True,
        help_text="Territory coverage"
    )

    # Financial terms
    advance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Advance amount"
    )

    recoupable = models.BooleanField(
        default=True,
        help_text="Is the advance recoupable?"
    )

    # Placeholder values used to generate this contract
    placeholder_values = models.JSONField(default=dict, help_text="Values used to fill placeholders")

    # Google Drive storage
    gdrive_file_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Google Drive file ID of contract (Google Docs)"
    )
    gdrive_file_url = models.URLField(blank=True, help_text="Google Drive file URL (Google Docs)")

    # PDF file (generated when sending for signature)
    gdrive_pdf_file_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Google Drive file ID of PDF version"
    )
    gdrive_pdf_file_url = models.URLField(blank=True, help_text="Google Drive file URL (PDF)")

    # Public sharing
    is_public = models.BooleanField(default=False, help_text="Whether contract is publicly accessible")
    public_share_url = models.URLField(blank=True, help_text="Public sharing URL")

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='processing')

    # Async task tracking
    celery_task_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Celery task ID for async contract generation"
    )
    error_message = models.TextField(
        blank=True,
        help_text="Error message if contract generation failed"
    )

    # Dropbox Sign integration
    dropbox_sign_request_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Dropbox Sign signature request ID"
    )

    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_contracts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    signed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        permissions = [
            ('view_all_contracts', 'Can view all contracts across departments'),
            ('publish_contract', 'Can make contract public'),
            ('send_for_signature', 'Can send contract for signature'),
            ('regenerate_contract', 'Can regenerate contract'),
        ]

    def __str__(self):
        return f"{self.contract_number} - {self.title}"


class ContractSignature(models.Model):
    """
    Signature tracking for contracts via Dropbox Sign.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('viewed', 'Viewed'),
        ('signed', 'Signed'),
        ('declined', 'Declined'),
    ]

    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name='signatures')

    # Signer information
    signer_email = models.EmailField(help_text="Email of the signer")
    signer_name = models.CharField(max_length=255, help_text="Name of the signer")
    signer_role = models.CharField(max_length=100, blank=True, help_text="Role of the signer (e.g., 'Client', 'Contractor')")

    # Dropbox Sign data
    dropbox_sign_signature_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Dropbox Sign signature ID"
    )

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Timestamps
    sent_at = models.DateTimeField(null=True, blank=True)
    viewed_at = models.DateTimeField(null=True, blank=True)
    signed_at = models.DateTimeField(null=True, blank=True)
    declined_at = models.DateTimeField(null=True, blank=True)

    # Decline reason if applicable
    decline_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.signer_email} - {self.contract.contract_number} ({self.status})"


class ContractScope(models.Model):
    """
    Defines what Works, Recordings, or Releases are covered by a contract.
    """

    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name='scopes'
    )

    # Scope objects (nullable, can specify one or more)
    work = models.ForeignKey(
        Work,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='contract_scopes'
    )

    recording = models.ForeignKey(
        Recording,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='contract_scopes'
    )

    release = models.ForeignKey(
        Release,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='contract_scopes'
    )

    # Option to include all works/recordings during contract term
    all_in_term = models.BooleanField(
        default=False,
        help_text="Include all works/recordings created during contract term"
    )

    # Additional scope parameters
    include_derivatives = models.BooleanField(
        default=True,
        help_text="Include remixes, covers, and other derivatives"
    )

    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Notes about this scope item"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['contract']),
            models.Index(fields=['work']),
            models.Index(fields=['recording']),
            models.Index(fields=['release']),
        ]

    def __str__(self):
        if self.all_in_term:
            return f"{self.contract.contract_number} - All in term"
        elif self.work:
            return f"{self.contract.contract_number} - Work: {self.work.title}"
        elif self.recording:
            return f"{self.contract.contract_number} - Recording: {self.recording.title}"
        elif self.release:
            return f"{self.contract.contract_number} - Release: {self.release.title}"
        return f"{self.contract.contract_number} - Scope"

    def clean(self):
        """Ensure at least one scope is specified."""
        from django.core.exceptions import ValidationError

        if not self.all_in_term and not self.work and not self.recording and not self.release:
            raise ValidationError("Must specify at least one scope (work, recording, release, or all_in_term)")


class ContractRate(models.Model):
    """
    Defines royalty rates for different channels/uses in a contract.
    """

    RIGHT_TYPE_CHOICES = [
        ('master', 'Master Rights'),
        ('publ', 'Publishing Rights'),
        ('sync', 'Synchronization Rights'),
        ('merch', 'Merchandise Rights'),
    ]

    CHANNEL_CHOICES = [
        ('stream', 'Streaming'),
        ('download', 'Digital Download'),
        ('physical', 'Physical Sales'),
        ('sync', 'Synchronization'),
        ('ugc', 'User Generated Content'),
        ('shorts', 'Shorts/Reels'),
        ('broadcast', 'Broadcast'),
        ('public_perf', 'Public Performance'),
    ]

    BASE_CHOICES = [
        ('gross', 'Gross Revenue'),
        ('net', 'Net Revenue'),
        ('wholesale', 'Wholesale Price'),
        ('retail', 'Retail Price'),
    ]

    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name='rates'
    )

    right_type = models.CharField(
        max_length=10,
        choices=RIGHT_TYPE_CHOICES,
        help_text="Type of right"
    )

    channel = models.CharField(
        max_length=20,
        choices=CHANNEL_CHOICES,
        help_text="Distribution channel"
    )

    # Rate information
    percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        help_text="Royalty percentage"
    )

    base = models.CharField(
        max_length=10,
        choices=BASE_CHOICES,
        default='net',
        help_text="What the percentage is based on"
    )

    # Minimum rates
    minimum_rate = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        blank=True,
        null=True,
        help_text="Minimum rate per unit (e.g., per stream)"
    )

    # Producer points (for recording contracts)
    producer_points_default = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        help_text="Default producer points for recordings under this contract"
    )

    # Additional terms
    escalation_clause = models.TextField(
        blank=True,
        null=True,
        help_text="Rate escalation terms (e.g., increases after X units sold)"
    )

    notes = models.TextField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['contract', 'right_type', 'channel']
        indexes = [
            models.Index(fields=['contract', 'right_type', 'channel']),
        ]
        ordering = ['right_type', 'channel']

    def __str__(self):
        return (f"{self.contract.contract_number} - "
                f"{self.get_right_type_display()} - "
                f"{self.get_channel_display()}: {self.percent}%")

    def get_effective_rate(self, units=None):
        """
        Calculate effective rate considering minimums and escalations.
        """
        base_rate = self.percent

        # Apply escalation if applicable
        if self.escalation_clause and units:
            # This would need custom logic based on the escalation clause
            # For now, return base rate
            pass

        return base_rate

    @classmethod
    def get_default_rates(cls, contract_type):
        """
        Get default rates for a contract type (industry standards).
        """
        defaults = {
            'artist_master': {
                ('master', 'stream'): {'percent': Decimal('20.00'), 'base': 'net'},
                ('master', 'download'): {'percent': Decimal('20.00'), 'base': 'net'},
                ('master', 'physical'): {'percent': Decimal('15.00'), 'base': 'net'},
            },
            'producer_service': {
                ('master', 'stream'): {'percent': Decimal('3.00'), 'base': 'net'},
                ('master', 'download'): {'percent': Decimal('3.00'), 'base': 'net'},
            },
            'publishing_writer': {
                ('publ', 'stream'): {'percent': Decimal('50.00'), 'base': 'gross'},
                ('publ', 'download'): {'percent': Decimal('50.00'), 'base': 'gross'},
                ('publ', 'sync'): {'percent': Decimal('50.00'), 'base': 'gross'},
            },
        }


class ContractTerms(models.Model):
    """
    Stores specific terms for a contract generation session.
    These are the business terms that will fill contract placeholders.
    """

    # Link to the contract being generated
    contract = models.OneToOneField(
        'Contract',
        on_delete=models.CASCADE,
        related_name='terms',
        null=True,
        blank=True,
        help_text="Associated contract (null for draft/preview)"
    )

    # Entity this contract is for
    entity = models.ForeignKey(
        Entity,
        on_delete=models.CASCADE,
        related_name='contract_terms'
    )

    # Contract duration
    contract_duration_years = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(50)],
        help_text="Contract duration in years"
    )

    notice_period_days = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(365)],
        help_text="Notice period in days before contract end"
    )

    auto_renewal = models.BooleanField(
        default=False,
        help_text="Whether contract auto-renews"
    )

    auto_renewal_years = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Auto-renewal period in years"
    )

    # Investment terms
    minimum_launches_per_year = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Minimum song launches per year"
    )

    max_investment_per_song = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Maximum investment per song in EUR"
    )

    max_investment_per_year = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Maximum total investment per year in EUR"
    )

    # Financial terms
    penalty_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('50000.00'),
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Penalty amount for contract breach in EUR"
    )

    currency = models.CharField(
        max_length=3,
        default='EUR',
        help_text="Currency for all financial terms"
    )

    # Contract start date
    start_date = models.DateField(
        help_text="Contract start date"
    )

    # Additional notes or special terms
    special_terms = models.TextField(
        blank=True,
        help_text="Any special terms or conditions"
    )

    # Auto-save data
    draft_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Auto-saved form data"
    )

    # Commission structure (range-based)
    commission_structure = models.JSONField(
        default=dict,
        blank=True,
        help_text="Range-based commission structure: first_years, middle_years, last_years with share type values"
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_contract_terms'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Contract Terms"
        verbose_name_plural = "Contract Terms"
        ordering = ['-created_at']

    def __str__(self):
        return f"Terms for {self.entity.display_name} - {self.contract_duration_years} years"

    def get_placeholders(self):
        """
        Convert contract terms to placeholder values.
        Includes range-based commission placeholders.
        """
        placeholders = {
            'contract.duration_years': str(self.contract_duration_years),
            'contract.duration': f"{self.contract_duration_years} ani" if self.contract_duration_years > 1 else "1 an",
            'contract.notice_period_days': str(self.notice_period_days),
            'contract.notice_period': f"{self.notice_period_days} zile",
            'contract.auto_renewal': 'da' if self.auto_renewal else 'nu',
            'contract.auto_renewal_years': str(self.auto_renewal_years or ''),
            'contract.minimum_launches': str(self.minimum_launches_per_year),
            'investment.per_song': f"{self.max_investment_per_song:,.2f}",
            'investment.per_year': f"{self.max_investment_per_year:,.2f}",
            'contract.penalty': f"{self.penalty_amount:,.2f}",
            'contract.currency': self.currency,
            'contract.start_date': self.start_date.strftime('%d.%m.%Y'),
        }

        # Add commission structure placeholders if available
        if self.commission_structure:
            # First years
            if 'first_years' in self.commission_structure:
                first_years = self.commission_structure['first_years']
                count = first_years.get('count', 0)
                placeholders['commission.first_years_count'] = str(count)

                for share_type, value in first_years.items():
                    if share_type != 'count':
                        placeholders[f'commission.first_years.{share_type}'] = str(value)

            # Last years
            if 'last_years' in self.commission_structure:
                last_years = self.commission_structure['last_years']
                count = last_years.get('count', 0)
                placeholders['commission.last_years_count'] = str(count)

                for share_type, value in last_years.items():
                    if share_type != 'count':
                        placeholders[f'commission.last_years.{share_type}'] = str(value)

        return placeholders

    def expand_commission_structure(self):
        """
        Expand range-based commission structure into per-year share records.
        Returns list of dicts ready to create ContractShare objects.

        Example commission_structure:
        {
            "first_years": {"count": 2, "concert": "20.0000", "rights": "25.0000"},
            "middle_years": {"concert": "25.0000", "rights": "30.0000"},
            "last_years": {"count": 2, "concert": "30.0000", "rights": "35.0000"}
        }

        Returns: List of {share_type_code, value, unit, valid_from, valid_to}
        """
        from dateutil.relativedelta import relativedelta

        if not self.commission_structure:
            return []

        shares_data = []
        duration_years = self.contract_duration_years
        start_date = self.start_date

        first_years_data = self.commission_structure.get('first_years', {})
        middle_years_data = self.commission_structure.get('middle_years', {})
        last_years_data = self.commission_structure.get('last_years', {})

        first_count = first_years_data.get('count', 0)
        last_count = last_years_data.get('count', 0)

        # Calculate year ranges
        # First X years: year 1 to X
        # Middle years: year X+1 to duration-Z
        # Last Z years: year duration-Z+1 to duration

        for year in range(1, duration_years + 1):
            year_start = start_date + relativedelta(years=year-1)
            year_end = start_date + relativedelta(years=year) - relativedelta(days=1)

            # Determine which range this year belongs to
            if year <= first_count:
                # First years
                rates = first_years_data
            elif year > duration_years - last_count:
                # Last years
                rates = last_years_data
            else:
                # Middle years
                rates = middle_years_data

            # Create share records for this year
            for share_type_code, value in rates.items():
                if share_type_code == 'count':
                    continue

                shares_data.append({
                    'share_type_code': share_type_code,
                    'value': str(value),
                    'unit': 'percent',
                    'valid_from': year_start,
                    'valid_to': year_end
                })

        return shares_data


class ShareType(models.Model):
    """
    Canonical share types used across contracts.
    Examples: concert_commission, master_share, writer_share, producer_points, etc.
    """
    code = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="Machine-readable share type code"
    )

    name = models.CharField(
        max_length=120,
        help_text="Human-readable share type name"
    )

    description = models.TextField(
        blank=True,
        help_text="Description of this share type"
    )

    # Template placeholder mapping
    placeholder_keys = models.JSONField(
        default=list,
        help_text="List of template placeholder keys for this share type. Use {year} for year-based placeholders."
    )

    # Optional: scope to specific contract types
    contract_types = models.JSONField(
        default=list,
        blank=True,
        help_text="List of contract types that use this share type (empty = all types)"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['code']
        verbose_name = "Share Type"
        verbose_name_plural = "Share Types"

    def __str__(self):
        return f"{self.code} - {self.name}"


class ContractShare(models.Model):
    """
    One row per contract + share_type + value with effective dates.
    Supports time-based rate changes and multi-year contracts.
    """

    UNIT_CHOICES = [
        ('percent', 'Percentage'),
        ('points', 'Points'),
        ('flat', 'Flat Amount'),
    ]

    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name='shares'
    )

    share_type = models.ForeignKey(
        ShareType,
        on_delete=models.PROTECT,
        related_name='contract_shares'
    )

    value = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0.0000'))],
        help_text="Share value (e.g., 15.0000 for 15%)"
    )

    unit = models.CharField(
        max_length=16,
        default='percent',
        choices=UNIT_CHOICES,
        help_text="Unit of measurement for the value"
    )

    # Time-based validity
    valid_from = models.DateField(
        help_text="Start date for this share rate"
    )

    valid_to = models.DateField(
        null=True,
        blank=True,
        help_text="End date (null = open-ended)"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['valid_from', 'share_type__code']
        indexes = [
            models.Index(fields=['contract', 'share_type']),
            models.Index(fields=['share_type', 'valid_from']),
            models.Index(fields=['valid_from', 'valid_to']),
        ]
        verbose_name = "Contract Share"
        verbose_name_plural = "Contract Shares"

    def __str__(self):
        return f"{self.contract.contract_number} - {self.share_type.code}: {self.value}{self.unit}"

    def get_placeholder_values(self):
        """Generate placeholder key-value pairs for this share."""
        placeholders = {}

        for key_template in self.share_type.placeholder_keys:
            # Calculate year from valid_from if placeholder contains {year}
            if '{year}' in key_template:
                year = self._calculate_year()
                key = key_template.replace('{year}', str(year))
            else:
                key = key_template

            # Format value based on unit
            if self.unit == 'percent':
                placeholders[key] = f"{self.value}"
            elif self.unit == 'points':
                placeholders[key] = f"{self.value}"
            else:
                placeholders[key] = f"{self.value}"

        return placeholders

    def _calculate_year(self):
        """Calculate contract year from valid_from date."""
        if not self.contract.term_start:
            return 1

        delta = (self.valid_from - self.contract.term_start).days
        return (delta // 365) + 1


class WebhookEvent(models.Model):
    """
    Track all webhook events for idempotency, security, and audit.
    Stores every webhook received from Dropbox Sign with verification status.
    """
    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name='webhook_events',
        null=True,
        blank=True,
        help_text="Related contract (null if contract not found)"
    )

    # Event identification
    event_type = models.CharField(
        max_length=100,
        help_text="Event type from Dropbox Sign (signature_request_signed, etc.)"
    )
    signature_request_id = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Dropbox Sign signature request ID"
    )
    signer_email = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Email of the signer (if applicable)"
    )
    event_hash = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="SHA256 hash for idempotency (prevents duplicate processing)"
    )

    # Verification tracking
    received_at = models.DateTimeField(auto_now_add=True, db_index=True)
    processed = models.BooleanField(
        default=False,
        help_text="Whether this event was successfully processed"
    )
    verified_with_api = models.BooleanField(
        default=False,
        help_text="Whether event was verified with Dropbox Sign API"
    )
    api_verification_attempts = models.IntegerField(
        default=0,
        help_text="Number of API verification attempts"
    )

    # Audit data
    raw_payload = models.JSONField(
        help_text="Complete webhook payload for forensics"
    )
    client_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of webhook sender"
    )
    verification_result = models.JSONField(
        null=True,
        blank=True,
        help_text="Result from Dropbox Sign API verification"
    )
    error_message = models.TextField(
        blank=True,
        help_text="Error message if processing failed"
    )

    class Meta:
        ordering = ['-received_at']
        indexes = [
            models.Index(fields=['event_hash']),
            models.Index(fields=['contract', 'event_type', 'received_at']),
            models.Index(fields=['signature_request_id', 'event_type']),
            models.Index(fields=['processed', 'received_at']),
        ]
        verbose_name = "Webhook Event"
        verbose_name_plural = "Webhook Events"

    def __str__(self):
        return f"{self.event_type} - {self.signature_request_id} @ {self.received_at}"
