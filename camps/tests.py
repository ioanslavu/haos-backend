"""
Comprehensive tests for Camps app
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from datetime import date, timedelta

from api.models import Department, Role, UserProfile
from identity.models import Entity
from camps.models import Camp, CampStudio, CampStudioArtist

User = get_user_model()


class CampModelTestCase(TestCase):
    """Test Camp model functionality"""

    def setUp(self):
        """Set up test data"""
        # Create department
        self.department = Department.objects.create(
            code='digital',
            name='Digital Department',
            is_active=True
        )

        # Create admin role
        self.admin_role = Role.objects.create(
            code='administrator',
            name='Administrator',
            level=1000,
            is_system_role=True
        )

        # Create admin user
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='test123',
            first_name='Admin',
            last_name='User'
        )
        UserProfile.objects.create(
            user=self.admin_user,
            role=self.admin_role,
            department=self.department,
            setup_completed=True
        )

        # Create test entity (artist)
        self.artist = Entity.objects.create(
            kind='PF',
            display_name='Test Artist',
            created_by=self.admin_user
        )

    def test_camp_creation_with_valid_data(self):
        """Test creating a camp with valid data"""
        camp = Camp.objects.create(
            name='Test Camp 2024',
            start_date=date(2024, 6, 1),
            end_date=date(2024, 6, 10),
            status='draft',
            department=self.department,
            created_by=self.admin_user
        )

        self.assertEqual(camp.name, 'Test Camp 2024')
        self.assertEqual(camp.status, 'draft')
        self.assertEqual(camp.department, self.department)
        self.assertEqual(camp.created_by, self.admin_user)
        self.assertIsNone(camp.deleted_at)
        self.assertFalse(camp.is_deleted)

    def test_camp_soft_delete_functionality(self):
        """Test soft delete sets deleted_at timestamp"""
        camp = Camp.objects.create(
            name='Test Camp',
            department=self.department,
            created_by=self.admin_user
        )

        # Verify not deleted
        self.assertIsNone(camp.deleted_at)
        self.assertFalse(camp.is_deleted)

        # Soft delete
        camp.soft_delete()

        # Verify deleted
        self.assertIsNotNone(camp.deleted_at)
        self.assertTrue(camp.is_deleted)
        self.assertIsInstance(camp.deleted_at, timezone.datetime)

    def test_camp_studios_count_property(self):
        """Test studios_count property"""
        camp = Camp.objects.create(
            name='Test Camp',
            department=self.department,
            created_by=self.admin_user
        )

        # Initially 0 studios
        self.assertEqual(camp.studios_count, 0)

        # Add studios
        CampStudio.objects.create(camp=camp, name='Studio A')
        CampStudio.objects.create(camp=camp, name='Studio B')

        # Should have 2 studios
        self.assertEqual(camp.studios_count, 2)

    def test_camp_str_representation(self):
        """Test string representation of camp"""
        camp = Camp.objects.create(
            name='Summer Camp 2024',
            department=self.department,
            created_by=self.admin_user
        )
        self.assertEqual(str(camp), 'Summer Camp 2024')


class CampStudioModelTestCase(TestCase):
    """Test CampStudio model functionality"""

    def setUp(self):
        """Set up test data"""
        self.department = Department.objects.create(
            code='digital',
            name='Digital Department',
            is_active=True
        )

        self.admin_role = Role.objects.create(
            code='administrator',
            name='Administrator',
            level=1000,
            is_system_role=True
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
            department=self.department,
            setup_completed=True
        )

        self.camp = Camp.objects.create(
            name='Test Camp',
            department=self.department,
            created_by=self.admin_user
        )

    def test_camp_studio_creation_with_relationship(self):
        """Test creating studio with relationship to camp"""
        studio = CampStudio.objects.create(
            camp=self.camp,
            name='Studio A',
            location='Abbey Road Studios',
            city='London',
            country='UK',
            hours=8.5,
            sessions=4,
            order=1
        )

        self.assertEqual(studio.camp, self.camp)
        self.assertEqual(studio.name, 'Studio A')
        self.assertEqual(studio.location, 'Abbey Road Studios')
        self.assertEqual(studio.city, 'London')
        self.assertEqual(studio.country, 'UK')
        self.assertEqual(float(studio.hours), 8.5)
        self.assertEqual(studio.sessions, 4)
        self.assertEqual(studio.order, 1)

    def test_camp_studio_cascade_delete(self):
        """Test that studios are deleted when camp is deleted"""
        studio = CampStudio.objects.create(
            camp=self.camp,
            name='Studio A'
        )

        studio_id = studio.id
        self.assertTrue(CampStudio.objects.filter(id=studio_id).exists())

        # Hard delete camp (not soft delete)
        self.camp.delete()

        # Studio should be cascade deleted
        self.assertFalse(CampStudio.objects.filter(id=studio_id).exists())

    def test_camp_studio_str_representation(self):
        """Test string representation of studio"""
        studio = CampStudio.objects.create(
            camp=self.camp,
            name='Studio A'
        )
        expected = f"{self.camp.name} - Studio A"
        self.assertEqual(str(studio), expected)


class CampStudioArtistModelTestCase(TestCase):
    """Test CampStudioArtist model functionality"""

    def setUp(self):
        """Set up test data"""
        self.department = Department.objects.create(
            code='digital',
            name='Digital Department',
            is_active=True
        )

        self.admin_role = Role.objects.create(
            code='administrator',
            name='Administrator',
            level=1000,
            is_system_role=True
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
            department=self.department,
            setup_completed=True
        )

        self.camp = Camp.objects.create(
            name='Test Camp',
            department=self.department,
            created_by=self.admin_user
        )

        self.studio = CampStudio.objects.create(
            camp=self.camp,
            name='Studio A'
        )

        self.artist_internal = Entity.objects.create(
            kind='PF',
            display_name='Internal Artist',
            created_by=self.admin_user
        )

        self.artist_external = Entity.objects.create(
            kind='PF',
            display_name='External Artist',
            created_by=self.admin_user
        )

    def test_camp_studio_artist_creation_internal(self):
        """Test creating internal artist assignment"""
        studio_artist = CampStudioArtist.objects.create(
            studio=self.studio,
            artist=self.artist_internal,
            is_internal=True
        )

        self.assertEqual(studio_artist.studio, self.studio)
        self.assertEqual(studio_artist.artist, self.artist_internal)
        self.assertTrue(studio_artist.is_internal)

    def test_camp_studio_artist_creation_external(self):
        """Test creating external artist assignment"""
        studio_artist = CampStudioArtist.objects.create(
            studio=self.studio,
            artist=self.artist_external,
            is_internal=False
        )

        self.assertEqual(studio_artist.studio, self.studio)
        self.assertEqual(studio_artist.artist, self.artist_external)
        self.assertFalse(studio_artist.is_internal)

    def test_camp_studio_artist_unique_constraint(self):
        """Test unique constraint on studio + artist"""
        CampStudioArtist.objects.create(
            studio=self.studio,
            artist=self.artist_internal,
            is_internal=True
        )

        # Attempting to create duplicate should raise error
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            CampStudioArtist.objects.create(
                studio=self.studio,
                artist=self.artist_internal,
                is_internal=False  # Even with different is_internal
            )

    def test_camp_studio_artist_str_representation(self):
        """Test string representation"""
        studio_artist = CampStudioArtist.objects.create(
            studio=self.studio,
            artist=self.artist_internal,
            is_internal=True
        )
        expected = f"{self.studio} - {self.artist_internal.display_name} (Internal)"
        self.assertEqual(str(studio_artist), expected)


class CampSerializerValidationTestCase(TestCase):
    """Test Camp serializer validation"""

    def setUp(self):
        """Set up test data"""
        self.department = Department.objects.create(
            code='digital',
            name='Digital Department',
            is_active=True
        )

        self.manager_role = Role.objects.create(
            code='manager',
            name='Manager',
            level=300,
            department=self.department,
            is_system_role=True
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
            department=self.department,
            setup_completed=True
        )

        self.client = APIClient()

    def test_end_date_validation_before_start_date(self):
        """Test validation fails when end_date is before start_date"""
        self.client.force_authenticate(user=self.manager_user)

        data = {
            'name': 'Invalid Camp',
            'start_date': '2024-06-10',
            'end_date': '2024-06-01',  # Before start_date
            'status': 'draft'
        }

        response = self.client.post('/api/v1/camps/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('end_date', response.data)

    def test_end_date_validation_equal_to_start_date(self):
        """Test validation passes when end_date equals start_date"""
        self.client.force_authenticate(user=self.manager_user)

        data = {
            'name': 'Valid Camp',
            'start_date': '2024-06-01',
            'end_date': '2024-06-01',  # Same as start_date
            'status': 'draft'
        }

        response = self.client.post('/api/v1/camps/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_end_date_validation_after_start_date(self):
        """Test validation passes when end_date is after start_date"""
        self.client.force_authenticate(user=self.manager_user)

        data = {
            'name': 'Valid Camp',
            'start_date': '2024-06-01',
            'end_date': '2024-06-10',
            'status': 'draft'
        }

        response = self.client.post('/api/v1/camps/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class CampAPIPermissionTestCase(TestCase):
    """Test Camp API permissions"""

    def setUp(self):
        """Set up test data"""
        self.department = Department.objects.create(
            code='digital',
            name='Digital Department',
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
            code='employee',
            name='Employee',
            level=200,
            department=self.department,
            is_system_role=True
        )
        self.manager_role = Role.objects.create(
            code='manager',
            name='Manager',
            level=300,
            department=self.department,
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
            password='test123'
        )
        UserProfile.objects.create(
            user=self.guest_user,
            role=self.guest_role,
            setup_completed=True
        )

        self.employee_user = User.objects.create_user(
            email='employee@test.com',
            password='test123'
        )
        UserProfile.objects.create(
            user=self.employee_user,
            role=self.employee_role,
            department=self.department,
            setup_completed=True
        )

        self.manager_user = User.objects.create_user(
            email='manager@test.com',
            password='test123'
        )
        UserProfile.objects.create(
            user=self.manager_user,
            role=self.manager_role,
            department=self.department,
            setup_completed=True
        )

        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='test123'
        )
        UserProfile.objects.create(
            user=self.admin_user,
            role=self.admin_role,
            department=self.department,
            setup_completed=True
        )

        # Create test camp
        self.camp = Camp.objects.create(
            name='Test Camp',
            department=self.department,
            created_by=self.admin_user
        )

        self.client = APIClient()

    def test_unauthenticated_cannot_access_camps(self):
        """Test unauthenticated users cannot access camps"""
        response = self.client.get('/api/v1/camps/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_guest_cannot_access_camps(self):
        """Test guest users (level 100) cannot access camps"""
        self.client.force_authenticate(user=self.guest_user)
        response = self.client.get('/api/v1/camps/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_cannot_access_camps(self):
        """Test employee users (level 200) cannot access camps"""
        self.client.force_authenticate(user=self.employee_user)
        response = self.client.get('/api/v1/camps/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_can_access_camps(self):
        """Test manager users (level 300) can access camps"""
        self.client.force_authenticate(user=self.manager_user)
        response = self.client.get('/api/v1/camps/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_can_access_camps(self):
        """Test admin users (level 1000) can access camps"""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/v1/camps/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_manager_can_create_camp(self):
        """Test manager can create camps"""
        self.client.force_authenticate(user=self.manager_user)

        data = {
            'name': 'New Camp',
            'status': 'draft'
        }

        response = self.client.post('/api/v1/camps/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_employee_cannot_create_camp(self):
        """Test employee cannot create camps"""
        self.client.force_authenticate(user=self.employee_user)

        data = {
            'name': 'New Camp',
            'status': 'draft'
        }

        response = self.client.post('/api/v1/camps/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class CampAPIListTestCase(TestCase):
    """Test GET /api/v1/camps/ - List camps"""

    def setUp(self):
        """Set up test data"""
        self.department = Department.objects.create(
            code='digital',
            name='Digital Department',
            is_active=True
        )

        self.manager_role = Role.objects.create(
            code='manager',
            name='Manager',
            level=300,
            department=self.department,
            is_system_role=True
        )

        self.manager_user = User.objects.create_user(
            email='manager@test.com',
            password='test123'
        )
        UserProfile.objects.create(
            user=self.manager_user,
            role=self.manager_role,
            department=self.department,
            setup_completed=True
        )

        # Create test camps
        self.camp1 = Camp.objects.create(
            name='Summer Camp 2024',
            start_date=date.today() + timedelta(days=10),
            status='draft',
            department=self.department,
            created_by=self.manager_user
        )

        self.camp2 = Camp.objects.create(
            name='Winter Camp 2024',
            start_date=date.today() - timedelta(days=30),
            status='completed',
            department=self.department,
            created_by=self.manager_user
        )

        self.camp3 = Camp.objects.create(
            name='Spring Camp 2024',
            status='active',
            department=self.department,
            created_by=self.manager_user
        )

        # Create a soft-deleted camp
        self.deleted_camp = Camp.objects.create(
            name='Deleted Camp',
            department=self.department,
            created_by=self.manager_user
        )
        self.deleted_camp.soft_delete()

        self.client = APIClient()
        self.client.force_authenticate(user=self.manager_user)

    def test_list_camps_excludes_soft_deleted(self):
        """Test list excludes soft-deleted camps"""
        response = self.client.get('/api/v1/camps/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should return 3 camps (excluding deleted one)
        self.assertEqual(response.data['count'], 3)

        camp_names = [camp['name'] for camp in response.data['results']]
        self.assertNotIn('Deleted Camp', camp_names)

    def test_list_camps_includes_studios_count(self):
        """Test list includes studios_count annotation"""
        # Add studios to camp1
        CampStudio.objects.create(camp=self.camp1, name='Studio A')
        CampStudio.objects.create(camp=self.camp1, name='Studio B')

        response = self.client.get('/api/v1/camps/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Find camp1 in results
        camp1_data = next(
            (camp for camp in response.data['results'] if camp['id'] == self.camp1.id),
            None
        )
        self.assertIsNotNone(camp1_data)
        self.assertEqual(camp1_data['studios_count'], 2)

    def test_search_filter_by_name(self):
        """Test search filter by name"""
        response = self.client.get('/api/v1/camps/', {'search': 'Summer'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['name'], 'Summer Camp 2024')

    def test_status_filter(self):
        """Test status filter"""
        response = self.client.get('/api/v1/camps/', {'status': 'completed'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['status'], 'completed')

    def test_time_filter_upcoming(self):
        """Test time_filter for upcoming camps"""
        response = self.client.get('/api/v1/camps/', {'time_filter': 'upcoming'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should include camp1 (future) and camp3 (no date)
        self.assertEqual(response.data['count'], 2)

    def test_time_filter_past(self):
        """Test time_filter for past camps"""
        response = self.client.get('/api/v1/camps/', {'time_filter': 'past'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should include only camp2 (past date)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.camp2.id)

    def test_time_filter_all(self):
        """Test time_filter for all camps"""
        response = self.client.get('/api/v1/camps/', {'time_filter': 'all'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)


class CampAPICreateTestCase(TestCase):
    """Test POST /api/v1/camps/ - Create camp"""

    def setUp(self):
        """Set up test data"""
        self.department = Department.objects.create(
            code='digital',
            name='Digital Department',
            is_active=True
        )

        self.manager_role = Role.objects.create(
            code='manager',
            name='Manager',
            level=300,
            department=self.department,
            is_system_role=True
        )

        self.manager_user = User.objects.create_user(
            email='manager@test.com',
            password='test123'
        )
        UserProfile.objects.create(
            user=self.manager_user,
            role=self.manager_role,
            department=self.department,
            setup_completed=True
        )

        self.artist1 = Entity.objects.create(
            kind='PF',
            display_name='Artist 1',
            created_by=self.manager_user
        )

        self.artist2 = Entity.objects.create(
            kind='PF',
            display_name='Artist 2',
            created_by=self.manager_user
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.manager_user)

    def test_create_camp_basic(self):
        """Test creating a basic camp without studios"""
        data = {
            'name': 'Test Camp',
            'start_date': '2024-06-01',
            'end_date': '2024-06-10',
            'status': 'draft'
        }

        response = self.client.post('/api/v1/camps/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify camp was created
        camp = Camp.objects.get(id=response.data['id'])
        self.assertEqual(camp.name, 'Test Camp')
        self.assertEqual(camp.department, self.department)
        self.assertEqual(camp.created_by, self.manager_user)

    def test_create_camp_with_nested_studios(self):
        """Test creating camp with nested studios and artists"""
        data = {
            'name': 'Test Camp',
            'status': 'draft',
            'studios': [
                {
                    'name': 'Studio A',
                    'location': 'Abbey Road',
                    'city': 'London',
                    'country': 'UK',
                    'hours': 8.5,
                    'sessions': 4,
                    'order': 1,
                    'internal_artist_ids': [self.artist1.id],
                    'external_artist_ids': [self.artist2.id]
                },
                {
                    'name': 'Studio B',
                    'order': 2,
                    'internal_artist_ids': [self.artist2.id],
                    'external_artist_ids': []
                }
            ]
        }

        response = self.client.post('/api/v1/camps/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify studios were created
        camp = Camp.objects.get(id=response.data['id'])
        self.assertEqual(camp.studios.count(), 2)

        # Verify Studio A
        studio_a = camp.studios.get(name='Studio A')
        self.assertEqual(studio_a.location, 'Abbey Road')
        self.assertEqual(float(studio_a.hours), 8.5)
        self.assertEqual(studio_a.studio_artists.filter(is_internal=True).count(), 1)
        self.assertEqual(studio_a.studio_artists.filter(is_internal=False).count(), 1)

        # Verify Studio B
        studio_b = camp.studios.get(name='Studio B')
        self.assertEqual(studio_b.studio_artists.filter(is_internal=True).count(), 1)
        self.assertEqual(studio_b.studio_artists.filter(is_internal=False).count(), 0)


class CampAPIDetailTestCase(TestCase):
    """Test GET /api/v1/camps/{id}/ - Get camp detail"""

    def setUp(self):
        """Set up test data"""
        self.department = Department.objects.create(
            code='digital',
            name='Digital Department',
            is_active=True
        )

        self.manager_role = Role.objects.create(
            code='manager',
            name='Manager',
            level=300,
            department=self.department,
            is_system_role=True
        )

        self.manager_user = User.objects.create_user(
            email='manager@test.com',
            password='test123'
        )
        UserProfile.objects.create(
            user=self.manager_user,
            role=self.manager_role,
            department=self.department,
            setup_completed=True
        )

        self.camp = Camp.objects.create(
            name='Test Camp',
            department=self.department,
            created_by=self.manager_user
        )

        self.studio = CampStudio.objects.create(
            camp=self.camp,
            name='Studio A'
        )

        self.artist = Entity.objects.create(
            kind='PF',
            display_name='Test Artist',
            created_by=self.manager_user
        )

        CampStudioArtist.objects.create(
            studio=self.studio,
            artist=self.artist,
            is_internal=True
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.manager_user)

    def test_get_camp_detail(self):
        """Test getting camp detail"""
        response = self.client.get(f'/api/v1/camps/{self.camp.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify basic fields
        self.assertEqual(response.data['name'], 'Test Camp')
        self.assertEqual(response.data['id'], self.camp.id)

        # Verify nested studios
        self.assertEqual(len(response.data['studios']), 1)
        studio_data = response.data['studios'][0]
        self.assertEqual(studio_data['name'], 'Studio A')

        # Verify nested artists
        self.assertEqual(len(studio_data['internal_artists']), 1)
        self.assertEqual(studio_data['internal_artists'][0]['display_name'], 'Test Artist')

    def test_get_nonexistent_camp(self):
        """Test getting non-existent camp returns 404"""
        response = self.client.get('/api/v1/camps/99999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_soft_deleted_camp(self):
        """Test getting soft-deleted camp returns 404"""
        self.camp.soft_delete()

        response = self.client.get(f'/api/v1/camps/{self.camp.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class CampAPIUpdateTestCase(TestCase):
    """Test PATCH /api/v1/camps/{id}/ - Update camp"""

    def setUp(self):
        """Set up test data"""
        self.department = Department.objects.create(
            code='digital',
            name='Digital Department',
            is_active=True
        )

        self.manager_role = Role.objects.create(
            code='manager',
            name='Manager',
            level=300,
            department=self.department,
            is_system_role=True
        )

        self.manager_user = User.objects.create_user(
            email='manager@test.com',
            password='test123'
        )
        UserProfile.objects.create(
            user=self.manager_user,
            role=self.manager_role,
            department=self.department,
            setup_completed=True
        )

        self.camp = Camp.objects.create(
            name='Original Name',
            status='draft',
            department=self.department,
            created_by=self.manager_user
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.manager_user)

    def test_update_camp_basic_fields(self):
        """Test updating basic camp fields"""
        data = {
            'name': 'Updated Name',
            'status': 'active'
        }

        response = self.client.patch(
            f'/api/v1/camps/{self.camp.id}/',
            data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify changes
        self.camp.refresh_from_db()
        self.assertEqual(self.camp.name, 'Updated Name')
        self.assertEqual(self.camp.status, 'active')

    def test_update_camp_studios(self):
        """Test updating camp studios replaces existing ones"""
        # Create initial studio
        CampStudio.objects.create(camp=self.camp, name='Old Studio')

        data = {
            'name': 'Updated Camp',
            'studios': [
                {
                    'name': 'New Studio A',
                    'order': 1,
                    'internal_artist_ids': [],
                    'external_artist_ids': []
                }
            ]
        }

        response = self.client.patch(
            f'/api/v1/camps/{self.camp.id}/',
            data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify old studio was deleted and new one created
        self.assertEqual(self.camp.studios.count(), 1)
        self.assertEqual(self.camp.studios.first().name, 'New Studio A')
        self.assertFalse(self.camp.studios.filter(name='Old Studio').exists())


class CampAPIDeleteTestCase(TestCase):
    """Test DELETE /api/v1/camps/{id}/ - Soft delete camp"""

    def setUp(self):
        """Set up test data"""
        self.department = Department.objects.create(
            code='digital',
            name='Digital Department',
            is_active=True
        )

        self.manager_role = Role.objects.create(
            code='manager',
            name='Manager',
            level=300,
            department=self.department,
            is_system_role=True
        )

        self.manager_user = User.objects.create_user(
            email='manager@test.com',
            password='test123'
        )
        UserProfile.objects.create(
            user=self.manager_user,
            role=self.manager_role,
            department=self.department,
            setup_completed=True
        )

        self.camp = Camp.objects.create(
            name='Test Camp',
            department=self.department,
            created_by=self.manager_user
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.manager_user)

    def test_delete_camp_soft_deletes(self):
        """Test DELETE sets deleted_at instead of hard deleting"""
        response = self.client.delete(f'/api/v1/camps/{self.camp.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify camp still exists but is soft-deleted
        self.camp.refresh_from_db()
        self.assertIsNotNone(self.camp.deleted_at)
        self.assertTrue(self.camp.is_deleted)

        # Verify it doesn't appear in list
        list_response = self.client.get('/api/v1/camps/')
        camp_ids = [camp['id'] for camp in list_response.data['results']]
        self.assertNotIn(self.camp.id, camp_ids)


class CampAPIDuplicateTestCase(TestCase):
    """Test POST /api/v1/camps/{id}/duplicate/ - Duplicate camp"""

    def setUp(self):
        """Set up test data"""
        self.department = Department.objects.create(
            code='digital',
            name='Digital Department',
            is_active=True
        )

        self.manager_role = Role.objects.create(
            code='manager',
            name='Manager',
            level=300,
            department=self.department,
            is_system_role=True
        )

        self.manager_user = User.objects.create_user(
            email='manager@test.com',
            password='test123'
        )
        UserProfile.objects.create(
            user=self.manager_user,
            role=self.manager_role,
            department=self.department,
            setup_completed=True
        )

        self.artist = Entity.objects.create(
            kind='PF',
            display_name='Test Artist',
            created_by=self.manager_user
        )

        # Create camp with studios and artists
        self.camp = Camp.objects.create(
            name='Original Camp',
            start_date=date(2024, 6, 1),
            end_date=date(2024, 6, 10),
            status='active',
            department=self.department,
            created_by=self.manager_user
        )

        self.studio = CampStudio.objects.create(
            camp=self.camp,
            name='Studio A',
            location='Abbey Road',
            hours=8.5,
            sessions=4,
            order=1
        )

        CampStudioArtist.objects.create(
            studio=self.studio,
            artist=self.artist,
            is_internal=True
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.manager_user)

    def test_duplicate_camp(self):
        """Test duplicating a camp creates a copy with modified name"""
        response = self.client.post(f'/api/v1/camps/{self.camp.id}/duplicate/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify new camp was created
        new_camp_id = response.data['id']
        self.assertNotEqual(new_camp_id, self.camp.id)

        new_camp = Camp.objects.get(id=new_camp_id)
        self.assertEqual(new_camp.name, 'Original Camp (Copy)')
        self.assertEqual(new_camp.status, 'draft')
        self.assertIsNone(new_camp.start_date)
        self.assertIsNone(new_camp.end_date)

    def test_duplicate_camp_copies_studios(self):
        """Test duplicating camp copies all studios"""
        response = self.client.post(f'/api/v1/camps/{self.camp.id}/duplicate/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        new_camp_id = response.data['id']
        new_camp = Camp.objects.get(id=new_camp_id)

        # Verify studios were copied
        self.assertEqual(new_camp.studios.count(), 1)
        new_studio = new_camp.studios.first()
        self.assertEqual(new_studio.name, 'Studio A')
        self.assertEqual(new_studio.location, 'Abbey Road')
        self.assertEqual(float(new_studio.hours), 8.5)

    def test_duplicate_camp_copies_artists(self):
        """Test duplicating camp copies all studio artists"""
        response = self.client.post(f'/api/v1/camps/{self.camp.id}/duplicate/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        new_camp_id = response.data['id']
        new_camp = Camp.objects.get(id=new_camp_id)
        new_studio = new_camp.studios.first()

        # Verify artists were copied
        self.assertEqual(new_studio.studio_artists.count(), 1)
        new_studio_artist = new_studio.studio_artists.first()
        self.assertEqual(new_studio_artist.artist, self.artist)
        self.assertTrue(new_studio_artist.is_internal)


class CampAPIExportPDFTestCase(TestCase):
    """Test POST /api/v1/camps/{id}/export_pdf/ - Export camp as PDF"""

    def setUp(self):
        """Set up test data"""
        self.department = Department.objects.create(
            code='digital',
            name='Digital Department',
            is_active=True
        )

        self.manager_role = Role.objects.create(
            code='manager',
            name='Manager',
            level=300,
            department=self.department,
            is_system_role=True
        )

        self.manager_user = User.objects.create_user(
            email='manager@test.com',
            password='test123'
        )
        UserProfile.objects.create(
            user=self.manager_user,
            role=self.manager_role,
            department=self.department,
            setup_completed=True
        )

        self.camp = Camp.objects.create(
            name='Test Camp',
            department=self.department,
            created_by=self.manager_user
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.manager_user)

    def test_export_pdf_returns_response(self):
        """Test export_pdf returns a response (don't validate PDF content)"""
        response = self.client.post(f'/api/v1/camps/{self.camp.id}/export_pdf/')

        # Should return 200 (not a REST 201) since it's a download
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify content type
        self.assertEqual(response['Content-Type'], 'application/pdf')

        # Verify Content-Disposition header
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertIn('camp_', response['Content-Disposition'])

    def test_export_pdf_nonexistent_camp(self):
        """Test export_pdf for non-existent camp returns 404"""
        response = self.client.post('/api/v1/camps/99999/export_pdf/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
