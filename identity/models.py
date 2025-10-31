from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from cryptography.fernet import Fernet
from django.conf import settings
import json
from django.utils import timezone
from .policies import SensitiveAccessPolicy  # Ensure model is registered with the app

User = get_user_model()


class Entity(models.Model):
    """
    Entity represents both Physical Persons (PF) and Legal Entities (PJ).
    Replaces the Client model while maintaining backward compatibility.
    """

    KIND_CHOICES = [
        ('PF', 'Physical Person'),
        ('PJ', 'Legal Entity'),
    ]

    # Core identification
    kind = models.CharField(
        max_length=2,
        choices=KIND_CHOICES,
        db_index=True,
        help_text="Entity type: Physical Person or Legal Entity"
    )

    display_name = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Display name for the entity"
    )

    alias_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_index=True,
        help_text="Alternative name or alias for the entity"
    )

    # Name fields for Physical Persons
    first_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="First name (for Physical Persons)"
    )

    last_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Last name (for Physical Persons)"
    )

    # Artist-specific fields
    stage_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Stage/professional name for artists"
    )

    nationality = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Country of origin/nationality"
    )

    gender = models.CharField(
        max_length=1,
        choices=[
            ('M', 'Male'),
            ('F', 'Female'),
            ('O', 'Other'),
        ],
        blank=True,
        null=True,
        help_text="Gender (for Physical Persons)"
    )

    # Profile photo
    profile_photo = models.ImageField(
        upload_to='entity_photos/',
        blank=True,
        null=True,
        help_text="Profile photo for the entity"
    )

    # Banking information
    iban = models.CharField(
        max_length=34,  # Max IBAN length
        blank=True,
        null=True,
        help_text="International Bank Account Number"
    )

    bank_name = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Name of the bank"
    )

    bank_branch = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Bank branch/location"
    )

    # Contact information
    email = models.EmailField(
        blank=True,
        null=True,
        help_text="Primary email address"
    )

    phone = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Primary phone number"
    )

    # Address information
    address = models.TextField(
        blank=True,
        null=True,
        help_text="Full address"
    )

    city = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    state = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="State/Province/County"
    )

    zip_code = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    country = models.CharField(
        max_length=100,
        default="Romania",
        blank=True,
        null=True
    )

    # Business information (mainly for PJ)
    company_registration_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Company registration number (for PJ)"
    )

    vat_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="VAT number (for PJ)"
    )

    # Metadata
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Internal notes"
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='entities_created'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Entity"
        verbose_name_plural = "Entities"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['display_name']),
            models.Index(fields=['kind', 'display_name']),
            models.Index(fields=['email']),
        ]

    def __str__(self):
        return f"{self.display_name} ({self.get_kind_display()})"

    @property
    def identifiers(self):
        """Get identifiers for this entity using generic foreign key."""
        # Identifier is defined later in this file
        return Identifier.objects.filter(
            owner_type='entity',
            owner_id=self.id
        )

    def get_placeholders(self):
        """
        Convert entity data to placeholder key-value pairs for contract generation.
        Maintains backward compatibility with Client model.
        """
        placeholders = {}

        # Entity information - SAME PLACEHOLDERS for both PF and PJ
        if self.display_name:
            placeholders['entity.name'] = self.display_name
            placeholders['entity.full_name'] = self.display_name

        # Gender (for gender placeholders)
        if self.kind == 'PF' and self.gender:
            placeholders['entity.gender'] = self.gender

        # Additional name fields (PF only, but use entity.* prefix)
        if self.kind == 'PF':
            if self.first_name:
                placeholders['entity.first_name'] = self.first_name
            if self.last_name:
                placeholders['entity.last_name'] = self.last_name
            if self.stage_name:
                placeholders['entity.stage_name'] = self.stage_name
            if self.nationality:
                placeholders['entity.nationality'] = self.nationality

        # Contact information - SAME for PF and PJ
        if self.email:
            placeholders['entity.email'] = self.email

        if self.phone:
            placeholders['entity.phone'] = self.phone

        # Address information - SAME for PF and PJ
        if self.address:
            placeholders['entity.address'] = self.address

        if self.city:
            placeholders['entity.city'] = self.city

        if self.state:
            placeholders['entity.state'] = self.state
            placeholders['entity.county'] = self.state  # Romanian alias

        if self.zip_code:
            placeholders['entity.zip_code'] = self.zip_code

        if self.country:
            placeholders['entity.country'] = self.country

        # Banking information - SAME for PF and PJ
        if self.iban:
            placeholders['entity.iban'] = self.iban
            placeholders['entity.bank_account'] = self.iban

        if self.bank_name:
            placeholders['entity.bank_name'] = self.bank_name

        if self.bank_branch:
            placeholders['entity.bank_branch'] = self.bank_branch

        # Business/Legal information - SAME for PF and PJ
        # Romanian system:
        # - For PJ: registration_number = J40/..., CUI = tax ID, VAT = optional
        # - For PF: registration_number might be CNP

        if self.company_registration_number:
            # This is J40/XXXXX/2020 for PJ entities
            placeholders['entity.registration_number'] = self.company_registration_number

        # CUI comes from vat_number field OR identifiers
        cui_value = None
        vat_value = None

        # Check identifiers first
        identifiers = self.identifiers.all()
        for identifier in identifiers:
            if identifier.scheme == 'CUI':
                cui_value = identifier.value
            elif identifier.scheme == 'VAT':
                vat_value = identifier.value
            elif identifier.scheme == 'IBAN' and identifier.value:
                placeholders['entity.iban'] = identifier.value
                placeholders['entity.bank_account'] = identifier.value

        # If no CUI in identifiers, use vat_number as CUI
        if not cui_value and self.vat_number:
            cui_value = self.vat_number

        # Set CUI placeholder
        if cui_value:
            placeholders['entity.cui'] = cui_value

        # VAT number (optional, defaults to CUI if not set)
        if vat_value:
            placeholders['entity.vat_number'] = vat_value
            placeholders['entity.vat'] = vat_value
        elif cui_value:
            # If no separate VAT, use CUI
            placeholders['entity.vat_number'] = cui_value
            placeholders['entity.vat'] = cui_value

        # Get ID and sensitive information for PF
        if self.kind == 'PF' and hasattr(self, 'sensitive_identity'):
            sensitive = self.sensitive_identity

            # Level 2: Type-aware placeholders (always available)
            if sensitive.identification_type == 'ID_CARD':
                placeholders['entity.id_document_type'] = 'CI'
                placeholders['entity.id_document_type_full'] = 'Carte de Identitate (CI)'
                placeholders['entity.id_document_type_en'] = 'Romanian ID Card (CI)'
            else:  # PASSPORT
                placeholders['entity.id_document_type'] = 'Pașaport'
                placeholders['entity.id_document_type_full'] = 'Pașaport'
                placeholders['entity.id_document_type_en'] = 'Passport'

            # ID Card specific fields
            if sensitive.identification_type == 'ID_CARD':
                if sensitive.id_series:
                    placeholders['id_series'] = sensitive.id_series
                    placeholders['id.series'] = sensitive.id_series
                if sensitive.id_number:
                    placeholders['id_number'] = sensitive.id_number
                    placeholders['id.number'] = sensitive.id_number
                # CNP - full value for contracts (not masked)
                if sensitive._cnp_encrypted:
                    cnp_value = sensitive.cnp
                    placeholders['cnp'] = cnp_value
                    placeholders['entity.cnp'] = cnp_value
                    # Smart placeholder: primary number (CNP for ID card)
                    placeholders['entity.id_primary_number'] = cnp_value

                # Series and number combined
                if sensitive.id_series and sensitive.id_number:
                    placeholders['entity.id_series_number'] = f"{sensitive.id_series} {sensitive.id_number}"

                # Level 3: Complete phrase placeholders for ID Card
                parts = []
                if sensitive.id_series and sensitive.id_number:
                    parts.append(f"CI seria {sensitive.id_series} nr. {sensitive.id_number}")
                if sensitive._cnp_encrypted:
                    parts.append(f"CNP {sensitive.cnp}")

                if parts:
                    placeholders['entity.identification_short'] = ', '.join(parts)

                # Full identification with issued details
                full_parts = parts.copy()
                if sensitive.id_issued_by:
                    full_parts.append(f"eliberat de {sensitive.id_issued_by}")
                if sensitive.id_issued_date:
                    full_parts.append(f"la data de {sensitive.id_issued_date}")
                if sensitive.id_expiry_date:
                    full_parts.append(f"valabil până la {sensitive.id_expiry_date}")

                if full_parts:
                    placeholders['entity.identification_full'] = ', '.join(full_parts)

            # Passport specific fields
            elif sensitive.identification_type == 'PASSPORT':
                if sensitive._passport_number_encrypted:
                    passport_num = sensitive.passport_number
                    placeholders['passport_number'] = passport_num
                    placeholders['entity.passport_number'] = passport_num
                    # Smart placeholder: primary number (passport number for passport)
                    placeholders['entity.id_primary_number'] = passport_num

                if sensitive.passport_country:
                    placeholders['passport_country'] = sensitive.passport_country
                    placeholders['entity.passport_country'] = sensitive.passport_country
                    placeholders['entity.id_country'] = sensitive.passport_country

                # Empty for passport (ID-specific)
                placeholders['entity.id_series_number'] = ''

                # Level 3: Complete phrase placeholders for Passport
                parts = []
                if sensitive._passport_number_encrypted:
                    parts.append(f"Pașaport nr. {sensitive.passport_number}")
                if sensitive.passport_country:
                    parts.append(f"emis de {sensitive.passport_country}")

                if parts:
                    placeholders['entity.identification_short'] = ', '.join(parts)

                # Full identification with issued details
                full_parts = parts.copy()
                # Note: For passports, we don't include "eliberat de" since "emis de {country}" is sufficient
                if sensitive.id_issued_date:
                    full_parts.append(f"la data de {sensitive.id_issued_date}")
                if sensitive.id_expiry_date:
                    full_parts.append(f"valabil până la {sensitive.id_expiry_date}")

                if full_parts:
                    placeholders['entity.identification_full'] = ', '.join(full_parts)

            # Shared fields (both ID card and passport)
            if sensitive.id_issued_by:
                placeholders['id_issued_by'] = sensitive.id_issued_by
                placeholders['id.issued_by'] = sensitive.id_issued_by
            if sensitive.id_issued_date:
                placeholders['id_issued_date'] = str(sensitive.id_issued_date)
                placeholders['id.issued_date'] = str(sensitive.id_issued_date)
            if sensitive.id_expiry_date:
                placeholders['id_expiry_date'] = str(sensitive.id_expiry_date)
                placeholders['id.expiry_date'] = str(sensitive.id_expiry_date)
            if sensitive.date_of_birth:
                placeholders['entity.date_of_birth'] = str(sensitive.date_of_birth)
            if sensitive.place_of_birth:
                placeholders['entity.place_of_birth'] = sensitive.place_of_birth

        return placeholders

    @property
    def roles(self):
        """Get list of creative roles for this entity."""
        return list(self.entity_roles.values_list('role', flat=True))

    @property
    def is_artist(self):
        return self.entity_roles.filter(role='artist').exists()

    @property
    def is_producer(self):
        return self.entity_roles.filter(role='producer').exists()

    @property
    def is_composer(self):
        return self.entity_roles.filter(role='composer').exists()

    @property
    def is_lyricist(self):
        return self.entity_roles.filter(role='lyricist').exists()


