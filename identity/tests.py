from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from api.models import Department, Role, UserProfile
from identity.models import Entity, ContactPerson
from campaigns.models import Campaign, CampaignHandler

User = get_user_model()


class EntityAccessTestCase(TestCase):
    """Test entity access permissions for different roles."""

    def setUp(self):
        """Set up test data."""
        # Create departments
        self.digital_dept = Department.objects.create(
            code='digital',
            name='Digital Department',
            is_active=True
        )
        self.sales_dept = Department.objects.create(
            code='sales',
            name='Sales Department',
            is_active=True
        )

        # Create roles
        self.guest_role = Role.objects.create(
            code='guest',
            name='Guest',
            level=100,
            is_system_role=True
        )
        self.employee_role = Role.objects.create(
            code='digital_employee',
            name='Digital Employee',
            level=200,
            department=self.digital_dept,
            is_system_role=True
        )
        self.manager_role = Role.objects.create(
            code='digital_manager',
            name='Digital Manager',
            level=300,
            department=self.digital_dept,
            is_system_role=True
        )
        self.admin_role = Role.objects.create(
            code='administrator',
            name='Administrator',
            level=1000,
            is_system_role=True
        )

        # Create users
        self.guest_user = User.objects.create_user(
            email='guest@test.com',
            password='test123',
            first_name='Guest',
            last_name='User'
        )
        UserProfile.objects.create(
            user=self.guest_user,
            role=self.guest_role,
            setup_completed=True
        )

        self.employee_user = User.objects.create_user(
            email='employee@test.com',
            password='test123',
            first_name='Employee',
            last_name='User'
        )
        UserProfile.objects.create(
            user=self.employee_user,
            role=self.employee_role,
            department=self.digital_dept,
            setup_completed=True
        )

        self.manager_user = User.objects.create_user(
            email='manager@test.com',
            password='test123',
            first_name='Manager',
            last_name='User'
        )
        UserProfile.objects.create(
            user=self.manager_user,
            role=self.manager_role,
            department=self.digital_dept,
            setup_completed=True
        )

        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='test123',
            first_name='Admin',
            last_name='User'
        )
        UserProfile.objects.create(
            user=self.admin_user,
            role=self.admin_role,
            setup_completed=True
        )

        # Create entities
        self.entity1 = Entity.objects.create(
            kind='PF',
            display_name='Test Artist 1',
            created_by=self.admin_user
        )
        self.entity2 = Entity.objects.create(
            kind='PJ',
            display_name='Test Client 1',
            created_by=self.admin_user
        )

        # Create contact persons
        self.contact1 = ContactPerson.objects.create(
            entity=self.entity1,
            name='Contact Person 1',
            role='manager'
        )

        # Create campaigns
        self.campaign_digital = Campaign.objects.create(
            campaign_name='Digital Campaign',
            client=self.entity1,
            artist=self.entity2,
            brand=self.entity1,
            department=self.digital_dept,
            value=10000,
            status='lead',
            created_by=self.admin_user
        )
        self.campaign_sales = Campaign.objects.create(
            campaign_name='Sales Campaign',
            client=self.entity1,
            artist=self.entity2,
            brand=self.entity1,
            department=self.sales_dept,
            value=20000,
            status='lead',
            created_by=self.admin_user
        )
        self.campaign_admin_only = Campaign.objects.create(
            campaign_name='Admin Only Campaign',
            client=self.entity1,
            artist=self.entity2,
            brand=self.entity1,
            department=None,  # Admin-only campaign
            value=30000,
            status='lead',
            created_by=self.admin_user
        )

        # Assign employee as handler to digital campaign
        CampaignHandler.objects.create(
            campaign=self.campaign_digital,
            user=self.employee_user,
            role='lead'
        )

        self.client = APIClient()

    def test_guest_cannot_access_entities(self):
        """Test that guest users cannot access entity list."""
        self.client.force_authenticate(user=self.guest_user)
        response = self.client.get('/api/v1/entities/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_can_access_entities(self):
        """Test that employees can access entity list."""
        self.client.force_authenticate(user=self.employee_user)
        response = self.client.get('/api/v1/entities/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_manager_can_access_entities(self):
        """Test that managers can access entity list."""
        self.client.force_authenticate(user=self.manager_user)
        response = self.client.get('/api/v1/entities/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_can_access_entities(self):
        """Test that admins can access entity list."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/v1/entities/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_guest_cannot_access_entity_detail(self):
        """Test that guest users cannot access entity details."""
        self.client.force_authenticate(user=self.guest_user)
        response = self.client.get(f'/api/v1/entities/{self.entity1.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_can_access_entity_detail(self):
        """Test that employees can access entity details."""
        self.client.force_authenticate(user=self.employee_user)
        response = self.client.get(f'/api/v1/entities/{self.entity1.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['display_name'], 'Test Artist 1')

    def test_employee_sees_only_assigned_campaigns(self):
        """Test that employees only see campaigns they're assigned to."""
        self.client.force_authenticate(user=self.employee_user)
        response = self.client.get(f'/api/v1/entities/{self.entity1.id}/relationships/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Employee should only see the digital campaign they're assigned to
        campaigns = response.data.get('campaigns', [])
        self.assertEqual(len(campaigns), 1)
        self.assertEqual(campaigns[0]['campaign_name'], 'Digital Campaign')

    def test_manager_sees_department_campaigns(self):
        """Test that managers see all campaigns from their department."""
        self.client.force_authenticate(user=self.manager_user)
        response = self.client.get(f'/api/v1/entities/{self.entity1.id}/relationships/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Manager should see all campaigns from digital department
        campaigns = response.data.get('campaigns', [])
        self.assertEqual(len(campaigns), 1)
        self.assertEqual(campaigns[0]['campaign_name'], 'Digital Campaign')

    def test_admin_sees_all_campaigns(self):
        """Test that admins see all campaigns including admin-only."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(f'/api/v1/entities/{self.entity1.id}/relationships/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Admin should see all campaigns
        campaigns = response.data.get('campaigns', [])
        self.assertEqual(len(campaigns), 3)
        campaign_names = [c['campaign_name'] for c in campaigns]
        self.assertIn('Digital Campaign', campaign_names)
        self.assertIn('Sales Campaign', campaign_names)
        self.assertIn('Admin Only Campaign', campaign_names)

    def test_unauthenticated_cannot_access_entities(self):
        """Test that unauthenticated users cannot access entities."""
        response = self.client.get('/api/v1/entities/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
