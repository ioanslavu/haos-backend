"""
Tests for alert service.

Tests alert generation from alert_service.py:
- create_stage_transition_alert() creates alert for target dept
- create_send_to_digital_alert() creates URGENT alert
- create_asset_submitted_alert() notifies Label
- create_asset_reviewed_alert() notifies Marketing
- Alert priorities are correct (info, important, urgent)
"""

from django.test import TestCase
from django.contrib.auth import get_user_model

from catalog.models import Song, SongAsset, SongAlert
from catalog.alert_service import SongAlertService
from api.models import Department, Role, UserProfile
from identity.models import Entity

User = get_user_model()


class StageTransitionAlertTestCase(TestCase):
    """Test create_stage_transition_alert() function."""

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

        # Create roles
        self.publishing_role = Role.objects.create(
            code='publishing_employee',
            name='Publishing Employee',
            level=200,
            department=self.publishing_dept
        )

        # Create user
        self.user = User.objects.create_user(
            email='user@test.com',
            password='test123',
            first_name='Test',
            last_name='User'
        )
        UserProfile.objects.create(
            user=self.user,
            role=self.publishing_role,
            department=self.publishing_dept,
            setup_completed=True
        )

        self.song = Song.objects.create(
            title='Test Song',
            created_by=self.user,
            stage='publishing'
        )

    def test_create_stage_transition_alert(self):
        """Test creating stage transition alert."""
        alert = SongAlertService.create_stage_transition_alert(
            self.song,
            from_stage='publishing',
            to_stage='label_recording',
            user=self.user
        )

        self.assertIsNotNone(alert)
        self.assertEqual(alert.song, self.song)
        self.assertEqual(alert.alert_type, 'stage_transition')
        self.assertEqual(alert.target_department, self.label_dept)
        self.assertEqual(alert.priority, 'important')
        self.assertIn(self.song.title, alert.title)

    def test_alert_includes_user_info(self):
        """Test that alert includes user who triggered transition."""
        alert = SongAlertService.create_stage_transition_alert(
            self.song,
            from_stage='publishing',
            to_stage='label_recording',
            user=self.user
        )

        self.assertIn('Test User', alert.message)

    def test_alert_for_stage_with_no_department(self):
        """Test alert creation for stage with no assigned department."""
        alert = SongAlertService.create_stage_transition_alert(
            self.song,
            from_stage='label_recording',
            to_stage='released',
            user=self.user
        )

        # Released stage has no department, so no alert created
        self.assertIsNone(alert)

    def test_alert_for_assigned_user(self):
        """Test that alert is also created for assigned user."""
        assigned_user = User.objects.create_user(
            email='assigned@test.com',
            password='test123',
            first_name='Assigned',
            last_name='User'
        )
        UserProfile.objects.create(
            user=assigned_user,
            role=self.publishing_role,
            department=self.publishing_dept,
            setup_completed=True
        )

        self.song.assigned_user = assigned_user
        self.song.save()

        SongAlertService.create_stage_transition_alert(
            self.song,
            from_stage='publishing',
            to_stage='label_recording',
            user=self.user
        )

        # Should create two alerts: one for department, one for assigned user
        alerts = SongAlert.objects.filter(song=self.song)
        self.assertEqual(alerts.count(), 2)

        # Check that one alert is for the assigned user
        user_alert = alerts.filter(target_user=assigned_user).first()
        self.assertIsNotNone(user_alert)
        self.assertEqual(user_alert.alert_type, 'assignment')


class SendToDigitalAlertTestCase(TestCase):
    """Test create_send_to_digital_alert() function."""

    def setUp(self):
        """Set up test data."""
        self.digital_dept = Department.objects.create(
            code='digital',
            name='Digital Department'
        )
        self.label_dept = Department.objects.create(
            code='label',
            name='Label Department'
        )

        self.label_role = Role.objects.create(
            code='label_employee',
            name='Label Employee',
            level=200,
            department=self.label_dept
        )

        self.user = User.objects.create_user(
            email='user@test.com',
            password='test123',
            first_name='Label',
            last_name='User'
        )
        UserProfile.objects.create(
            user=self.user,
            role=self.label_role,
            department=self.label_dept,
            setup_completed=True
        )

        self.song = Song.objects.create(
            title='Test Song',
            created_by=self.user,
            stage='ready_for_digital'
        )

    def test_create_urgent_alert(self):
        """Test that send_to_digital creates URGENT alert."""
        alert = SongAlertService.create_send_to_digital_alert(
            self.song,
            self.user
        )

        self.assertIsNotNone(alert)
        self.assertEqual(alert.priority, 'urgent')
        self.assertEqual(alert.alert_type, 'sent_to_digital')
        self.assertEqual(alert.target_department, self.digital_dept)

    def test_alert_message_includes_user(self):
        """Test that alert message includes user who sent to digital."""
        alert = SongAlertService.create_send_to_digital_alert(
            self.song,
            self.user
        )

        self.assertIn('Label User', alert.message)
        self.assertIn('Label', alert.message)

    def test_alert_action_url(self):
        """Test that alert has correct action URL."""
        alert = SongAlertService.create_send_to_digital_alert(
            self.song,
            self.user
        )

        self.assertIn(str(self.song.id), alert.action_url)
        self.assertEqual(alert.action_label, 'Create Release')