class EntityRole(models.Model):
    """
    Defines creative roles for entities.
    An entity can have multiple roles (e.g., artist and producer).
    """

    # Creative roles
    CREATIVE_ROLE_CHOICES = [
        ('artist', 'Artist'),
        ('producer', 'Producer'),
        ('composer', 'Composer'),
        ('lyricist', 'Lyricist'),
        ('audio_editor', 'Audio Editor'),
    ]

    # Business roles
    BUSINESS_ROLE_CHOICES = [
        ('client', 'Client'),
        ('brand', 'Brand'),
        ('label', 'Label'),
        ('booking', 'Booking'),
        ('endorsements', 'Endorsements'),
        ('publishing', 'Publishing'),
        ('productie', 'Productie'),
        ('new_business', 'New Business'),
        ('digital', 'Digital'),
    ]

    ROLE_CHOICES = CREATIVE_ROLE_CHOICES + BUSINESS_ROLE_CHOICES

    entity = models.ForeignKey(
        Entity,
        on_delete=models.CASCADE,
        related_name='entity_roles'
    )

    role = models.CharField(
        max_length=50,
        choices=ROLE_CHOICES,
        db_index=True
    )

    # Optional metadata
    primary_role = models.BooleanField(
        default=False,
        help_text="Is this the primary role for this entity?"
    )

    is_internal = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Is this a signed artist/internal role or external contractor?"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['entity', 'role']
        ordering = ['-primary_role', 'role']
        indexes = [
            models.Index(fields=['role']),
        ]

    def __str__(self):
        return f"{self.entity.display_name} - {self.get_role_display()}"


