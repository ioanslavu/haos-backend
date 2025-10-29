"""
Tests for ShareType and ContractShare models and API endpoints.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta

from contracts.models import (
    ShareType, ContractShare, Contract, ContractTemplate
)
from identity.models import Entity

User = get_user_model()


class ShareTypeModelTest(TestCase):
    """Tests for the ShareType model."""

    def setUp(self):
        """Set up test data."""
        self.share_type, _ = ShareType.objects.get_or_create(
            code='concert_commission',
            defaults={
                'name': 'Concert Commission',
                'description': 'Commission from concerts',
                'placeholder_keys': ['commission.year_{year}.concerts', 'concert_commission'],
                'contract_types': ['artist_master']
            }
        )

    def test_share_type_creation(self):
        """Test creating a share type."""
        self.assertEqual(self.share_type.code, 'concert_commission')
        self.assertEqual(self.share_type.name, 'Concert Commission')
        self.assertEqual(len(self.share_type.placeholder_keys), 2)
        self.assertIn('artist_master', self.share_type.contract_types)

    def test_share_type_str(self):
        """Test share type string representation."""
        expected = f"{self.share_type.code} - {self.share_type.name}"
        self.assertEqual(str(self.share_type), expected)

    def test_share_type_ordering(self):
        """Test that share types are ordered by code."""
        ShareType.objects.get_or_create(
            code='master_share',
            defaults={
                'name': 'Master Share',
                'placeholder_keys': ['master_share']
            }
        )
        ShareType.objects.get_or_create(
            code='writer_share',
            defaults={
                'name': 'Writer Share',
                'placeholder_keys': ['writer_share']
            }
        )

        share_types = list(ShareType.objects.all())
        # Test that ordering is by code (alphabetical)
        codes = [st.code for st in share_types]
        self.assertEqual(codes, sorted(codes))

        # Verify some expected share types exist
        self.assertIn('concert_commission', codes)
        self.assertIn('master_share', codes)
        self.assertIn('writer_share', codes)


class ContractShareModelTest(TestCase):
    """Tests for the ContractShare model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        self.entity = Entity.objects.create(
            kind='PF',
            display_name='Test Artist',
            email='artist@example.com'
        )

        self.template = ContractTemplate.objects.create(
            name='Test Template',
            gdrive_template_file_id='test123',
            gdrive_output_folder_id='folder123',
            created_by=self.user
        )

        self.contract = Contract.objects.create(
            template=self.template,
            contract_number='CNT-TEST-001',
            title='Test Contract',
            counterparty_entity=self.entity,
            term_start=date.today(),
            created_by=self.user
        )

        self.share_type, _ = ShareType.objects.get_or_create(
            code='concert_commission',
            defaults={
                'name': 'Concert Commission',
                'placeholder_keys': ['commission.year_{year}.concerts']
            }
        )

    def test_contract_share_creation(self):
        """Test creating a contract share."""
        share = ContractShare.objects.create(
            contract=self.contract,
            share_type=self.share_type,
            value=Decimal('15.0000'),
            unit='percent',
            valid_from=date.today()
        )

        self.assertEqual(share.contract, self.contract)
        self.assertEqual(share.share_type, self.share_type)
        self.assertEqual(share.value, Decimal('15.0000'))
        self.assertEqual(share.unit, 'percent')

    def test_contract_share_str(self):
        """Test contract share string representation."""
        share = ContractShare.objects.create(
            contract=self.contract,
            share_type=self.share_type,
            value=Decimal('15.0000'),
            unit='percent',
            valid_from=date.today()
        )

        expected = f"{self.contract.contract_number} - {self.share_type.code}: {share.value}{share.unit}"
        self.assertEqual(str(share), expected)

    def test_get_placeholder_values_with_year(self):
        """Test generating placeholder values with year calculation."""
        share = ContractShare.objects.create(
            contract=self.contract,
            share_type=self.share_type,
            value=Decimal('15.0000'),
            unit='percent',
            valid_from=date.today()
        )

        placeholders = share.get_placeholder_values()

        # Should have placeholders for year 1 (since valid_from == contract.term_start)
        self.assertIn('commission.year_1.concerts', placeholders)
        self.assertEqual(placeholders['commission.year_1.concerts'], '15.0000')

    def test_get_placeholder_values_without_year(self):
        """Test generating placeholder values without year placeholder."""
        share_type_no_year, _ = ShareType.objects.get_or_create(
            code='master_share',
            defaults={
                'name': 'Master Share',
                'placeholder_keys': ['master_share', 'artist.master_share']
            }
        )

        share = ContractShare.objects.create(
            contract=self.contract,
            share_type=share_type_no_year,
            value=Decimal('70.0000'),
            unit='percent',
            valid_from=date.today()
        )

        placeholders = share.get_placeholder_values()

        self.assertIn('master_share', placeholders)
        self.assertIn('artist.master_share', placeholders)
        self.assertEqual(placeholders['master_share'], '70.0000')

    def test_calculate_year(self):
        """Test year calculation from valid_from date."""
        # Year 1: valid_from == term_start
        share_year_1 = ContractShare.objects.create(
            contract=self.contract,
            share_type=self.share_type,
            value=Decimal('10.0000'),
            unit='percent',
            valid_from=self.contract.term_start
        )
        self.assertEqual(share_year_1._calculate_year(), 1)

        # Year 2: valid_from = term_start + 365 days
        share_type_year2, _ = ShareType.objects.get_or_create(
            code='test_year2',
            defaults={
                'name': 'Test Year 2',
                'placeholder_keys': ['test.year_{year}']
            }
        )
        share_year_2 = ContractShare.objects.create(
            contract=self.contract,
            share_type=share_type_year2,
            value=Decimal('15.0000'),
            unit='percent',
            valid_from=self.contract.term_start + timedelta(days=365)
        )
        self.assertEqual(share_year_2._calculate_year(), 2)

    def test_different_units(self):
        """Test creating shares with different units."""
        # Percent
        share_percent = ContractShare.objects.create(
            contract=self.contract,
            share_type=self.share_type,
            value=Decimal('15.0000'),
            unit='percent',
            valid_from=date.today()
        )
        self.assertEqual(share_percent.unit, 'percent')

        # Points
        share_type_points, _ = ShareType.objects.get_or_create(
            code='producer_points',
            defaults={
                'name': 'Producer Points',
                'placeholder_keys': ['producer.points']
            }
        )
        share_points = ContractShare.objects.create(
            contract=self.contract,
            share_type=share_type_points,
            value=Decimal('3.0000'),
            unit='points',
            valid_from=date.today()
        )
        self.assertEqual(share_points.unit, 'points')

        # Flat amount
        share_type_flat, _ = ShareType.objects.get_or_create(
            code='flat_fee',
            defaults={
                'name': 'Flat Fee',
                'placeholder_keys': ['flat_fee']
            }
        )
        share_flat = ContractShare.objects.create(
            contract=self.contract,
            share_type=share_type_flat,
            value=Decimal('5000.0000'),
            unit='flat',
            valid_from=date.today()
        )
        self.assertEqual(share_flat.unit, 'flat')

    def test_valid_to_open_ended(self):
        """Test that valid_to can be null for open-ended shares."""
        share = ContractShare.objects.create(
            contract=self.contract,
            share_type=self.share_type,
            value=Decimal('15.0000'),
            unit='percent',
            valid_from=date.today(),
            valid_to=None  # Open-ended
        )

        self.assertIsNone(share.valid_to)

    def test_valid_to_with_end_date(self):
        """Test shares with explicit end dates."""
        share = ContractShare.objects.create(
            contract=self.contract,
            share_type=self.share_type,
            value=Decimal('15.0000'),
            unit='percent',
            valid_from=date.today(),
            valid_to=date.today() + timedelta(days=365)
        )

        self.assertIsNotNone(share.valid_to)
        self.assertEqual(share.valid_to, date.today() + timedelta(days=365))
