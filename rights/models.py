from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal
from identity.models import Entity
from catalog.models import Work, Recording


class Credit(models.Model):
    """
    Represents a contribution to a Work or Recording.
    Tracks who contributed and in what role, with optional share information.
    """

    SCOPE_CHOICES = [
        ('work', 'Work'),
        ('recording', 'Recording'),
    ]

    # Role choices based on scope
    WORK_ROLE_CHOICES = [
        ('composer', 'Composer'),
        ('lyricist', 'Lyricist'),
        ('arranger', 'Editor'),
    ]

    RECORDING_ROLE_CHOICES = [
        ('artist', 'Artist'),
        ('producer', 'Producer'),
        ('audio_editor', 'Editor'),
    ]

    # Combine all roles for the field (validation will check scope)
    ALL_ROLE_CHOICES = WORK_ROLE_CHOICES + RECORDING_ROLE_CHOICES

    SHARE_KIND_CHOICES = [
        ('none', 'No Share'),
        ('writer_share', 'Writer Share'),
        ('publisher_share', 'Publisher Share'),
        ('master_share', 'Master Share'),
        ('points', 'Producer Points'),
    ]

    # Scope
    scope = models.CharField(
        max_length=10,
        choices=SCOPE_CHOICES,
        db_index=True,
        help_text="Whether this credit is for a Work or Recording"
    )

    object_id = models.BigIntegerField(
        db_index=True,
        help_text="ID of the Work or Recording"
    )

    # Credit information
    entity = models.ForeignKey(
        Entity,
        on_delete=models.CASCADE,
        related_name='credits'
    )

    role = models.CharField(
        max_length=30,
        choices=ALL_ROLE_CHOICES,
        db_index=True,
        help_text="Role in the work/recording"
    )

    # Share information (optional)
    share_kind = models.CharField(
        max_length=20,
        choices=SHARE_KIND_CHOICES,
        default='none',
        help_text="Type of share/royalty"
    )

    share_value = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        help_text="Share percentage (0-100)"
    )

    # Additional information
    credited_as = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Name as credited (if different from entity name)"
    )

    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Additional notes about this credit"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['scope', 'object_id', 'entity', 'role']
        ordering = ['role', 'entity__display_name']
        indexes = [
            models.Index(fields=['scope', 'object_id', 'role']),
            models.Index(fields=['entity', 'role']),
        ]

    def __str__(self):
        return f"{self.entity.display_name} - {self.get_role_display()} on {self.scope} {self.object_id}"

    def clean(self):
        """Validate role based on scope."""
        work_roles = [r[0] for r in self.WORK_ROLE_CHOICES]
        recording_roles = [r[0] for r in self.RECORDING_ROLE_CHOICES]

        if self.scope == 'work' and self.role not in work_roles:
            raise ValidationError(f"Role '{self.role}' is not valid for Work credits")
        elif self.scope == 'recording' and self.role not in recording_roles:
            raise ValidationError(f"Role '{self.role}' is not valid for Recording credits")

        # Validate share_kind based on scope and role
        if self.share_kind != 'none' and self.share_value is None:
            raise ValidationError("Share value is required when share kind is specified")

        if self.scope == 'work':
            if self.share_kind == 'master_share' or self.share_kind == 'points':
                raise ValidationError("Master share and points are not valid for Work credits")
        elif self.scope == 'recording':
            if self.share_kind in ['writer_share', 'publisher_share']:
                raise ValidationError("Writer and publisher shares are not valid for Recording credits")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    @property
    def get_work(self):
        """Get the associated Work if scope is 'work'."""
        if self.scope == 'work':
            return Work.objects.filter(id=self.object_id).first()
        return None

    @property
    def get_recording(self):
        """Get the associated Recording if scope is 'recording'."""
        if self.scope == 'recording':
            return Recording.objects.filter(id=self.object_id).first()
        return None