class SensitiveIdentity(models.Model):
    """
    Stores sensitive identity information for Physical Persons (PF only).
    Data is encrypted at rest and access is audited.
    Supports both Romanian ID cards and passports.
    """

    IDENTIFICATION_TYPE_CHOICES = [
        ('ID_CARD', 'Romanian ID Card'),
        ('PASSPORT', 'Passport'),
    ]

    entity = models.OneToOneField(
        Entity,
        on_delete=models.CASCADE,
        related_name='sensitive_identity'
    )

    # Identification type selector
    identification_type = models.CharField(
        max_length=20,
        choices=IDENTIFICATION_TYPE_CHOICES,
        default='ID_CARD',
        help_text="Type of identification document"
    )

    # --- ID CARD FIELDS ---
    # Encrypted CNP (Romanian Personal Numeric Code) - Required for ID cards
    _cnp_encrypted = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Encrypted CNP (for ID card)"
    )

    id_series = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="ID card series (e.g., 'RT')"
    )

    id_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="ID card number"
    )

    # --- PASSPORT FIELDS ---
    # Encrypted passport number
    _passport_number_encrypted = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Encrypted passport number"
    )

    passport_country = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Country of passport issuance"
    )

    # --- SHARED FIELDS (both ID card and passport) ---
    # Personal information
    date_of_birth = models.DateField(
        blank=True,
        null=True
    )

    place_of_birth = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    id_issued_by = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Issuing authority"
    )

    id_issued_date = models.DateField(
        blank=True,
        null=True
    )

    id_expiry_date = models.DateField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Sensitive Identity"
        verbose_name_plural = "Sensitive Identities"
        # Custom Django permission used to authorize sensitive data reveal
        # via view-level permission checks. This enables future roles/departments
        # (e.g., legal_manager, finance_manager) to be granted this capability
        # without code changes — simply assign the permission to their groups.
        permissions = [
            ("reveal_sensitive_identity", "Can reveal sensitive identity information"),
        ]


