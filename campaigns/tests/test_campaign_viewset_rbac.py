"""
Comprehensive RBAC tests for CampaignViewSet.

Tests cover:
- List filtering by role and department
- Retrieve permissions
- Create/Update/Delete permissions
- Through model M2M assignment (CampaignAssignment)
- Edge cases and security vulnerabilities
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from campaigns.models import Campaign, CampaignAssignment
from identity.models import Entity
from catalog.models import Work
from api.models import Department, Role, Role, UserProfile


User = get_user_model()


class CampaignViewSetListFilteringTestCase(TestCase):
    """Test list endpoint filtering based on RBAC."""

    def setUp(self):
        self.client = APIClient()

        # Create departments
        self.dept_digital, _ = Department.objects.get_or_create(code='digital', defaults={'name': 'Digital'})
        self.dept_sales, _ = Department.objects.get_or_create(code='sales', defaults={'name': 'Sales'})

        # Create entities
        self.entity = Entity.objects.create(
            display_name='Test Entity',
            kind='PJ'
        )

        # Create users
        self.admin = User.objects.create_user(username='admin', password='pass')
        self.admin_profile = self.admin.profile
        self.admin_profile.department = self.dept_digital
        self.admin_profile.role = Role.objects.get(code='administrator')
        self.admin_profile.save()

        self.digital_manager = User.objects.create_user(username='dig_manager', password='pass')
        self.digital_manager_profile = self.digital_manager.profile
        self.digital_manager_profile.department = self.dept_digital
        self.digital_manager_profile.role = Role.objects.get(code='digital_manager')
        self.digital_manager_profile.save()

        self.digital_employee1 = User.objects.create_user(username='dig_emp1', password='pass')
        self.digital_employee1_profile = self.digital_employee1.profile
        self.digital_employee1_profile.department = self.dept_digital
        self.digital_employee1_profile.role = Role.objects.get(code='digital_employee')
        self.digital_employee1_profile.save()

        self.digital_employee2 = User.objects.create_user(username='dig_emp2', password='pass')
        self.digital_employee2_profile = self.digital_employee2.profile
        self.digital_employee2_profile.department = self.dept_digital
        self.digital_employee2_profile.role = Role.objects.get(code='digital_employee')
        self.digital_employee2_profile.save()

        self.sales_employee = User.objects.create_user(username='sales_emp', password='pass')
        self.sales_employee_profile = self.sales_employee.profile
        self.sales_employee_profile.department = self.dept_sales
        self.sales_employee_profile.role = Role.objects.get(code='digital_employee')
        self.sales_employee_profile.save()

        # Create campaigns in different departments
        self.campaign_digital_emp1 = Campaign.objects.create(
            campaign_name='Digital Campaign 1',
            client=self.entity,
            brand=self.entity,
            department=self.dept_digital,
            created_by=self.digital_employee1,
            value='5000.00'
        )

        self.campaign_digital_emp2 = Campaign.objects.create(
            campaign_name='Digital Campaign 2',
            client=self.entity,
            brand=self.entity,
            department=self.dept_digital,
            created_by=self.digital_employee2,
            value='5000.00'
        )

        self.campaign_sales = Campaign.objects.create(
            campaign_name='Sales Campaign 1',
            client=self.entity,
            brand=self.entity,
            department=self.dept_sales,
            created_by=self.sales_employee,
            value='5000.00'
        )

        # Assign employee1 to campaign 2 via handler
        CampaignAssignment.objects.create(
            campaign=self.campaign_digital_emp2,
            user=self.digital_employee1,
            role='support'
        )

    def test_admin_sees_all_campaigns(self):
        """Admin should see all campaigns across all departments."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/v1/campaigns/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should see all 3 campaigns
        self.assertEqual(response.data['count'], 3)

    def test_manager_sees_department_campaigns_only(self):
        """Manager should see all campaigns in their department only."""
        self.client.force_authenticate(user=self.digital_manager)
        response = self.client.get('/api/v1/campaigns/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should see 2 digital campaigns
        self.assertEqual(response.data['count'], 2)

        # Verify they're from digital department
        for campaign in response.data['results']:
            self.assertEqual(campaign['department'], self.dept_digital.id)

    def test_employee_sees_only_owned_and_assigned(self):
        """Employee should see only campaigns they created or are assigned to."""
        self.client.force_authenticate(user=self.digital_employee1)
        response = self.client.get('/api/v1/campaigns/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should see 2 campaigns (created 1, assigned to 1)
        self.assertEqual(response.data['count'], 2)

        campaign_ids = [c['id'] for c in response.data['results']]
        self.assertIn(self.campaign_digital_emp1.id, campaign_ids)
        self.assertIn(self.campaign_digital_emp2.id, campaign_ids)

    def test_employee_does_not_see_other_department(self):
        """Employee should not see campaigns from other departments."""
        self.client.force_authenticate(user=self.digital_employee1)
        response = self.client.get('/api/v1/campaigns/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should not see sales campaign
        campaign_ids = [c['id'] for c in response.data['results']]
        self.assertNotIn(self.campaign_sales.id, campaign_ids)

    def test_employee_does_not_see_unrelated_campaign_in_same_dept(self):
        """Employee should not see campaigns in same dept they're not related to."""
        self.client.force_authenticate(user=self.digital_employee2)
        response = self.client.get('/api/v1/campaigns/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should see only 1 campaign (the one they created)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.campaign_digital_emp2.id)

    def test_unauthenticated_user_denied(self):
        """Unauthenticated users should be denied."""
        response = self.client.get('/api/v1/campaigns/')
        # DRF returns 403 when permission classes deny access to unauthenticated users
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class CampaignViewSetRetrievePermissionsTestCase(TestCase):
    """Test retrieve (detail) endpoint permissions."""

    def setUp(self):
        self.client = APIClient()

        # Create departments and users
        self.dept, _ = Department.objects.get_or_create(code='test', defaults={'name': 'Test'})
        self.entity = Entity.objects.create(display_name='Entity', kind='PJ')

        self.owner = User.objects.create_user(username='owner', password='pass')
        self.owner_profile = self.owner.profile
        self.owner_profile.department = self.dept
        self.owner_profile.role = Role.objects.get(code='digital_employee')
        self.owner_profile.save()

        self.assigned = User.objects.create_user(username='assigned', password='pass')
        self.assigned_profile = self.assigned.profile
        self.assigned_profile.department = self.dept
        self.assigned_profile.role = Role.objects.get(code='digital_employee')
        self.assigned_profile.save()

        self.other = User.objects.create_user(username='other', password='pass')
        self.other_profile = self.other.profile
        self.other_profile.department = self.dept
        self.other_profile.role = Role.objects.get(code='digital_employee')
        self.other_profile.save()

        # Create campaign
        self.campaign = Campaign.objects.create(
            campaign_name='Test Campaign',
            client=self.entity,
            brand=self.entity,
            department=self.dept,
            created_by=self.owner,
            value='5000.00'
        )

        # Assign one user
        CampaignAssignment.objects.create(
            campaign=self.campaign,
            user=self.assigned,
            role='support'
        )

    def test_owner_can_retrieve(self):
        """Owner can retrieve their campaign."""
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(f'/api/v1/campaigns/{self.campaign.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.campaign.id)

    def test_assigned_user_can_retrieve(self):
        """Assigned user can retrieve campaign."""
        self.client.force_authenticate(user=self.assigned)
        response = self.client.get(f'/api/v1/campaigns/{self.campaign.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.campaign.id)

    def test_other_user_cannot_retrieve(self):
        """Other user in same dept cannot retrieve unrelated campaign."""
        self.client.force_authenticate(user=self.other)
        response = self.client.get(f'/api/v1/campaigns/{self.campaign.id}/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_manager_can_retrieve_any_in_dept(self):
        """Manager can retrieve any campaign in their department."""
        manager = User.objects.create_user(username='manager', password='pass')
        manager_profile = manager.profile

        manager_profile.department = self.dept

        manager_profile.role = Role.objects.get(code='digital_manager')

        manager_profile.save()

        self.client.force_authenticate(user=manager)
        response = self.client.get(f'/api/v1/campaigns/{self.campaign.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_can_retrieve_any(self):
        """Admin can retrieve any campaign."""
        admin = User.objects.create_user(username='admin', password='pass')
        admin_profile = admin.profile

        admin_profile.department = self.dept

        admin_profile.role = Role.objects.get(code='administrator')

        admin_profile.save()

        self.client.force_authenticate(user=admin)
        response = self.client.get(f'/api/v1/campaigns/{self.campaign.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class CampaignViewSetCreateTestCase(TestCase):
    """Test create endpoint."""

    def setUp(self):
        self.client = APIClient()

        # Use digital department so campaigns auto-assigned to user's dept will be digital
        self.dept, _ = Department.objects.get_or_create(code='digital', defaults={'name': 'Digital'})
        self.entity = Entity.objects.create(display_name='Entity', kind='PJ')

        self.user = User.objects.create_user(username='user', password='pass')
        self.user_profile = self.user.profile
        self.user_profile.department = self.dept
        self.user_profile.role = Role.objects.get(code='digital_employee')
        self.user_profile.save()

    def test_create_auto_assigns_creator(self):
        """Creating campaign should auto-assign creator."""
        self.client.force_authenticate(user=self.user)

        data = {
            'campaign_name': 'New Campaign',
            'brand': self.entity.id,
            'client': self.entity.id,  # Both client and brand are required
            'value': '10000.00',  # Required for service_fee pricing model (default)
        }

        response = self.client.post('/api/v1/campaigns/', data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify creator is assigned
        campaign = Campaign.objects.get(id=response.data['id'])
        self.assertEqual(campaign.created_by, self.user)

    def test_create_sets_department_to_digital(self):
        """Creating campaign should set department to digital."""
        # Ensure digital department exists
        digital_dept = Department.objects.get_or_create(code='digital')[0]

        self.client.force_authenticate(user=self.user)

        data = {
            'campaign_name': 'New Campaign',
            'brand': self.entity.id,
            'client': self.entity.id,
            'value': '10000.00',  # Required for service_fee pricing model (default)
        }

        response = self.client.post('/api/v1/campaigns/', data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify department is digital
        campaign = Campaign.objects.get(id=response.data['id'])
        self.assertEqual(campaign.department.code, 'digital')


class CampaignViewSetUpdateDeleteTestCase(TestCase):
    """Test update and delete permissions."""

    def setUp(self):
        self.client = APIClient()

        self.dept, _ = Department.objects.get_or_create(code='test', defaults={'name': 'Test'})
        self.entity = Entity.objects.create(display_name='Entity', kind='PJ')

        self.owner = User.objects.create_user(username='owner', password='pass')
        self.owner_profile = self.owner.profile
        self.owner_profile.department = self.dept
        self.owner_profile.role = Role.objects.get(code='digital_employee')
        self.owner_profile.save()

        self.other = User.objects.create_user(username='other', password='pass')
        self.other_profile = self.other.profile
        self.other_profile.department = self.dept
        self.other_profile.role = Role.objects.get(code='digital_employee')
        self.other_profile.save()

        self.campaign = Campaign.objects.create(
            campaign_name='Test Campaign',
            client=self.entity,
            brand=self.entity,
            department=self.dept,
            created_by=self.owner,
            value='5000.00'  # Required for service_fee pricing model validation
        )

    def test_owner_can_update(self):
        """Owner can update their campaign."""
        self.client.force_authenticate(user=self.owner)

        data = {'campaign_name': 'Updated Title'}
        response = self.client.patch(f'/api/v1/campaigns/{self.campaign.id}/', data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.campaign_name, 'Updated Title')

    def test_other_user_cannot_update(self):
        """Other user cannot update unrelated campaign."""
        self.client.force_authenticate(user=self.other)

        data = {'campaign_name': 'Hacked Title'}
        response = self.client.patch(f'/api/v1/campaigns/{self.campaign.id}/', data)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.campaign_name, 'Test Campaign')  # Unchanged

    def test_owner_can_delete(self):
        """Owner can delete their campaign."""
        self.client.force_authenticate(user=self.owner)

        response = self.client.delete(f'/api/v1/campaigns/{self.campaign.id}/')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Campaign.objects.filter(id=self.campaign.id).exists())

    def test_other_user_cannot_delete(self):
        """Other user cannot delete unrelated campaign."""
        self.client.force_authenticate(user=self.other)

        response = self.client.delete(f'/api/v1/campaigns/{self.campaign.id}/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Campaign.objects.filter(id=self.campaign.id).exists())


class CampaignAssignmentTestCase(TestCase):
    """Test CampaignAssignment through model assignment logic."""

    def setUp(self):
        self.client = APIClient()

        self.dept, _ = Department.objects.get_or_create(code='test', defaults={'name': 'Test'})
        self.entity = Entity.objects.create(display_name='Entity', kind='PJ')

        self.owner = User.objects.create_user(username='owner', password='pass')
        self.owner_profile = self.owner.profile
        self.owner_profile.department = self.dept
        self.owner_profile.role = Role.objects.get(code='digital_employee')
        self.owner_profile.save()

        self.assigned_lead = User.objects.create_user(username='lead', password='pass')
        self.lead_profile = self.assigned_lead.profile
        self.lead_profile.department = self.dept
        self.lead_profile.role = Role.objects.get(code='digital_employee')
        self.lead_profile.save()

        self.assigned_support = User.objects.create_user(username='support', password='pass')
        self.support_profile = self.assigned_support.profile
        self.support_profile.department = self.dept
        self.support_profile.role = Role.objects.get(code='digital_employee')
        self.support_profile.save()

        self.assigned_observer = User.objects.create_user(username='observer', password='pass')
        self.observer_profile = self.assigned_observer.profile
        self.observer_profile.department = self.dept
        self.observer_profile.role = Role.objects.get(code='digital_employee')
        self.observer_profile.save()

        self.campaign = Campaign.objects.create(
            campaign_name='Test Campaign',
            client=self.entity,
            brand=self.entity,
            department=self.dept,
            created_by=self.owner,
            value='5000.00'
        )

        # Assign different handler roles
        CampaignAssignment.objects.create(
            campaign=self.campaign,
            user=self.assigned_lead,
            role='lead'
        )

        CampaignAssignment.objects.create(
            campaign=self.campaign,
            user=self.assigned_support,
            role='support'
        )

        CampaignAssignment.objects.create(
            campaign=self.campaign,
            user=self.assigned_observer,
            role='observer'
        )

    def test_all_handler_roles_can_retrieve(self):
        """All handler roles should have access to campaign."""
        # Test lead
        self.client.force_authenticate(user=self.assigned_lead)
        response = self.client.get(f'/api/v1/campaigns/{self.campaign.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Test support
        self.client.force_authenticate(user=self.assigned_support)
        response = self.client.get(f'/api/v1/campaigns/{self.campaign.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Test observer
        self.client.force_authenticate(user=self.assigned_observer)
        response = self.client.get(f'/api/v1/campaigns/{self.campaign.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_handler_appears_in_list(self):
        """Assigned users should see campaign in their list."""
        self.client.force_authenticate(user=self.assigned_lead)
        response = self.client.get('/api/v1/campaigns/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        campaign_ids = [c['id'] for c in response.data['results']]
        self.assertIn(self.campaign.id, campaign_ids)

    def test_removing_handler_removes_access(self):
        """Removing handler should remove access for employees."""
        # Remove lead handler
        CampaignAssignment.objects.filter(
            campaign=self.campaign,
            user=self.assigned_lead
        ).delete()

        self.client.force_authenticate(user=self.assigned_lead)

        # Should no longer see in list
        response = self.client.get('/api/v1/campaigns/')
        campaign_ids = [c['id'] for c in response.data['results']]
        self.assertNotIn(self.campaign.id, campaign_ids)

        # Should not be able to retrieve
        response = self.client.get(f'/api/v1/campaigns/{self.campaign.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class CampaignViewSetEdgeCasesTestCase(TestCase):
    """Test edge cases and potential security vulnerabilities."""

    def setUp(self):
        self.client = APIClient()
        self.dept, _ = Department.objects.get_or_create(code='test', defaults={'name': 'Test'})
        self.entity = Entity.objects.create(display_name='Entity', kind='PJ')

    def test_user_without_profile_gets_empty_list(self):
        """User without profile should get empty list."""
        user = User.objects.create_user(username='noprofile', password='pass')

        Campaign.objects.create(
            campaign_name='Campaign',
            client=self.entity,
            brand=self.entity,
            department=self.dept,
            created_by=user,
            value='5000.00'
        )

        self.client.force_authenticate(user=user)
        response = self.client.get('/api/v1/campaigns/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)

    def test_user_without_department_gets_empty_list(self):
        """User without department should get empty list."""
        user = User.objects.create_user(username='nodept', password='pass')
        profile = user.profile

        profile.department = None

        profile.role = Role.objects.get(code='digital_employee')

        profile.save()

        Campaign.objects.create(
            campaign_name='Campaign',
            client=self.entity,
            brand=self.entity,
            department=self.dept,
            value='5000.00'
        )

        self.client.force_authenticate(user=user)
        response = self.client.get('/api/v1/campaigns/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)

    def test_campaign_without_department_only_admin_access(self):
        """Campaign without department should only be accessible to admin."""
        admin = User.objects.create_user(username='admin', password='pass')
        admin_profile = admin.profile

        admin_profile.department = self.dept

        admin_profile.role = Role.objects.get(code='administrator')

        admin_profile.save()

        employee = User.objects.create_user(username='employee', password='pass')
        employee_profile = employee.profile

        employee_profile.department = self.dept

        employee_profile.role = Role.objects.get(code='digital_employee')

        employee_profile.save()

        campaign = Campaign.objects.create(
            campaign_name='No Dept Campaign',
            client=self.entity,
            brand=self.entity,
            department=None,
            created_by=employee,
            value='5000.00'
        )

        # Admin can see it
        self.client.force_authenticate(user=admin)
        response = self.client.get(f'/api/v1/campaigns/{campaign.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Employee cannot see it (even though they created it)
        self.client.force_authenticate(user=employee)
        response = self.client.get(f'/api/v1/campaigns/{campaign.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_deleted_department_prevents_access(self):
        """Campaign in deleted department should not be accessible."""
        dept, _ = Department.objects.get_or_create(code='todelete', defaults={'name': 'ToDelete'})

        user = User.objects.create_user(username='user', password='pass')
        profile = user.profile

        profile.department = dept

        profile.role = Role.objects.get(code='digital_employee')

        profile.save()

        campaign = Campaign.objects.create(
            campaign_name='Campaign',
            client=self.entity,
            brand=self.entity,
            department=dept,
            created_by=user,
            value='5000.00'
        )

        # Delete department
        # Simulate deleted department by setting to None
        campaign.department = None
        campaign.save()
        profile.department = None
        profile.save()

        self.client.force_authenticate(user=user)
        response = self.client.get('/api/v1/campaigns/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)