class Split(models.Model):
    """
    Represents payment/royalty splits for Works and Recordings.
    Enforces 100% total validation for each split type.
    """

    SCOPE_CHOICES = [
        ('work', 'Work'),
        ('recording', 'Recording'),
    ]

    RIGHT_TYPE_CHOICES = [
        ('writer', 'Writer Share'),         # Work only
        ('publisher', 'Publisher Share'),   # Work only
        ('master', 'Master Share'),         # Recording only
    ]

    # Scope
    scope = models.CharField(
        max_length=10,
        choices=SCOPE_CHOICES,
        db_index=True,
        help_text="Whether this split is for a Work or Recording"
    )

    object_id = models.BigIntegerField(
        db_index=True,
        help_text="ID of the Work or Recording"
    )

    # Split information
    entity = models.ForeignKey(
        Entity,
        on_delete=models.CASCADE,
        related_name='splits'
    )

    right_type = models.CharField(
        max_length=20,
        choices=RIGHT_TYPE_CHOICES,
        db_index=True,
        help_text="Type of right/royalty"
    )

    share = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        help_text="Share percentage (0-100)"
    )

    # Source information (e.g., from contract)
    source = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Source of this split (e.g., 'Contract #123')"
    )

    # Additional fields
    is_locked = models.BooleanField(
        default=False,
        help_text="Prevent this split from being edited"
    )

    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Notes about this split"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['scope', 'object_id', 'entity', 'right_type']
        ordering = ['-share', 'entity__display_name']
        indexes = [
            models.Index(fields=['scope', 'object_id', 'right_type']),
            models.Index(fields=['entity', 'right_type']),
        ]

    def __str__(self):
        return f"{self.entity.display_name} - {self.share}% {self.get_right_type_display()}"

    def clean(self):
        """Validate right type based on scope and check total doesn't exceed 100%."""
        # Validate right_type based on scope
        if self.scope == 'work' and self.right_type == 'master':
            raise ValidationError("Master share is not valid for Work splits")
        elif self.scope == 'recording' and self.right_type in ['writer', 'publisher']:
            raise ValidationError("Writer and publisher shares are not valid for Recording splits")

        # Check if adding/updating this split would exceed 100%
        if self.pk:
            # Updating existing split
            existing_splits = Split.objects.filter(
                scope=self.scope,
                object_id=self.object_id,
                right_type=self.right_type
            ).exclude(pk=self.pk)
        else:
            # Creating new split
            existing_splits = Split.objects.filter(
                scope=self.scope,
                object_id=self.object_id,
                right_type=self.right_type
            )

        total_share = sum(s.share for s in existing_splits) + (self.share or Decimal('0'))

        if total_share > Decimal('100.01'):  # Allow 0.01 tolerance for rounding
            raise ValidationError(
                f"Total {self.get_right_type_display()} for this {self.scope} "
                f"would exceed 100% (total: {total_share:.2f}%)"
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    @property
    def get_work(self):
        """Get the associated Work if scope is 'work'."""
        if self.scope == 'work':
            return Work.objects.filter(id=self.object_id).first()
        return None

    @property
    def get_recording(self):
        """Get the associated Recording if scope is 'recording'."""
        if self.scope == 'recording':
            return Recording.objects.filter(id=self.object_id).first()
        return None

    @classmethod
    def validate_splits_total(cls, scope, object_id, right_type):
        """
        Validate that splits for a given scope/object/right_type total 100%.
        Returns a dictionary with validation results.
        """
        splits = cls.objects.filter(
            scope=scope,
            object_id=object_id,
            right_type=right_type
        )

        total = sum(s.share for s in splits)
        is_complete = abs(total - Decimal('100')) < Decimal('0.01')

        # For publishers, it's OK to have 0% (no publishers)
        if right_type == 'publisher' and total == Decimal('0'):
            is_complete = True

        return {
            'total': total,
            'is_complete': is_complete,
            'missing': Decimal('100') - total if not is_complete else Decimal('0'),
            'splits': list(splits.values('entity__display_name', 'share', 'source'))
        }

    @classmethod
    def auto_calculate_from_credits(cls, scope, object_id):
        """
        Auto-calculate splits based on Credits.
        This is a helper method to generate initial splits.
        """
        credits = Credit.objects.filter(scope=scope, object_id=object_id)

        if scope == 'work':
            # Calculate writer splits from composers/lyricists
            writer_credits = credits.filter(role__in=['composer', 'lyricist'])
            if writer_credits.exists():
                # Equal split among all writers if no share specified
                writer_count = writer_credits.count()
                equal_share = Decimal('100') / writer_count

                for credit in writer_credits:
                    split_share = credit.share_value if credit.share_value else equal_share
                    cls.objects.get_or_create(
                        scope=scope,
                        object_id=object_id,
                        entity=credit.entity,
                        right_type='writer',
                        defaults={'share': split_share}
                    )

            # Publisher splits from publisher credits
            publisher_credits = credits.filter(role='publisher')
            for credit in publisher_credits:
                if credit.share_value:
                    cls.objects.get_or_create(
                        scope=scope,
                        object_id=object_id,
                        entity=credit.entity,
                        right_type='publisher',
                        defaults={'share': credit.share_value}
                    )

        elif scope == 'recording':
            # Calculate master splits from artists and producers
            master_credits = credits.filter(role__in=['artist', 'producer'])

            # Default: artist gets majority, producer gets points
            artist_credits = credits.filter(role='artist')
            producer_credits = credits.filter(role='producer')

            # If we have both artists and producers
            if artist_credits.exists() and producer_credits.exists():
                # Producers get their points
                producer_total = sum(c.share_value for c in producer_credits if c.share_value) or Decimal('0')

                # Artists share the rest equally
                artist_total = Decimal('100') - producer_total
                artist_count = artist_credits.count()
                artist_share_each = artist_total / artist_count if artist_count > 0 else Decimal('0')

                for credit in artist_credits:
                    cls.objects.get_or_create(
                        scope=scope,
                        object_id=object_id,
                        entity=credit.entity,
                        right_type='master',
                        defaults={'share': artist_share_each}
                    )

                for credit in producer_credits:
                    if credit.share_value:
                        cls.objects.get_or_create(
                            scope=scope,
                            object_id=object_id,
                            entity=credit.entity,
                            right_type='master',
                            defaults={'share': credit.share_value}
                        )


class SplitValidation:
    """
    Utility class for validating split totals.
    Used by views and serializers to ensure data integrity.
    """

    @staticmethod
    def validate_work_splits(work_id):
        """Validate all splits for a Work."""
        results = {
            'work_id': work_id,
            'valid': True,
            'errors': [],
            'warnings': []
        }

        # Check writer splits (must equal 100%)
        writer_validation = Split.validate_splits_total('work', work_id, 'writer')
        if not writer_validation['is_complete']:
            results['valid'] = False
            results['errors'].append(
                f"Writer splits total {writer_validation['total']:.2f}%, "
                f"missing {writer_validation['missing']:.2f}%"
            )

        # Check publisher splits (must equal 100% if publishers exist)
        publisher_validation = Split.validate_splits_total('work', work_id, 'publisher')
        if publisher_validation['total'] > 0 and not publisher_validation['is_complete']:
            results['valid'] = False
            results['errors'].append(
                f"Publisher splits total {publisher_validation['total']:.2f}%, "
                f"missing {publisher_validation['missing']:.2f}%"
            )
        elif publisher_validation['total'] == 0:
            results['warnings'].append("No publisher splits defined")

        results['writer_splits'] = writer_validation
        results['publisher_splits'] = publisher_validation

        return results

    @staticmethod
    def validate_recording_splits(recording_id):
        """Validate all splits for a Recording."""
        results = {
            'recording_id': recording_id,
            'valid': True,
            'errors': [],
            'warnings': []
        }

        # Check master splits (must equal 100%)
        master_validation = Split.validate_splits_total('recording', recording_id, 'master')
        if not master_validation['is_complete']:
            results['valid'] = False
            results['errors'].append(
                f"Master splits total {master_validation['total']:.2f}%, "
                f"missing {master_validation['missing']:.2f}%"
            )

        results['master_splits'] = master_validation

        return results

    @staticmethod
    def bulk_validate(scope, object_ids):
        """Validate splits for multiple objects."""
        results = []

        for obj_id in object_ids:
            if scope == 'work':
                result = SplitValidation.validate_work_splits(obj_id)
            else:
                result = SplitValidation.validate_recording_splits(obj_id)
            results.append(result)

        return {
            'scope': scope,
            'total_objects': len(object_ids),
            'valid_count': sum(1 for r in results if r['valid']),
            'invalid_count': sum(1 for r in results if not r['valid']),
            'details': results
        }