# NOTE: The SensitiveAccessPolicy model is defined at module end to avoid
# interfering with the SensitiveIdentity class body below.

    def clean(self):
        """Validate that entity is PF and required fields based on identification type."""
        if self.entity.kind != 'PF':
            raise ValidationError("Sensitive identity can only be created for Physical Persons (PF)")

        # Validate ID card fields
        if self.identification_type == 'ID_CARD':
            if not self._cnp_encrypted:
                raise ValidationError("CNP is required for ID card identification")
            if not self.id_series:
                raise ValidationError("ID series is required for ID card identification")
            if not self.id_number:
                raise ValidationError("ID number is required for ID card identification")

        # Validate passport fields
        elif self.identification_type == 'PASSPORT':
            if not self._passport_number_encrypted:
                raise ValidationError("Passport number is required for passport identification")
            if not self.passport_country:
                raise ValidationError("Passport country is required for passport identification")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    @property
    def cnp(self):
        """Get decrypted CNP (requires audit log)."""
        if not self._cnp_encrypted:
            return None
        # This should be called only through the reveal API with audit logging
        try:
            return self._decrypt_field(self._cnp_encrypted)
        except Exception as e:
            # If decryption fails, the data was encrypted with a different key
            # This can happen if the encryption key was changed
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to decrypt CNP for entity {self.entity_id}: {str(e)}")
            return None

    @cnp.setter
    def cnp(self, value):
        """Set encrypted CNP and auto-extract date of birth."""
        if value:
            self._cnp_encrypted = self._encrypt_field(value)
            # Auto-extract date of birth from CNP
            dob = self._extract_dob_from_cnp(value)
            if dob:
                self.date_of_birth = dob
        else:
            self._cnp_encrypted = None

    def _extract_dob_from_cnp(self, cnp_value):
        """
        Extract date of birth from Romanian CNP.
        CNP format: SAALLZZJJNNNC
        S = sex/century (1/2=1900s, 3/4=1800s, 5/6=2000s, 7/8=residents, 9=foreigners)
        AA = year, LL = month, ZZ = day
        """
        if not cnp_value or len(cnp_value) != 13:
            return None

        try:
            # Extract components
            sex_century = int(cnp_value[0])
            year = int(cnp_value[1:3])
            month = int(cnp_value[3:5])
            day = int(cnp_value[5:7])

            # Determine century based on first digit
            if sex_century in [1, 2]:
                century = 1900
            elif sex_century in [3, 4]:
                century = 1800
            elif sex_century in [5, 6]:
                century = 2000
            elif sex_century in [7, 8]:
                # Residents - assume 1900s or 2000s based on year
                century = 1900 if year > 30 else 2000
            elif sex_century == 9:
                # Foreigners - assume 1900s or 2000s based on year
                century = 1900 if year > 30 else 2000
            else:
                return None

            full_year = century + year

            # Validate month and day
            if month < 1 or month > 12:
                return None
            if day < 1 or day > 31:
                return None

            from datetime import date
            return date(full_year, month, day)

        except (ValueError, IndexError):
            return None

    @property
    def passport_number(self):
        """Get decrypted passport number (requires audit log)."""
        if not self._passport_number_encrypted:
            return None
        # This should be called only through the reveal API with audit logging
        try:
            return self._decrypt_field(self._passport_number_encrypted)
        except Exception as e:
            # If decryption fails, the data was encrypted with a different key
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to decrypt passport number for entity {self.entity_id}: {str(e)}")
            return None

    @passport_number.setter
    def passport_number(self, value):
        """Set encrypted passport number."""
        if value:
            self._passport_number_encrypted = self._encrypt_field(value)
        else:
            self._passport_number_encrypted = None

    def _get_encryption_key(self):
        """Get encryption key from settings."""
        key = getattr(settings, 'FIELD_ENCRYPTION_KEY', None)
        if not key:
            raise ValueError(
                "FIELD_ENCRYPTION_KEY not configured in settings. "
                "Please set this in your .env file. "
                "Generate a key with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        return key

    def _encrypt_field(self, value):
        """Encrypt a field value."""
        if not value:
            return None
        f = Fernet(self._get_encryption_key())
        return f.encrypt(value.encode()).decode()

    def _decrypt_field(self, encrypted_value):
        """Decrypt a field value."""
        if not encrypted_value:
            return None
        f = Fernet(self._get_encryption_key())
        return f.decrypt(encrypted_value.encode()).decode()

    def get_masked_cnp(self):
        """Return masked CNP for display."""
        if not self._cnp_encrypted:
            return None
        return "***-***-***"

    def get_masked_passport_number(self):
        """Return masked passport number for display."""
        if not self._passport_number_encrypted:
            return None
        return "********"


class Identifier(models.Model):
    """
    Central registry for various identification codes.
    Supports ISRC, ISWC, UPC, CUI, VAT, IBAN, etc.
    """

    OWNER_TYPE_CHOICES = [
        ('entity', 'Entity'),
        ('work', 'Work'),
        ('recording', 'Recording'),
        ('release', 'Release'),
    ]

    SCHEME_CHOICES = [
        # Music industry codes
        ('ISRC', 'International Standard Recording Code'),
        ('ISWC', 'International Standard Musical Work Code'),
        ('UPC', 'Universal Product Code'),
        ('EAN', 'European Article Number'),

        # Entity identifiers
        ('CUI', 'Unique Registration Code (Romania)'),
        ('VAT', 'VAT Number'),
        ('IBAN', 'International Bank Account Number'),
        ('BIC', 'Bank Identifier Code'),
        ('SSN', 'Social Security Number'),
        ('EIN', 'Employer Identification Number'),

        # PRO identifiers
        ('IPI', 'Interested Party Information'),
        ('CAE', 'Composer, Author and Publisher Number'),

        # Platform identifiers
        ('SPOTIFY_URI', 'Spotify URI'),
        ('APPLE_ID', 'Apple Music ID'),
        ('YOUTUBE_ID', 'YouTube ID'),
    ]

    owner_type = models.CharField(
        max_length=20,
        choices=OWNER_TYPE_CHOICES,
        db_index=True
    )

    owner_id = models.BigIntegerField(
        db_index=True,
        help_text="ID of the owner object"
    )

    scheme = models.CharField(
        max_length=20,
        choices=SCHEME_CHOICES,
        db_index=True
    )

    value = models.CharField(
        max_length=100,
        db_index=True,
        help_text="The identifier value"
    )

    # Flag for sensitive identifiers (like SSN)
    pii_flag = models.BooleanField(
        default=False,
        help_text="Contains personally identifiable information"
    )

    # Optional metadata
    issued_by = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Organization that issued this identifier"
    )

    issued_date = models.DateField(
        blank=True,
        null=True
    )

    expiry_date = models.DateField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['scheme', 'value']
        indexes = [
            models.Index(fields=['owner_type', 'owner_id', 'scheme']),
            models.Index(fields=['scheme', 'value']),
            models.Index(fields=['value']),
        ]
        ordering = ['scheme', 'value']

    def __str__(self):
        return f"{self.scheme}: {self.value}"

    def clean(self):
        """Validate identifier format based on scheme."""
        if self.scheme == 'ISRC':
            # ISRC format: CC-XXX-YY-NNNNN
            if not self.value or len(self.value) != 12:
                raise ValidationError("ISRC must be 12 characters")
        elif self.scheme == 'ISWC':
            # ISWC format: T-NNNNNNNNN-C
            if not self.value or not self.value.startswith('T-'):
                raise ValidationError("ISWC must start with 'T-'")
        elif self.scheme == 'UPC':
            # UPC is 12 digits
            if not self.value or not self.value.isdigit() or len(self.value) != 12:
                raise ValidationError("UPC must be 12 digits")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class AuditLogSensitive(models.Model):
    """
    Audit log for sensitive data access.
    Tracks who accessed sensitive information and when.
    """

    FIELD_CHOICES = [
        ('cnp', 'CNP'),
        ('passport_number', 'Passport Number'),
        ('ssn', 'SSN'),
        ('id_card', 'ID Card Details'),
        ('bank_account', 'Bank Account'),
    ]

    ACTION_CHOICES = [
        ('view', 'View'),
        ('export', 'Export'),
        ('update', 'Update'),
    ]

    # What was accessed
    entity = models.ForeignKey(
        Entity,
        on_delete=models.CASCADE,
        related_name='sensitive_audits'
    )

    field = models.CharField(
        max_length=20,
        choices=FIELD_CHOICES
    )

    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        default='view'
    )

    # Who accessed it
    viewer_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sensitive_data_views'
    )

    # Why it was accessed
    reason = models.TextField(
        help_text="Reason for accessing sensitive data"
    )

    # Context
    viewed_at = models.DateTimeField(auto_now_add=True)

    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True
    )

    user_agent = models.TextField(
        blank=True,
        null=True
    )

    # Session tracking
    session_key = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    class Meta:
        ordering = ['-viewed_at']
        indexes = [
            models.Index(fields=['entity', 'viewed_at']),
            models.Index(fields=['viewer_user', 'viewed_at']),
            models.Index(fields=['field', 'action']),
        ]
        verbose_name = "Sensitive Data Audit Log"
        verbose_name_plural = "Sensitive Data Audit Logs"

    def __str__(self):
        return f"{self.viewer_user} accessed {self.entity}'s {self.field} at {self.viewed_at}"


