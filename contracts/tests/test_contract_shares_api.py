"""
Tests for contract shares API endpoints.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal
from datetime import date, timedelta

from contracts.models import (
    ShareType, ContractShare, Contract, ContractTemplate
)
from identity.models import Entity

User = get_user_model()


class EntityLatestSharesAPITest(TestCase):
    """Tests for the /entities/{id}/latest_contract_shares/ API endpoint."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        # Create user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@hahahaproduction.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

        # Create entity
        self.entity = Entity.objects.create(
            kind='PF',
            display_name='Test Artist',
            email='artist@example.com'
        )

        # Create template
        self.template = ContractTemplate.objects.create(
            name='Artist Master Agreement',
            gdrive_template_file_id='test123',
            gdrive_output_folder_id='folder123',
            created_by=self.user
        )

        # Get or create share types (they're seeded in migration)
        self.concert_share_type, _ = ShareType.objects.get_or_create(
            code='concert_commission',
            defaults={
                'name': 'Concert Commission',
                'placeholder_keys': ['commission.year_{year}.concerts'],
                'contract_types': ['artist_master']
            }
        )

        self.rights_share_type, _ = ShareType.objects.get_or_create(
            code='rights_percentage',
            defaults={
                'name': 'Rights Percentage',
                'placeholder_keys': ['commission.year_{year}.rights'],
                'contract_types': ['artist_master']
            }
        )

        self.master_share_type, _ = ShareType.objects.get_or_create(
            code='master_share',
            defaults={
                'name': 'Master Share',
                'placeholder_keys': ['master_share'],
                'contract_types': ['artist_master', 'producer_service']
            }
        )

    def test_get_latest_shares_no_contracts(self):
        """Test API when entity has no contracts."""
        url = f'/api/v1/identity/entities/{self.entity.id}/latest_contract_shares/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['contract_id'])
        self.assertIsNone(response.data['contract_type'])
        self.assertEqual(response.data['shares'], [])

    def test_get_latest_shares_with_signed_contract(self):
        """Test API returns shares from latest signed contract."""
        # Create signed contract with shares
        contract = Contract.objects.create(
            template=self.template,
            contract_number='CNT-TEST-001',
            title='Test Artist Contract',
            contract_type='artist_master',
            counterparty_entity=self.entity,
            term_start=date.today(),
            status='signed',
            created_by=self.user
        )

        ContractShare.objects.create(
            contract=contract,
            share_type=self.concert_share_type,
            value=Decimal('10.0000'),
            unit='percent',
            valid_from=contract.term_start
        )

        ContractShare.objects.create(
            contract=contract,
            share_type=self.rights_share_type,
            value=Decimal('15.0000'),
            unit='percent',
            valid_from=contract.term_start
        )

        url = f'/api/v1/identity/entities/{self.entity.id}/latest_contract_shares/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['contract_id'], contract.id)
        self.assertEqual(response.data['contract_number'], 'CNT-TEST-001')
        self.assertEqual(response.data['contract_type'], 'artist_master')
        self.assertEqual(len(response.data['shares']), 2)

        # Verify share data
        shares = response.data['shares']
        concert_share = next(s for s in shares if s['share_type_code'] == 'concert_commission')
        self.assertEqual(concert_share['value'], '10.0000')
        self.assertEqual(concert_share['unit'], 'percent')

    def test_get_latest_shares_with_draft_contract(self):
        """Test API returns shares from draft contracts."""
        contract = Contract.objects.create(
            template=self.template,
            contract_number='CNT-TEST-002',
            title='Test Draft Contract',
            contract_type='artist_master',
            counterparty_entity=self.entity,
            term_start=date.today(),
            status='draft',
            created_by=self.user
        )

        ContractShare.objects.create(
            contract=contract,
            share_type=self.master_share_type,
            value=Decimal('70.0000'),
            unit='percent',
            valid_from=contract.term_start
        )

        url = f'/api/v1/identity/entities/{self.entity.id}/latest_contract_shares/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['contract_id'], contract.id)
        self.assertEqual(len(response.data['shares']), 1)

    def test_get_latest_shares_returns_most_recent(self):
        """Test API returns shares from the most recent contract."""
        # Create older contract
        old_contract = Contract.objects.create(
            template=self.template,
            contract_number='CNT-TEST-003',
            title='Old Contract',
            contract_type='artist_master',
            counterparty_entity=self.entity,
            term_start=date.today() - timedelta(days=365),
            status='signed',
            created_by=self.user
        )

        ContractShare.objects.create(
            contract=old_contract,
            share_type=self.concert_share_type,
            value=Decimal('5.0000'),
            unit='percent',
            valid_from=old_contract.term_start
        )

        # Create newer contract
        new_contract = Contract.objects.create(
            template=self.template,
            contract_number='CNT-TEST-004',
            title='New Contract',
            contract_type='artist_master',
            counterparty_entity=self.entity,
            term_start=date.today(),
            status='signed',
            created_by=self.user
        )

        ContractShare.objects.create(
            contract=new_contract,
            share_type=self.concert_share_type,
            value=Decimal('20.0000'),
            unit='percent',
            valid_from=new_contract.term_start
        )

        url = f'/api/v1/identity/entities/{self.entity.id}/latest_contract_shares/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['contract_id'], new_contract.id)
        self.assertEqual(response.data['contract_number'], 'CNT-TEST-004')

        # Should return new contract's share value
        shares = response.data['shares']
        concert_share = next(s for s in shares if s['share_type_code'] == 'concert_commission')
        self.assertEqual(concert_share['value'], '20.0000')

    def test_filter_by_contract_type(self):
        """Test filtering shares by contract type."""
        # Create artist master contract
        artist_contract = Contract.objects.create(
            template=self.template,
            contract_number='CNT-TEST-005',
            title='Artist Contract',
            contract_type='artist_master',
            counterparty_entity=self.entity,
            term_start=date.today(),
            status='signed',
            created_by=self.user
        )

        ContractShare.objects.create(
            contract=artist_contract,
            share_type=self.concert_share_type,
            value=Decimal('10.0000'),
            unit='percent',
            valid_from=artist_contract.term_start
        )

        # Create producer contract (more recent)
        producer_contract = Contract.objects.create(
            template=self.template,
            contract_number='CNT-TEST-006',
            title='Producer Contract',
            contract_type='producer_service',
            counterparty_entity=self.entity,
            term_start=date.today() + timedelta(days=1),
            status='signed',
            created_by=self.user
        )

        ContractShare.objects.create(
            contract=producer_contract,
            share_type=self.master_share_type,
            value=Decimal('3.0000'),
            unit='points',
            valid_from=producer_contract.term_start
        )

        # Request artist_master contract type specifically
        url = f'/api/v1/identity/entities/{self.entity.id}/latest_contract_shares/'
        response = self.client.get(url, {'contract_type': 'artist_master'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['contract_id'], artist_contract.id)
        self.assertEqual(response.data['contract_type'], 'artist_master')

    def test_unauthorized_access(self):
        """Test that unauthenticated users cannot access the endpoint."""
        self.client.force_authenticate(user=None)

        url = f'/api/v1/identity/entities/{self.entity.id}/latest_contract_shares/'
        response = self.client.get(url)

        # Django REST Framework returns 403 when authentication credentials are not provided
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_nonexistent_entity(self):
        """Test accessing shares for nonexistent entity."""
        url = '/api/v1/identity/entities/99999/latest_contract_shares/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_multiple_shares_same_contract(self):
        """Test returning multiple shares from the same contract."""
        contract = Contract.objects.create(
            template=self.template,
            contract_number='CNT-TEST-007',
            title='Multi-Share Contract',
            contract_type='artist_master',
            counterparty_entity=self.entity,
            term_start=date.today(),
            status='signed',
            created_by=self.user
        )

        # Add multiple shares for different years
        ContractShare.objects.create(
            contract=contract,
            share_type=self.concert_share_type,
            value=Decimal('10.0000'),
            unit='percent',
            valid_from=contract.term_start
        )

        ContractShare.objects.create(
            contract=contract,
            share_type=self.concert_share_type,
            value=Decimal('15.0000'),
            unit='percent',
            valid_from=contract.term_start + timedelta(days=365)
        )

        ContractShare.objects.create(
            contract=contract,
            share_type=self.concert_share_type,
            value=Decimal('20.0000'),
            unit='percent',
            valid_from=contract.term_start + timedelta(days=730)
        )

        url = f'/api/v1/identity/entities/{self.entity.id}/latest_contract_shares/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['shares']), 3)