class AssetSubmittedAlertTestCase(TestCase):
    """Test create_asset_submitted_alert() function."""

    def setUp(self):
        """Set up test data."""
        self.label_dept = Department.objects.create(
            code='label',
            name='Label Department'
        )
        self.marketing_dept = Department.objects.create(
            code='marketing',
            name='Marketing Department'
        )

        self.marketing_role = Role.objects.create(
            code='marketing_employee',
            name='Marketing Employee',
            level=200,
            department=self.marketing_dept
        )

        self.user = User.objects.create_user(
            email='user@test.com',
            password='test123',
            first_name='Marketing',
            last_name='User'
        )
        UserProfile.objects.create(
            user=self.user,
            role=self.marketing_role,
            department=self.marketing_dept,
            setup_completed=True
        )

        self.song = Song.objects.create(
            title='Test Song',
            created_by=self.user,
            stage='marketing_assets'
        )

    def test_create_asset_submitted_alert(self):
        """Test creating asset submitted alert."""
        alert = SongAlertService.create_asset_submitted_alert(
            self.song,
            self.user
        )

        self.assertIsNotNone(alert)
        self.assertEqual(alert.alert_type, 'asset_submitted')
        self.assertEqual(alert.target_department, self.label_dept)
        self.assertEqual(alert.priority, 'important')

    def test_alert_targets_label_department(self):
        """Test that alert targets Label department."""
        alert = SongAlertService.create_asset_submitted_alert(
            self.song,
            self.user
        )

        self.assertEqual(alert.target_department, self.label_dept)
        self.assertIn('review', alert.message.lower())


class AssetReviewedAlertTestCase(TestCase):
    """Test create_asset_reviewed_alert() function."""

    def setUp(self):
        """Set up test data."""
        self.label_dept = Department.objects.create(
            code='label',
            name='Label Department'
        )
        self.marketing_dept = Department.objects.create(
            code='marketing',
            name='Marketing Department'
        )

        self.label_role = Role.objects.create(
            code='label_employee',
            name='Label Employee',
            level=200,
            department=self.label_dept
        )

        self.label_user = User.objects.create_user(
            email='label@test.com',
            password='test123',
            first_name='Label',
            last_name='User'
        )
        UserProfile.objects.create(
            user=self.label_user,
            role=self.label_role,
            department=self.label_dept,
            setup_completed=True
        )

        self.marketing_user = User.objects.create_user(
            email='marketing@test.com',
            password='test123',
            first_name='Marketing',
            last_name='User'
        )

        self.song = Song.objects.create(
            title='Test Song',
            created_by=self.marketing_user,
            stage='marketing_assets'
        )

        self.asset = SongAsset.objects.create(
            song=self.song,
            asset_type='cover_art',
            google_drive_url='https://drive.google.com/file/d/abc123',
            title='Cover Art',
            uploaded_by=self.marketing_user
        )

    def test_create_asset_approved_alert(self):
        """Test creating asset approved alert."""
        alert = SongAlertService.create_asset_reviewed_alert(
            self.song,
            self.asset,
            'approved',
            self.label_user
        )

        self.assertIsNotNone(alert)
        self.assertEqual(alert.alert_type, 'asset_approved')
        self.assertEqual(alert.target_department, self.marketing_dept)
        self.assertEqual(alert.priority, 'info')
        self.assertIn('approved', alert.message)

    def test_create_asset_rejected_alert(self):
        """Test creating asset rejected alert."""
        alert = SongAlertService.create_asset_reviewed_alert(
            self.song,
            self.asset,
            'rejected',
            self.label_user
        )

        self.assertIsNotNone(alert)
        self.assertEqual(alert.alert_type, 'asset_rejected')
        self.assertEqual(alert.priority, 'important')
        self.assertIn('rejected', alert.message)

    def test_create_asset_revision_requested_alert(self):
        """Test creating asset revision requested alert."""
        alert = SongAlertService.create_asset_reviewed_alert(
            self.song,
            self.asset,
            'revision_requested',
            self.label_user
        )

        self.assertIsNotNone(alert)
        self.assertEqual(alert.alert_type, 'asset_rejected')
        self.assertEqual(alert.priority, 'important')
        self.assertIn('requested revisions', alert.message)

    def test_alert_includes_reviewer_name(self):
        """Test that alert includes reviewer's name."""
        alert = SongAlertService.create_asset_reviewed_alert(
            self.song,
            self.asset,
            'approved',
            self.label_user
        )

        self.assertIn('Label User', alert.message)