class SocialMediaAccount(models.Model):
    """
    Social media accounts for entities.
    An entity can have multiple accounts per platform.
    """

    PLATFORM_CHOICES = [
        ('instagram', 'Instagram'),
        ('tiktok', 'TikTok'),
        ('youtube', 'YouTube'),
        ('facebook', 'Facebook'),
        ('twitter', 'Twitter/X'),
        ('spotify', 'Spotify'),
        ('apple_music', 'Apple Music'),
        ('soundcloud', 'SoundCloud'),
        ('bandcamp', 'Bandcamp'),
        ('linkedin', 'LinkedIn'),
        ('website', 'Website'),
        ('other', 'Other'),
    ]

    entity = models.ForeignKey(
        Entity,
        on_delete=models.CASCADE,
        related_name='social_media_accounts'
    )

    platform = models.CharField(
        max_length=50,
        choices=PLATFORM_CHOICES,
        db_index=True,
        help_text="Social media platform"
    )

    handle = models.CharField(
        max_length=255,
        blank=True,
        help_text="Username/handle (without @ symbol)"
    )

    url = models.URLField(
        max_length=500,
        help_text="Full URL to the profile/page"
    )

    display_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Display name on the platform"
    )

    follower_count = models.IntegerField(
        blank=True,
        null=True,
        help_text="Number of followers/subscribers (optional)"
    )

    is_verified = models.BooleanField(
        default=False,
        help_text="Is this account verified on the platform?"
    )

    is_primary = models.BooleanField(
        default=False,
        help_text="Is this the primary account for this platform?"
    )

    notes = models.TextField(
        blank=True,
        help_text="Additional notes about this account"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['platform', '-is_primary', '-follower_count']
        indexes = [
            models.Index(fields=['entity', 'platform']),
            models.Index(fields=['platform', 'is_primary']),
        ]
        verbose_name = "Social Media Account"
        verbose_name_plural = "Social Media Accounts"

    def __str__(self):
        if self.handle:
            return f"{self.entity.display_name} - {self.get_platform_display()} (@{self.handle})"
        return f"{self.entity.display_name} - {self.get_platform_display()}"

    def get_platform_icon(self):
        """Return platform-specific icon class or emoji"""
        icons = {
            'instagram': '📷',
            'tiktok': '🎵',
            'youtube': '▶️',
            'facebook': '👤',
            'twitter': '🐦',
            'spotify': '🎧',
            'apple_music': '🍎',
            'soundcloud': '☁️',
            'bandcamp': '🎸',
            'linkedin': '💼',
            'website': '🌐',
            'other': '🔗',
        }
        return icons.get(self.platform, '🔗')


class ContactPerson(models.Model):
    """
    Contact persons associated with an entity.
    Used for tracking relationships with individuals at client/brand organizations.
    """

    ROLE_CHOICES = [
        ('marketing', 'Marketing / Growth'),
        ('pr', 'PR / Publicist / Press'),
        ('playlist_curator', 'Playlist curator / DSP editor'),
        ('radio', 'Radio DJ / Programmer'),
        ('a&r', 'A&R'),
        ('manager', 'Artist manager'),
        ('booking_agent', 'Booking agent / Agent'),
        ('venue', 'Venue / Booker'),
        ('promoter', 'Promoter / Event promoter'),
        ('distributor', 'Distributor / DSP aggregator'),
        ('publisher', 'Publisher / Sync rights'),
        ('sync_supervisor', 'Sync / Music supervisor (film/TV/ads)'),
        ('producer', 'Producer / Beatmaker'),
        ('songwriter', 'Songwriter / Composer / Lyricist'),
        ('engineer', 'Recording / Mixing / Mastering engineer'),
        ('photographer', 'Photographer / Videographer'),
        ('designer', 'Graphic / Artwork designer'),
        ('brand', 'Brand / Sponsor / Partnership rep'),
        ('influencer', 'Influencer / Creator / KOL'),
        ('retailer', 'Retail / Merch / Store contact'),
        ('legal', 'Lawyer / Contracts / Rights'),
        ('finance', 'Accountant / Finance / Royalty admin'),
        ('operations', 'Ops / Logistics / Warehouse / Supplier'),
        ('admin', 'Admin / Coordinator / Personal assistant'),
        ('fan', 'Fan / Superfan (direct-to-fan ops)'),
        ('other', 'Other / Misc'),
    ]

    ENGAGEMENT_STAGE_CHOICES = [
        ('lead', 'Lead (new, unqualified)'),
        ('prospect', 'Prospect (in talks / negotiating)'),
        ('active', 'Active (current project / engagement)'),
        ('partner', 'Partner (formal long-term partner)'),
        ('dormant', 'Dormant (no recent activity)'),
        ('lost', 'Lost (opportunity lost)'),
        ('blacklisted', 'Blacklisted / Do not contact'),
    ]

    SENTIMENT_CHOICES = [
        ('advocate', 'Advocate / Champion (promotes you)'),
        ('supportive', 'Supportive / Helpful'),
        ('approachable', 'Approachable (easy to reach)'),
        ('friendly', 'Friendly / Warm'),
        ('professional', 'Professional / Neutral-positive'),
        ('neutral', 'Neutral / No strong feeling'),
        ('reserved', 'Reserved / Polite but distant'),
        ('distant', 'Distant / Low engagement'),
        ('awkward', 'Awkward / Tricky rapport'),
        ('friction', 'Friction / Frequent disagreements'),
        ('hostile', 'Hostile / Negative'),
        ('blocked', 'Blocked / Legal / Do not contact'),
    ]

    entity = models.ForeignKey(
        Entity,
        on_delete=models.CASCADE,
        related_name='contact_persons'
    )

    name = models.CharField(
        max_length=255,
        help_text="Full name of the contact person"
    )

    role = models.CharField(
        max_length=50,
        choices=ROLE_CHOICES,
        blank=True,
        null=True,
        help_text="Business role of the contact person"
    )

    engagement_stage = models.CharField(
        max_length=50,
        choices=ENGAGEMENT_STAGE_CHOICES,
        blank=True,
        null=True,
        help_text="Current engagement stage in relationship"
    )

    sentiment = models.CharField(
        max_length=50,
        choices=SENTIMENT_CHOICES,
        blank=True,
        null=True,
        help_text="Relationship sentiment / attitude"
    )

    notes = models.TextField(
        blank=True,
        help_text="Additional notes about this contact"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['entity', 'name']),
            models.Index(fields=['role']),
            models.Index(fields=['engagement_stage']),
        ]
        verbose_name = "Contact Person"
        verbose_name_plural = "Contact Persons"

    def __str__(self):
        return f"{self.name} ({self.entity.display_name})"


