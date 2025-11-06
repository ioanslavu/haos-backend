"""
Tests for Song Workflow API/ViewSets.

Tests REST API endpoints using Django REST Framework's APITestCase:
- Song CRUD operations
- Custom actions (transition, send_to_digital, archive, etc.)
- Nested resources (checklist, assets, notes, alerts)
- Permission-based filtering
"""

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from catalog.models import (
    Work, Recording, Release, Song, SongChecklistItem,
    SongStageTransition, SongAsset, SongNote, SongAlert
)
from api.models import Department, Role, UserProfile
from identity.models import Entity, Identifier
from rights.models import Split

User = get_user_model()


class SongAPICRUDTestCase(APITestCase):
    """Test Song CRUD API endpoints."""

    def setUp(self):
        """Set up test data."""
        # Create departments
        self.publishing_dept = Department.objects.create(
            code='publishing',
            name='Publishing Department'
        )
        self.label_dept = Department.objects.create(
            code='label',
            name='Label Department'
        )
        self.marketing_dept = Department.objects.create(
            code='marketing',
            name='Marketing Department'
        )

        # Create roles
        self.admin_role = Role.objects.create(
            code='administrator',
            name='Administrator',
            level=1000
        )
        self.publishing_role = Role.objects.create(
            code='publishing_employee',
            name='Publishing Employee',
            level=200,
            department=self.publishing_dept
        )
        self.marketing_role = Role.objects.create(
            code='marketing_employee',
            name='Marketing Employee',
            level=200,
            department=self.marketing_dept
        )

        # Create users
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

        self.publishing_user = User.objects.create_user(
            email='publishing@test.com',
            password='test123',
            first_name='Publishing',
            last_name='User'
        )
        UserProfile.objects.create(
            user=self.publishing_user,
            role=self.publishing_role,
            department=self.publishing_dept,
            setup_completed=True
        )

        self.marketing_user = User.objects.create_user(
            email='marketing@test.com',
            password='test123',
            first_name='Marketing',
            last_name='User'
        )
        UserProfile.objects.create(
            user=self.marketing_user,
            role=self.marketing_role,
            department=self.marketing_dept,
            setup_completed=True
        )

        self.client = APIClient()

    def test_list_songs_filtered_by_department(self):
        """Test listing songs filtered by user's department."""
        # Create songs in different stages
        song_publishing = Song.objects.create(
            title='Publishing Song',
            created_by=self.publishing_user,
            stage='publishing'
        )
        song_marketing = Song.objects.create(
            title='Marketing Song',
            created_by=self.publishing_user,
            stage='marketing_assets'
        )

        # Publishing user can see publishing stage
        self.client.force_authenticate(user=self.publishing_user)
        response = self.client.get('/api/v1/songs/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [s['title'] for s in response.data['results']]
        self.assertIn('Publishing Song', titles)

        # Marketing user can only see marketing stage
        self.client.force_authenticate(user=self.marketing_user)
        response = self.client.get('/api/v1/songs/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [s['title'] for s in response.data['results']]
        self.assertIn('Marketing Song', titles)
        self.assertNotIn('Publishing Song', titles)

    def test_create_song(self):
        """Test creating a song."""
        self.client.force_authenticate(user=self.publishing_user)

        data = {
            'title': 'New Song',
            'genre': 'Pop',
            'language': 'en',
            'priority': 'normal'
        }

        response = self.client.post('/api/v1/songs/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'New Song')
        self.assertEqual(response.data['stage'], 'draft')

        # Verify created_by is set
        song = Song.objects.get(id=response.data['id'])
        self.assertEqual(song.created_by, self.publishing_user)

    def test_retrieve_song(self):
        """Test retrieving a song."""
        song = Song.objects.create(
            title='Test Song',
            created_by=self.publishing_user,
            stage='publishing'
        )

        self.client.force_authenticate(user=self.publishing_user)
        response = self.client.get(f'/api/v1/songs/{song.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Test Song')

    def test_update_song(self):
        """Test updating a song."""
        song = Song.objects.create(
            title='Test Song',
            created_by=self.publishing_user,
            stage='draft'
        )

        self.client.force_authenticate(user=self.publishing_user)
        data = {
            'title': 'Updated Song',
            'genre': 'Rock',
            'language': 'en'
        }

        response = self.client.patch(f'/api/v1/songs/{song.id}/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Updated Song')
        self.assertEqual(response.data['genre'], 'Rock')

    def test_delete_song(self):
        """Test deleting a song."""
        song = Song.objects.create(
            title='Test Song',
            created_by=self.publishing_user,
            stage='draft'
        )

        self.client.force_authenticate(user=self.publishing_user)
        response = self.client.delete(f'/api/v1/songs/{song.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Song.objects.filter(id=song.id).exists())

    def test_non_owner_cannot_delete_song(self):
        """Test that non-owner cannot delete song."""
        song = Song.objects.create(
            title='Test Song',
            created_by=self.publishing_user,
            stage='marketing_assets'
        )

        # Marketing user cannot delete (no permission)
        self.client.force_authenticate(user=self.marketing_user)
        response = self.client.delete(f'/api/v1/songs/{song.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class SongTransitionTestCase(APITestCase):
    """Test song stage transition endpoints."""

    def setUp(self):
        """Set up test data."""
        self.publishing_dept = Department.objects.create(
            code='publishing',
            name='Publishing Department'
        )
        self.label_dept = Department.objects.create(
            code='label',
            name='Label Department'
        )

        self.admin_role = Role.objects.create(
            code='administrator',
            name='Administrator',
            level=1000
        )
        self.publishing_role = Role.objects.create(
            code='publishing_employee',
            name='Publishing Employee',
            level=200,
            department=self.publishing_dept
        )

        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='test123'
        )
        UserProfile.objects.create(
            user=self.admin_user,
            role=self.admin_role,
            setup_completed=True
        )

        self.publishing_user = User.objects.create_user(
            email='publishing@test.com',
            password='test123'
        )
        UserProfile.objects.create(
            user=self.publishing_user,
            role=self.publishing_role,
            department=self.publishing_dept,
            setup_completed=True
        )

        self.client = APIClient()

    def test_valid_transition(self):
        """Test valid stage transition."""
        song = Song.objects.create(
            title='Test Song',
            created_by=self.publishing_user,
            stage='publishing'
        )

        # Create complete checklist
        SongChecklistItem.objects.create(
            song=song,
            stage='publishing',
            category='Work Setup',
            item_name='Work created',
            description='Create work',
            required=True,
            validation_type='manual',
            is_complete=True,
            order=1
        )

        self.client.force_authenticate(user=self.admin_user)
        data = {
            'target_stage': 'label_recording',
            'notes': 'Moving to label'
        }

        response = self.client.post(f'/api/v1/songs/{song.id}/transition/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['stage'], 'label_recording')

        # Verify transition was logged
        song.refresh_from_db()
        self.assertEqual(song.stage, 'label_recording')
        self.assertTrue(song.stage_transitions.exists())

    def test_invalid_transition_incomplete_checklist(self):
        """Test transition fails with incomplete checklist."""
        song = Song.objects.create(
            title='Test Song',
            created_by=self.publishing_user,
            stage='publishing'
        )

        # Create incomplete checklist
        SongChecklistItem.objects.create(
            song=song,
            stage='publishing',
            category='Work Setup',
            item_name='Work created',
            description='Create work',
            required=True,
            validation_type='manual',
            is_complete=False,  # Not complete
            order=1
        )

        self.client.force_authenticate(user=self.publishing_user)
        data = {
            'target_stage': 'label_recording'
        }

        response = self.client.post(f'/api/v1/songs/{song.id}/transition/', data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Checklist', response.data['error'])

    def test_invalid_transition_wrong_stage(self):
        """Test transition fails for invalid stage progression."""
        song = Song.objects.create(
            title='Test Song',
            created_by=self.publishing_user,
            stage='draft'
        )

        self.client.force_authenticate(user=self.admin_user)
        data = {
            'target_stage': 'label_recording'  # Cannot skip publishing
        }

        response = self.client.post(f'/api/v1/songs/{song.id}/transition/', data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_transition_wrong_department(self):
        """Test transition fails when user is from wrong department."""
        song = Song.objects.create(
            title='Test Song',
            created_by=self.publishing_user,
            stage='label_recording'
        )

        # Publishing user cannot transition from label_recording
        self.client.force_authenticate(user=self.publishing_user)
        data = {
            'target_stage': 'marketing_assets'
        }

        response = self.client.post(f'/api/v1/songs/{song.id}/transition/', data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class SongCustomActionsTestCase(APITestCase):
    """Test custom song actions."""

    def setUp(self):
        """Set up test data."""
        self.digital_dept = Department.objects.create(
            code='digital',
            name='Digital Department'
        )

        self.admin_role = Role.objects.create(
            code='administrator',
            name='Administrator',
            level=1000
        )
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='test123'
        )
        UserProfile.objects.create(
            user=self.admin_user,
            role=self.admin_role,
            setup_completed=True
        )

        self.client = APIClient()

    def test_send_to_digital_action(self):
        """Test send_to_digital action creates urgent alert."""
        song = Song.objects.create(
            title='Test Song',
            created_by=self.admin_user,
            stage='ready_for_digital'
        )

        self.client.force_authenticate(user=self.admin_user)
        data = {
            'target_stage': 'digital_distribution'
        }

        response = self.client.post(f'/api/v1/songs/{song.id}/send_to_digital/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify urgent alert was created
        alert = SongAlert.objects.filter(
            song=song,
            alert_type='sent_to_digital',
            priority='urgent'
        ).first()
        self.assertIsNotNone(alert)

    def test_archive_action(self):
        """Test archiving a song."""
        song = Song.objects.create(
            title='Test Song',
            created_by=self.admin_user,
            stage='publishing'
        )

        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(f'/api/v1/songs/{song.id}/archive/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        song.refresh_from_db()
        self.assertTrue(song.is_archived)
        self.assertEqual(song.stage, 'archived')

    def test_my_queue_action(self):
        """Test getting user's department queue."""
        publishing_dept = Department.objects.create(
            code='publishing',
            name='Publishing'
        )
        publishing_role = Role.objects.create(
            code='publishing_employee',
            name='Publishing Employee',
            level=200,
            department=publishing_dept
        )
        publishing_user = User.objects.create_user(
            email='publishing@test.com',
            password='test123'
        )
        UserProfile.objects.create(
            user=publishing_user,
            role=publishing_role,
            department=publishing_dept,
            setup_completed=True
        )

        # Create songs
        song1 = Song.objects.create(
            title='Publishing Song',
            created_by=publishing_user,
            stage='publishing'
        )
        song2 = Song.objects.create(
            title='Label Song',
            created_by=self.admin_user,
            stage='label_recording'
        )

        self.client.force_authenticate(user=publishing_user)
        response = self.client.get('/api/v1/songs/my_queue/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        titles = [s['title'] for s in response.data]
        self.assertIn('Publishing Song', titles)
        self.assertNotIn('Label Song', titles)

    def test_overdue_action_manager_only(self):
        """Test that only managers can view overdue songs."""
        publishing_dept = Department.objects.create(
            code='publishing',
            name='Publishing'
        )
        employee_role = Role.objects.create(
            code='publishing_employee',
            name='Publishing Employee',
            level=200,  # Employee
            department=publishing_dept
        )
        employee_user = User.objects.create_user(
            email='employee@test.com',
            password='test123'
        )
        UserProfile.objects.create(
            user=employee_user,
            role=employee_role,
            department=publishing_dept,
            setup_completed=True
        )

        # Employee cannot access
        self.client.force_authenticate(user=employee_user)
        response = self.client.get('/api/v1/songs/overdue/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Admin can access
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/v1/songs/overdue/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_stats_action(self):
        """Test getting department statistics."""
        publishing_dept = Department.objects.create(
            code='publishing',
            name='Publishing'
        )
        publishing_role = Role.objects.create(
            code='publishing_employee',
            name='Publishing Employee',
            level=200,
            department=publishing_dept
        )
        publishing_user = User.objects.create_user(
            email='publishing@test.com',
            password='test123'
        )
        UserProfile.objects.create(
            user=publishing_user,
            role=publishing_role,
            department=publishing_dept,
            setup_completed=True
        )

        # Create songs
        Song.objects.create(
            title='Draft Song',
            created_by=publishing_user,
            stage='draft'
        )
        Song.objects.create(
            title='Publishing Song',
            created_by=publishing_user,
            stage='publishing',
            priority='urgent'
        )

        self.client.force_authenticate(user=publishing_user)
        response = self.client.get('/api/v1/songs/stats/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_songs', response.data)
        self.assertIn('by_stage', response.data)
        self.assertIn('by_priority', response.data)
        self.assertEqual(response.data['total_songs'], 2)


class SongChecklistAPITestCase(APITestCase):
    """Test song checklist nested endpoints."""

    def setUp(self):
        """Set up test data."""
        self.publishing_dept = Department.objects.create(
            code='publishing',
            name='Publishing'
        )
        self.publishing_role = Role.objects.create(
            code='publishing_employee',
            name='Publishing Employee',
            level=200,
            department=self.publishing_dept
        )
        self.manager_role = Role.objects.create(
            code='publishing_manager',
            name='Publishing Manager',
            level=300,
            department=self.publishing_dept
        )

        self.employee_user = User.objects.create_user(
            email='employee@test.com',
            password='test123'
        )
        UserProfile.objects.create(
            user=self.employee_user,
            role=self.publishing_role,
            department=self.publishing_dept,
            setup_completed=True
        )

        self.manager_user = User.objects.create_user(
            email='manager@test.com',
            password='test123'
        )
        UserProfile.objects.create(
            user=self.manager_user,
            role=self.manager_role,
            department=self.publishing_dept,
            setup_completed=True
        )

        self.song = Song.objects.create(
            title='Test Song',
            created_by=self.employee_user,
            stage='publishing'
        )

        self.client = APIClient()

    def test_list_checklist_items(self):
        """Test listing checklist items for a song."""
        item = SongChecklistItem.objects.create(
            song=self.song,
            stage='publishing',
            category='Work Setup',
            item_name='Work created',
            description='Create work',
            required=True,
            validation_type='manual',
            order=1
        )

        self.client.force_authenticate(user=self.employee_user)
        response = self.client.get(f'/api/v1/songs/{self.song.id}/checklist/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['item_name'], 'Work created')

    def test_toggle_checklist_item(self):
        """Test toggling manual checklist item."""
        item = SongChecklistItem.objects.create(
            song=self.song,
            stage='publishing',
            category='Work Setup',
            item_name='Work created',
            description='Create work',
            required=True,
            validation_type='manual',
            is_complete=False,
            order=1
        )

        self.client.force_authenticate(user=self.employee_user)
        response = self.client.post(f'/api/v1/songs/{self.song.id}/checklist/{item.id}/toggle/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_complete'])

        # Toggle back
        response = self.client.post(f'/api/v1/songs/{self.song.id}/checklist/{item.id}/toggle/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_complete'])

    def test_cannot_toggle_auto_checklist_item(self):
        """Test that auto checklist items cannot be toggled."""
        item = SongChecklistItem.objects.create(
            song=self.song,
            stage='publishing',
            category='Work Setup',
            item_name='Work created',
            description='Create work',
            required=True,
            validation_type='auto_entity_exists',
            validation_rule={'entity': 'work'},
            order=1
        )

        self.client.force_authenticate(user=self.employee_user)
        response = self.client.post(f'/api/v1/songs/{self.song.id}/checklist/{item.id}/toggle/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class SongAssetAPITestCase(APITestCase):
    """Test song asset nested endpoints."""

    def setUp(self):
        """Set up test data."""
        self.marketing_dept = Department.objects.create(
            code='marketing',
            name='Marketing'
        )
        self.label_dept = Department.objects.create(
            code='label',
            name='Label'
        )

        self.marketing_role = Role.objects.create(
            code='marketing_employee',
            name='Marketing Employee',
            level=200,
            department=self.marketing_dept
        )
        self.label_role = Role.objects.create(
            code='label_employee',
            name='Label Employee',
            level=200,
            department=self.label_dept
        )

        self.marketing_user = User.objects.create_user(
            email='marketing@test.com',
            password='test123'
        )
        UserProfile.objects.create(
            user=self.marketing_user,
            role=self.marketing_role,
            department=self.marketing_dept,
            setup_completed=True
        )

        self.label_user = User.objects.create_user(
            email='label@test.com',
            password='test123'
        )
        UserProfile.objects.create(
            user=self.label_user,
            role=self.label_role,
            department=self.label_dept,
            setup_completed=True
        )

        self.song = Song.objects.create(
            title='Test Song',
            created_by=self.marketing_user,
            stage='marketing_assets'
        )

        self.client = APIClient()

    def test_create_asset(self):
        """Test creating a song asset."""
        self.client.force_authenticate(user=self.marketing_user)
        data = {
            'asset_type': 'cover_art',
            'google_drive_url': 'https://drive.google.com/file/d/abc123',
            'file_format': 'png',
            'width': 3000,
            'height': 3000
        }

        response = self.client.post(f'/api/v1/songs/{self.song.id}/assets/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['asset_type'], 'cover_art')
        self.assertEqual(response.data['review_status'], 'pending')

    def test_label_can_review_asset(self):
        """Test that Label can review Marketing assets."""
        asset = SongAsset.objects.create(
            song=self.song,
            asset_type='cover_art',
            google_drive_url='https://drive.google.com/file/d/abc123',
            uploaded_by=self.marketing_user
        )

        self.client.force_authenticate(user=self.label_user)
        data = {
            'action': 'approved',
            'notes': 'Looks great!'
        }

        response = self.client.post(f'/api/v1/songs/{self.song.id}/assets/{asset.id}/review/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['review_status'], 'approved')

        # Verify alert was created
        alert = SongAlert.objects.filter(
            song=self.song,
            alert_type='asset_approved'
        ).first()
        self.assertIsNotNone(alert)


class SongNoteAPITestCase(APITestCase):
    """Test song note endpoints."""

    def setUp(self):
        """Set up test data."""
        self.sales_dept = Department.objects.create(
            code='sales',
            name='Sales'
        )
        self.sales_role = Role.objects.create(
            code='sales_employee',
            name='Sales Employee',
            level=200,
            department=self.sales_dept
        )

        self.sales_user = User.objects.create_user(
            email='sales@test.com',
            password='test123'
        )
        UserProfile.objects.create(
            user=self.sales_user,
            role=self.sales_role,
            department=self.sales_dept,
            setup_completed=True
        )

        self.song = Song.objects.create(
            title='Test Song',
            created_by=self.sales_user,
            stage='publishing'
        )

        self.client = APIClient()

    def test_create_note(self):
        """Test creating a note."""
        self.client.force_authenticate(user=self.sales_user)
        data = {
            'note_type': 'comment',
            'content': 'This is a test note'
        }

        response = self.client.post(f'/api/v1/songs/{self.song.id}/notes/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['content'], 'This is a test note')

    def test_create_sales_pitch_note(self):
        """Test creating a sales pitch note."""
        self.client.force_authenticate(user=self.sales_user)
        data = {
            'note_type': 'sales_pitch',
            'content': 'Pitched to major artist',
            'pitched_to_artist': 'Famous Artist',
            'pitch_outcome': 'interested'
        }

        response = self.client.post(f'/api/v1/songs/{self.song.id}/notes/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['pitch_outcome'], 'interested')


class SongAlertAPITestCase(APITestCase):
    """Test song alert endpoints."""

    def setUp(self):
        """Set up test data."""
        self.digital_dept = Department.objects.create(
            code='digital',
            name='Digital'
        )
        self.digital_role = Role.objects.create(
            code='digital_employee',
            name='Digital Employee',
            level=200,
            department=self.digital_dept
        )

        self.digital_user = User.objects.create_user(
            email='digital@test.com',
            password='test123'
        )
        UserProfile.objects.create(
            user=self.digital_user,
            role=self.digital_role,
            department=self.digital_dept,
            setup_completed=True
        )

        self.song = Song.objects.create(
            title='Test Song',
            created_by=self.digital_user,
            stage='digital_distribution'
        )

        self.client = APIClient()

    def test_list_alerts(self):
        """Test listing alerts for user."""
        alert = SongAlert.objects.create(
            song=self.song,
            alert_type='stage_transition',
            target_user=self.digital_user,
            title='Test Alert',
            message='Test message',
            priority='info'
        )

        self.client.force_authenticate(user=self.digital_user)
        response = self.client.get('/api/v1/alerts/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data['results']), 0)

    def test_mark_alert_read(self):
        """Test marking alert as read."""
        alert = SongAlert.objects.create(
            song=self.song,
            alert_type='stage_transition',
            target_user=self.digital_user,
            title='Test Alert',
            message='Test message',
            priority='info'
        )

        self.client.force_authenticate(user=self.digital_user)
        response = self.client.post(f'/api/v1/alerts/{alert.id}/mark_read/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_read'])

    def test_unread_count(self):
        """Test getting unread alert count."""
        SongAlert.objects.create(
            song=self.song,
            alert_type='stage_transition',
            target_user=self.digital_user,
            title='Test Alert 1',
            message='Test message',
            priority='info',
            is_read=False
        )
        SongAlert.objects.create(
            song=self.song,
            alert_type='stage_transition',
            target_user=self.digital_user,
            title='Test Alert 2',
            message='Test message',
            priority='info',
            is_read=False
        )

        self.client.force_authenticate(user=self.digital_user)
        response = self.client.get('/api/v1/alerts/unread_count/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['unread_count'], 2)


class SongPermissionAPITestCase(APITestCase):
    """Test permission-based API access."""

    def setUp(self):
        """Set up test data."""
        self.publishing_dept = Department.objects.create(
            code='publishing',
            name='Publishing'
        )
        self.marketing_dept = Department.objects.create(
            code='marketing',
            name='Marketing'
        )

        self.publishing_role = Role.objects.create(
            code='publishing_employee',
            name='Publishing Employee',
            level=200,
            department=self.publishing_dept
        )
        self.marketing_role = Role.objects.create(
            code='marketing_employee',
            name='Marketing Employee',
            level=200,
            department=self.marketing_dept
        )

        self.publishing_user = User.objects.create_user(
            email='publishing@test.com',
            password='test123'
        )
        UserProfile.objects.create(
            user=self.publishing_user,
            role=self.publishing_role,
            department=self.publishing_dept,
            setup_completed=True
        )

        self.marketing_user = User.objects.create_user(
            email='marketing@test.com',
            password='test123'
        )
        UserProfile.objects.create(
            user=self.marketing_user,
            role=self.marketing_role,
            department=self.marketing_dept,
            setup_completed=True
        )

        self.client = APIClient()

    def test_marketing_cannot_see_publishing_songs(self):
        """Test that Marketing cannot see Publishing stage songs."""
        song = Song.objects.create(
            title='Publishing Song',
            created_by=self.publishing_user,
            stage='publishing'
        )

        self.client.force_authenticate(user=self.marketing_user)
        response = self.client.get(f'/api/v1/songs/{song.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_marketing_can_only_edit_marketing_stage(self):
        """Test that Marketing can only edit marketing_assets stage."""
        song = Song.objects.create(
            title='Marketing Song',
            created_by=self.marketing_user,
            stage='marketing_assets'
        )

        self.client.force_authenticate(user=self.marketing_user)
        data = {'title': 'Updated Title'}

        response = self.client.patch(f'/api/v1/songs/{song.id}/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
