from django.test import TestCase
from django.contrib.auth import get_user_model
from unittest.mock import patch
from rest_framework.test import APIClient
from rest_framework import status

from contracts.models import ContractTemplate, Contract
from contracts.rbac import ContractTypePolicy


User = get_user_model()


class ContractsRBACEnforcementTest(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Users
        self.admin = User.objects.create_superuser(
            username='admin', email='admin@example.com', password='pass'
        )

        self.dig_manager = User.objects.create_user(
            username='dig_manager', email='dig_manager@example.com', password='pass'
        )
        self.dig_manager.profile.role = 'digital_manager'
        self.dig_manager.profile.department = 'digital'
        self.dig_manager.profile.save()

        self.dig_employee = User.objects.create_user(
            username='dig_employee', email='dig_employee@example.com', password='pass'
        )
        self.dig_employee.profile.role = 'digital_employee'
        self.dig_employee.profile.department = 'digital'
        self.dig_employee.profile.save()

        self.sales_employee = User.objects.create_user(
            username='sales_employee', email='sales_employee@example.com', password='pass'
        )
        self.sales_employee.profile.role = 'sales_employee'
        self.sales_employee.profile.department = 'sales'
        self.sales_employee.profile.save()

        # Template and two contracts in different departments/types
        self.template = ContractTemplate.objects.create(
            name='T', gdrive_template_file_id='tmpl', gdrive_output_folder_id='out', created_by=self.admin
        )

        self.digital_artist = Contract.objects.create(
            template=self.template,
            contract_number='DIG-ART-1',
            title='Digital Artist',
            contract_type='artist_master',
            department='digital',
            status='draft',
            created_by=self.dig_manager,
        )

        self.digital_producer = Contract.objects.create(
            template=self.template,
            contract_number='DIG-PROD-1',
            title='Digital Producer',
            contract_type='producer_service',
            department='digital',
            status='draft',
            created_by=self.dig_manager,
        )

        self.sales_artist = Contract.objects.create(
            template=self.template,
            contract_number='SAL-ART-1',
            title='Sales Artist',
            contract_type='artist_master',
            department='sales',
            status='draft',
            created_by=self.sales_employee,
        )

        # Policies: digital_employee can view/update/regenerate artist_master only
        ContractTypePolicy.objects.create(
            role='digital_employee', department='digital', contract_type='artist_master',
            can_view=True, can_publish=False, can_send=False, can_update=True, can_delete=False, can_regenerate=True,
        )
        # Manager: allow all on both types in digital
        ContractTypePolicy.objects.create(
            role='digital_manager', department='digital', contract_type='artist_master',
            can_view=True, can_publish=True, can_send=True, can_update=True, can_delete=True, can_regenerate=True,
        )
        ContractTypePolicy.objects.create(
            role='digital_manager', department='digital', contract_type='producer_service',
            can_view=True, can_publish=True, can_send=True, can_update=True, can_delete=True, can_regenerate=True,
        )

        # Admin via profile (not superuser)
        self.admin_profile = User.objects.create_user(
            username='admin_profile', email='admin_profile@example.com', password='pass'
        )
        self.admin_profile.profile.role = 'administrator'
        self.admin_profile.profile.department = None
        self.admin_profile.profile.save()

    def test_view_scoping_limits_by_department_and_type(self):
        self.client.force_authenticate(self.dig_employee)
        resp = self.client.get('/api/v1/contracts/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # Paginated list
        results = resp.data.get('results') or []
        ids = {c['id'] for c in results}
        self.assertIn(self.digital_artist.id, ids)
        self.assertNotIn(self.digital_producer.id, ids)  # not allowed type
        self.assertNotIn(self.sales_artist.id, ids)      # other department

    def test_make_public_permission_denied(self):
        self.client.force_authenticate(self.dig_employee)
        url = f'/api/v1/contracts/{self.digital_artist.id}/make_public/'
        # Even without gdrive_file_id, permission class should deny first
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_make_public_allowed_path_skipped_external(self):
        # Manager should pass permission gate; missing file yields 400 (not 403)
        self.client.force_authenticate(self.dig_manager)
        url = f'/api/v1/contracts/{self.digital_artist.id}/make_public/'
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_allowed_when_policy_true_and_denied_otherwise(self):
        self.client.force_authenticate(self.dig_employee)
        # Allowed type
        url = f'/api/v1/contracts/{self.digital_artist.id}/'
        resp = self.client.patch(url, {'title': 'New Title'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # Denied type
        url2 = f'/api/v1/contracts/{self.digital_producer.id}/'
        resp2 = self.client.patch(url2, {'title': 'X'}, format='json')
        self.assertIn(resp2.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))

    def test_update_denied_on_department_mismatch(self):
        self.client.force_authenticate(self.dig_employee)
        url = f'/api/v1/contracts/{self.sales_artist.id}/'
        resp = self.client.patch(url, {'title': 'Nope'}, format='json')
        self.assertIn(resp.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))

    def test_delete_denied_without_policy_and_not_found_out_of_scope(self):
        # Employee cannot delete (forbidden or not found due to queryset scoping)
        self.client.force_authenticate(self.dig_employee)
        url = f'/api/v1/contracts/{self.digital_artist.id}/'
        resp = self.client.delete(url)
        self.assertIn(resp.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))

    def test_regenerate_permission(self):
        self.client.force_authenticate(self.dig_employee)
        # Allowed type
        url = f'/api/v1/contracts/{self.digital_artist.id}/regenerate/'
        resp = self.client.post(url, {'placeholder_values': {'a': 'b'}}, format='json')
        self.assertIn(resp.status_code, (status.HTTP_202_ACCEPTED,))
        # Denied type
        url2 = f'/api/v1/contracts/{self.digital_producer.id}/regenerate/'
        resp2 = self.client.post(url2, {'placeholder_values': {'a': 'b'}}, format='json')
        self.assertIn(resp2.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))

    def test_admin_override_allows_actions_but_business_rules_still_apply(self):
        # Update signed should be blocked by signed rule
        self.digital_artist.status = 'signed'
        self.digital_artist.save()
        self.client.force_authenticate(self.admin)
        url = f'/api/v1/contracts/{self.digital_artist.id}/'
        resp = self.client.patch(url, {'title': 'Admin Update'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

        # Delete signed should be blocked
        resp2 = self.client.delete(url)
        self.assertEqual(resp2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_profile_override(self):
        self.client.force_authenticate(self.admin_profile)
        # Can update regardless of policy
        url = f'/api/v1/contracts/{self.digital_producer.id}/'
        resp = self.client.patch(url, {'title': 'Admin Profile Update'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_make_public_missing_file_returns_400_even_with_permission(self):
        self.client.force_authenticate(self.dig_manager)
        url = f'/api/v1/contracts/{self.digital_artist.id}/make_public/'
        # missing gdrive_file_id
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # Skipped: external cancellation check for Dropbox Sign

    def test_regenerate_requires_draft_or_failed(self):
        # Allow employee on allowed type, but set status to pending_signature
        self.client.force_authenticate(self.dig_employee)
        self.digital_artist.status = 'pending_signature'
        self.digital_artist.save()
        url = f'/api/v1/contracts/{self.digital_artist.id}/regenerate/'
        resp = self.client.post(url, {'placeholder_values': {'x': 'y'}}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_status_update_only_allowed_in_draft_or_pending(self):
        self.client.force_authenticate(self.dig_manager)
        # draft -> OK to set status
        url = f'/api/v1/contracts/{self.digital_producer.id}/'
        resp = self.client.patch(url, {'status': 'processing'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # signed -> cannot update
        self.digital_producer.status = 'signed'
        self.digital_producer.save()
        resp2 = self.client.patch(url, {'status': 'draft'}, format='json')
        self.assertEqual(resp2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_view_when_no_policy_rows_returns_only_null_type_in_dept(self):
        # Create a no-type contract in digital
        no_type = Contract.objects.create(
            template=self.template,
            contract_number='DIG-NULL-1',
            title='No Type',
            contract_type=None,
            department='digital',
            status='draft',
            created_by=self.dig_manager,
        )
        # Authenticate a role with no policy rows in sales dept
        self.client.force_authenticate(self.sales_employee)
        resp = self.client.get('/api/v1/contracts/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data.get('results') or []
        ids = {c['id'] for c in results}
        # Should not see digital contracts
        self.assertNotIn(self.digital_artist.id, ids)
        # Now authenticate digital employee but delete policy rows first
        ContractTypePolicy.objects.filter(role='digital_employee', department='digital').delete()
        self.client.force_authenticate(self.dig_employee)
        resp2 = self.client.get('/api/v1/contracts/')
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        results2 = resp2.data.get('results') or []
        ids2 = {c['id'] for c in results2}
        # Should not see typed contracts due to no policy; should see null-type within department
        self.assertNotIn(self.digital_artist.id, ids2)
        self.assertIn(no_type.id, ids2)

    def test_actions_denied_when_policy_absent_even_if_visible(self):
        # Make a null-type contract visible via list to digital_employee
        visible = Contract.objects.create(
            template=self.template,
            contract_number='DIG-NULL-2',
            title='Null Type Visible',
            contract_type=None,
            department='digital',
            status='draft',
            created_by=self.dig_manager,
        )
        # Remove all policies for employee
        ContractTypePolicy.objects.filter(role='digital_employee', department='digital').delete()
        self.client.force_authenticate(self.dig_employee)
        # Update should be denied (no policy lookup for None type)
        resp = self.client.patch(f'/api/v1/contracts/{visible.id}/', {'title': 'X'}, format='json')
        self.assertIn(resp.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))

    def test_department_mismatch_denied_or_not_found_for_manager(self):
        self.client.force_authenticate(self.dig_manager)
        # Trying to delete a sales dept contract
        resp = self.client.delete(f'/api/v1/contracts/{self.sales_artist.id}/')
        self.assertIn(resp.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))

    def test_send_for_signature_permissions_employee_denied(self):
        # Employee cannot send
        self.client.force_authenticate(self.dig_employee)
        resp = self.client.post(
            f'/api/v1/contracts/{self.digital_artist.id}/send_for_signature/',
            {'signers': [{'email': 'a@b.com', 'name': 'A'}]}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

        # Manager path intentionally not tested to avoid external dependency