class ContactEmail(models.Model):
    """
    Email addresses for contact persons.
    A contact person can have multiple email addresses.
    """

    contact_person = models.ForeignKey(
        ContactPerson,
        on_delete=models.CASCADE,
        related_name='emails'
    )

    email = models.EmailField(
        help_text="Email address"
    )

    label = models.CharField(
        max_length=50,
        blank=True,
        help_text="Label for this email (e.g., 'work', 'personal')"
    )

    is_primary = models.BooleanField(
        default=False,
        help_text="Is this the primary email?"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_primary', 'email']
        indexes = [
            models.Index(fields=['contact_person', 'is_primary']),
            models.Index(fields=['email']),
        ]
        verbose_name = "Contact Email"
        verbose_name_plural = "Contact Emails"

    def __str__(self):
        return self.email


class ContactPhone(models.Model):
    """
    Phone numbers for contact persons.
    A contact person can have multiple phone numbers.
    """

    contact_person = models.ForeignKey(
        ContactPerson,
        on_delete=models.CASCADE,
        related_name='phones'
    )

    phone = models.CharField(
        max_length=50,
        help_text="Phone number"
    )

    label = models.CharField(
        max_length=50,
        blank=True,
        help_text="Label for this phone (e.g., 'mobile', 'office', 'direct')"
    )

    is_primary = models.BooleanField(
        default=False,
        help_text="Is this the primary phone?"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_primary', 'phone']
        indexes = [
            models.Index(fields=['contact_person', 'is_primary']),
        ]
        verbose_name = "Contact Phone"
        verbose_name_plural = "Contact Phones"

    def __str__(self):
        return self.phone


class ClientProfile(models.Model):
    """
    Department-specific client health and reliability profile.
    Each department maintains their own view of client health.
    Based on collaboration frequency, feedback quality, and payment latency.
    """

    entity = models.ForeignKey(
        Entity,
        on_delete=models.CASCADE,
        related_name='client_profiles',
        help_text="The client entity this profile belongs to"
    )

    department = models.ForeignKey(
        'api.Department',
        on_delete=models.CASCADE,
        related_name='client_profiles',
        help_text="The department this profile belongs to"
    )

    # Overall health score (1-10)
    health_score = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        db_index=True,
        help_text="Overall client health score (1-10). Can be manually set or auto-calculated."
    )

    # Component scores (1-10) - for future auto-calculation
    collaboration_frequency_score = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Score based on how often we work with this client (1-10)"
    )

    feedback_score = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Score based on client feedback quality and responsiveness (1-10)"
    )

    payment_latency_score = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Score based on payment timeliness (1-10, 10=always on time)"
    )

    # Context and notes
    notes = models.TextField(
        blank=True,
        help_text="Notes about this client's health score and reliability"
    )

    # Tracking
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='client_profiles_updated',
        help_text="Last user who updated this profile"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['entity', 'department']
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['entity', 'department']),
            models.Index(fields=['department', 'health_score']),
            models.Index(fields=['health_score']),
        ]
        verbose_name = "Client Profile"
        verbose_name_plural = "Client Profiles"

    def __str__(self):
        score_text = f"{self.health_score}/10" if self.health_score else "No score"
        return f"{self.entity.display_name} - {self.department.name} ({score_text})"

    def get_score_trend(self):
        """
        Calculate score trend based on recent history.
        Returns: 'up', 'down', or 'stable'
        """
        history = self.history.order_by('-changed_at')[:2]
        if len(history) < 2:
            return 'stable'

        current = history[0].health_score or 0
        previous = history[1].health_score or 0

        if current > previous:
            return 'up'
        elif current < previous:
            return 'down'
        return 'stable'

    def save(self, *args, **kwargs):
        """Override save to create history entry on changes."""
        # Check if this is an update (not a new record)
        is_update = self.pk is not None

        if is_update:
            # Get the old values before saving
            try:
                old_instance = ClientProfile.objects.get(pk=self.pk)
                # Check if any score changed
                if (old_instance.health_score != self.health_score or
                    old_instance.collaboration_frequency_score != self.collaboration_frequency_score or
                    old_instance.feedback_score != self.feedback_score or
                    old_instance.payment_latency_score != self.payment_latency_score or
                    old_instance.notes != self.notes):

                    # Save first to get updated values
                    super().save(*args, **kwargs)

                    # Create history entry
                    ClientProfileHistory.objects.create(
                        client_profile=self,
                        health_score=self.health_score,
                        collaboration_frequency_score=self.collaboration_frequency_score,
                        feedback_score=self.feedback_score,
                        payment_latency_score=self.payment_latency_score,
                        notes=self.notes,
                        changed_by=self.updated_by
                    )
                    return
            except ClientProfile.DoesNotExist:
                pass

        # Normal save
        super().save(*args, **kwargs)