class SalesPitchAlertTestCase(TestCase):
    """Test create_sales_pitch_alert() function."""

    def setUp(self):
        """Set up test data."""
        self.sales_dept = Department.objects.create(
            code='sales',
            name='Sales Department'
        )
        self.publishing_dept = Department.objects.create(
            code='publishing',
            name='Publishing Department'
        )

        self.sales_role = Role.objects.create(
            code='sales_employee',
            name='Sales Employee',
            level=200,
            department=self.sales_dept
        )
        self.publishing_role = Role.objects.create(
            code='publishing_employee',
            name='Publishing Employee',
            level=200,
            department=self.publishing_dept
        )

        self.sales_user = User.objects.create_user(
            email='sales@test.com',
            password='test123',
            first_name='Sales',
            last_name='User'
        )
        UserProfile.objects.create(
            user=self.sales_user,
            role=self.sales_role,
            department=self.sales_dept,
            setup_completed=True
        )

        self.creator_user = User.objects.create_user(
            email='creator@test.com',
            password='test123',
            first_name='Creator',
            last_name='User'
        )
        UserProfile.objects.create(
            user=self.creator_user,
            role=self.publishing_role,
            department=self.publishing_dept,
            setup_completed=True
        )

        self.song = Song.objects.create(
            title='Test Song',
            created_by=self.creator_user,
            stage='publishing'
        )

    def test_create_sales_pitch_alert(self):
        """Test creating sales pitch alert."""
        alert = SongAlertService.create_sales_pitch_alert(
            self.song,
            self.sales_user,
            'Famous Artist'
        )

        self.assertIsNotNone(alert)
        self.assertEqual(alert.target_user, self.creator_user)
        self.assertEqual(alert.priority, 'info')
        self.assertIn('pitched', alert.message.lower())
        self.assertIn('Famous Artist', alert.message)

    def test_alert_notifies_creator(self):
        """Test that alert notifies song creator."""
        alert = SongAlertService.create_sales_pitch_alert(
            self.song,
            self.sales_user,
            'Famous Artist'
        )

        self.assertEqual(alert.target_user, self.creator_user)

    def test_no_alert_if_no_creator(self):
        """Test that no alert is created if song has no creator."""
        song_no_creator = Song.objects.create(
            title='No Creator Song',
            created_by=None,
            stage='publishing'
        )

        alert = SongAlertService.create_sales_pitch_alert(
            song_no_creator,
            self.sales_user,
            'Famous Artist'
        )

        self.assertIsNone(alert)


class AlertPriorityTestCase(TestCase):
    """Test that alerts have correct priorities."""

    def setUp(self):
        """Set up test data."""
        self.digital_dept = Department.objects.create(
            code='digital',
            name='Digital Department'
        )
        self.label_dept = Department.objects.create(
            code='label',
            name='Label Department'
        )
        self.marketing_dept = Department.objects.create(
            code='marketing',
            name='Marketing Department'
        )

        self.admin_role = Role.objects.create(
            code='administrator',
            name='Administrator',
            level=1000
        )

        self.user = User.objects.create_user(
            email='user@test.com',
            password='test123',
            first_name='Test',
            last_name='User'
        )
        UserProfile.objects.create(
            user=self.user,
            role=self.admin_role,
            setup_completed=True
        )

        self.song = Song.objects.create(
            title='Test Song',
            created_by=self.user,
            stage='publishing'
        )

        self.asset = SongAsset.objects.create(
            song=self.song,
            asset_type='cover_art',
            google_drive_url='https://drive.google.com/file/d/abc123',
            uploaded_by=self.user
        )

    def test_stage_transition_is_important(self):
        """Test that stage transition alerts are 'important'."""
        alert = SongAlertService.create_stage_transition_alert(
            self.song,
            from_stage='publishing',
            to_stage='label_recording',
            user=self.user
        )

        self.assertEqual(alert.priority, 'important')

    def test_send_to_digital_is_urgent(self):
        """Test that send_to_digital alerts are 'urgent'."""
        alert = SongAlertService.create_send_to_digital_alert(
            self.song,
            self.user
        )

        self.assertEqual(alert.priority, 'urgent')

    def test_asset_submitted_is_important(self):
        """Test that asset submitted alerts are 'important'."""
        alert = SongAlertService.create_asset_submitted_alert(
            self.song,
            self.user
        )

        self.assertEqual(alert.priority, 'important')

    def test_asset_approved_is_info(self):
        """Test that asset approved alerts are 'info'."""
        alert = SongAlertService.create_asset_reviewed_alert(
            self.song,
            self.asset,
            'approved',
            self.user
        )

        self.assertEqual(alert.priority, 'info')

    def test_asset_rejected_is_important(self):
        """Test that asset rejected alerts are 'important'."""
        alert = SongAlertService.create_asset_reviewed_alert(
            self.song,
            self.asset,
            'rejected',
            self.user
        )

        self.assertEqual(alert.priority, 'important')

    def test_sales_pitch_is_info(self):
        """Test that sales pitch alerts are 'info'."""
        alert = SongAlertService.create_sales_pitch_alert(
            self.song,
            self.user,
            'Famous Artist'
        )

        self.assertEqual(alert.priority, 'info')