class ClientProfileHistory(models.Model):
    """
    History of changes to client profiles.
    Tracks all modifications to see improvements or degradations in client relationships.
    """

    client_profile = models.ForeignKey(
        ClientProfile,
        on_delete=models.CASCADE,
        related_name='history',
        help_text="The client profile this history entry belongs to"
    )

    # Score snapshots at this point in time
    health_score = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Health score at this point in time"
    )

    collaboration_frequency_score = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Collaboration frequency score at this point in time"
    )

    feedback_score = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Feedback score at this point in time"
    )

    payment_latency_score = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Payment latency score at this point in time"
    )

    notes = models.TextField(
        blank=True,
        help_text="Notes at this point in time"
    )

    # Who made this change
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='client_profile_changes',
        help_text="User who made this change"
    )

    # Optional: reason for change
    change_reason = models.TextField(
        blank=True,
        help_text="Optional reason for this change"
    )

    changed_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-changed_at']
        indexes = [
            models.Index(fields=['client_profile', '-changed_at']),
            models.Index(fields=['changed_by', '-changed_at']),
        ]
        verbose_name = "Client Profile History"
        verbose_name_plural = "Client Profile Histories"

    def __str__(self):
        score_text = f"{self.health_score}/10" if self.health_score else "No score"
        return f"{self.client_profile.entity.display_name} - {score_text} at {self.changed_at}"

    def get_score_change(self):
        """
        Calculate the score change from the previous history entry.
        Returns: positive/negative integer or None
        """
        previous = ClientProfileHistory.objects.filter(
            client_profile=self.client_profile,
            changed_at__lt=self.changed_at
        ).order_by('-changed_at').first()

        if not previous or not previous.health_score or not self.health_score:
            return None

        return self.health_score - previous.health_score
