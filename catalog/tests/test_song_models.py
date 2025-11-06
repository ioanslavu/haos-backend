"""
Tests for Song Workflow models.

Tests the following models:
- Song
- SongChecklistItem
- SongStageTransition
- SongAsset
- SongNote
- SongAlert
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from catalog.models import (
    Work, Recording, Release, Song, SongChecklistItem,
    SongStageTransition, SongAsset, SongNote, SongAlert
)
from api.models import Department, Role, UserProfile
from identity.models import Entity, Identifier
from rights.models import Split, Credit

User = get_user_model()


class SongModelTestCase(TestCase):
    """Test Song model functionality."""

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
        self.digital_dept = Department.objects.create(
            code='digital',
            name='Digital Department'
        )

        # Create roles
        self.admin_role = Role.objects.create(
            code='administrator',
            name='Administrator',
            level=1000,
            is_system_role=True
        )
        self.publishing_role = Role.objects.create(
            code='publishing_employee',
            name='Publishing Employee',
            level=200,
            department=self.publishing_dept
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

        # Create artist entity
        self.artist = Entity.objects.create(
            kind='PF',
            display_name='Test Artist',
            created_by=self.admin_user
        )

        # Create work and recording
        self.work = Work.objects.create(
            title='Test Work',
            year_composed=2024
        )
        self.recording = Recording.objects.create(
            title='Test Recording',
            work=self.work,
            type='audio_master',
            status='ready',
            duration_seconds=180
        )

    def test_song_creation(self):
        """Test creating a song."""
        song = Song.objects.create(
            title='Test Song',
            artist=self.artist,
            genre='Pop',
            language='en',
            created_by=self.publishing_user,
            stage='draft'
        )

        self.assertEqual(song.title, 'Test Song')
        self.assertEqual(song.stage, 'draft')
        self.assertEqual(song.created_by, self.publishing_user)
        self.assertIsNotNone(song.created_at)

    def test_song_str_representation(self):
        """Test song string representation."""
        song = Song.objects.create(
            title='Test Song',
            created_by=self.publishing_user,
            stage='publishing'
        )
        self.assertEqual(str(song), 'Test Song - Publishing')

    def test_calculate_checklist_progress(self):
        """Test checklist progress calculation."""
        song = Song.objects.create(
            title='Test Song',
            created_by=self.publishing_user,
            stage='publishing'
        )

        # Create checklist items
        item1 = SongChecklistItem.objects.create(
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
        item2 = SongChecklistItem.objects.create(
            song=song,
            stage='publishing',
            category='Work Setup',
            item_name='ISWC assigned',
            description='Assign ISWC',
            required=True,
            validation_type='manual',
            is_complete=False,
            order=2
        )
        item3 = SongChecklistItem.objects.create(
            song=song,
            stage='publishing',
            category='Optional',
            item_name='Optional task',
            description='Optional',
            required=False,  # Not required
            validation_type='manual',
            is_complete=False,
            order=3
        )

        # Should be 50% (1 of 2 required items complete)
        progress = song.calculate_checklist_progress()
        self.assertEqual(progress, 50.0)

    def test_calculate_checklist_progress_no_items(self):
        """Test checklist progress when no items exist."""
        song = Song.objects.create(
            title='Test Song',
            created_by=self.publishing_user,
            stage='draft'
        )

        # No checklist items = 100% complete
        progress = song.calculate_checklist_progress()
        self.assertEqual(progress, 100.0)

    def test_can_transition_to_valid(self):
        """Test valid stage transition."""
        song = Song.objects.create(
            title='Test Song',
            created_by=self.publishing_user,
            stage='publishing'
        )

        # Create complete checklist
        item = SongChecklistItem.objects.create(
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

        # Admin can transition
        can_transition, reason = song.can_transition_to('label_recording', self.admin_user)
        self.assertTrue(can_transition)
        self.assertEqual(reason, 'Admin override')

    def test_can_transition_to_invalid_checklist_incomplete(self):
        """Test transition fails when checklist incomplete."""
        song = Song.objects.create(
            title='Test Song',
            created_by=self.publishing_user,
            stage='publishing'
        )

        # Create incomplete checklist
        item = SongChecklistItem.objects.create(
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

        # Non-admin cannot transition with incomplete checklist
        can_transition, reason = song.can_transition_to('label_recording', self.publishing_user)
        self.assertFalse(can_transition)
        self.assertIn('Checklist incomplete', reason)

    def test_can_transition_to_invalid_stage(self):
        """Test transition fails for invalid stage."""
        song = Song.objects.create(
            title='Test Song',
            created_by=self.publishing_user,
            stage='draft'
        )

        # Cannot jump from draft to label_recording (must go through publishing)
        can_transition, reason = song.can_transition_to('label_recording', self.admin_user)
        self.assertFalse(can_transition)
        self.assertIn('Cannot transition', reason)

    def test_update_computed_fields(self):
        """Test updating computed fields."""
        song = Song.objects.create(
            title='Test Song',
            created_by=self.publishing_user,
            stage='publishing',
            stage_deadline=timezone.now().date() - timedelta(days=1),  # Overdue
            stage_entered_at=timezone.now() - timedelta(days=5)
        )

        # Create checklist
        item = SongChecklistItem.objects.create(
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

        song.update_computed_fields()
        song.refresh_from_db()

        self.assertEqual(song.checklist_progress, 100.0)
        self.assertTrue(song.is_overdue)
        self.assertEqual(song.days_in_current_stage, 5)

    def test_is_overdue_calculation(self):
        """Test is_overdue field calculation."""
        # Song with past deadline
        song_overdue = Song.objects.create(
            title='Overdue Song',
            created_by=self.publishing_user,
            stage='publishing',
            stage_deadline=timezone.now().date() - timedelta(days=1)
        )
        song_overdue.update_computed_fields()
        song_overdue.refresh_from_db()
        self.assertTrue(song_overdue.is_overdue)

        # Song with future deadline
        song_on_time = Song.objects.create(
            title='On Time Song',
            created_by=self.publishing_user,
            stage='publishing',
            stage_deadline=timezone.now().date() + timedelta(days=7)
        )
        song_on_time.update_computed_fields()
        song_on_time.refresh_from_db()
        self.assertFalse(song_on_time.is_overdue)

        # Song with no deadline
        song_no_deadline = Song.objects.create(
            title='No Deadline Song',
            created_by=self.publishing_user,
            stage='publishing'
        )
        song_no_deadline.update_computed_fields()
        song_no_deadline.refresh_from_db()
        self.assertFalse(song_no_deadline.is_overdue)

    def test_days_in_current_stage_calculation(self):
        """Test days_in_current_stage calculation."""
        stage_entered = timezone.now() - timedelta(days=10)
        song = Song.objects.create(
            title='Test Song',
            created_by=self.publishing_user,
            stage='publishing',
            stage_entered_at=stage_entered
        )

        song.update_computed_fields()
        song.refresh_from_db()

        self.assertEqual(song.days_in_current_stage, 10)


class SongChecklistItemModelTestCase(TestCase):
    """Test SongChecklistItem model."""

    def setUp(self):
        """Set up test data."""
        self.admin_role = Role.objects.create(
            code='administrator',
            name='Administrator',
            level=1000
        )
        self.user = User.objects.create_user(
            email='user@test.com',
            password='test123'
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

        self.work = Work.objects.create(
            title='Test Work'
        )
        self.recording = Recording.objects.create(
            title='Test Recording',
            work=self.work
        )

    def test_checklist_item_creation(self):
        """Test creating a checklist item."""
        item = SongChecklistItem.objects.create(
            song=self.song,
            stage='publishing',
            category='Work Setup',
            item_name='Work created',
            description='Create a work entity',
            required=True,
            validation_type='manual',
            order=1
        )

        self.assertEqual(item.song, self.song)
        self.assertEqual(item.stage, 'publishing')
        self.assertFalse(item.is_complete)

    def test_manual_completion(self):
        """Test manually completing a checklist item."""
        item = SongChecklistItem.objects.create(
            song=self.song,
            stage='publishing',
            category='Work Setup',
            item_name='Work created',
            description='Create a work entity',
            required=True,
            validation_type='manual',
            order=1
        )

        # Complete the item
        item.is_complete = True
        item.completed_by = self.user
        item.completed_at = timezone.now()
        item.save()

        self.assertTrue(item.is_complete)
        self.assertEqual(item.completed_by, self.user)
        self.assertIsNotNone(item.completed_at)

    def test_validate_manual(self):
        """Test validation for manual checklist item."""
        item = SongChecklistItem.objects.create(
            song=self.song,
            stage='publishing',
            category='Work Setup',
            item_name='Work created',
            description='Create a work entity',
            required=True,
            validation_type='manual',
            is_complete=True,
            order=1
        )

        self.assertTrue(item.validate())

        item.is_complete = False
        self.assertFalse(item.validate())

    def test_validate_auto_entity_exists_work(self):
        """Test auto validation for entity existence (Work)."""
        item = SongChecklistItem.objects.create(
            song=self.song,
            stage='publishing',
            category='Work Setup',
            item_name='Work created',
            description='Create a work entity',
            required=True,
            validation_type='auto_entity_exists',
            validation_rule={'entity': 'work'},
            order=1
        )

        # No work linked
        self.assertFalse(item.validate())

        # Link work
        self.song.work = self.work
        self.song.save()

        self.assertTrue(item.validate())

    def test_validate_auto_entity_exists_recording(self):
        """Test auto validation for entity existence (Recording)."""
        item = SongChecklistItem.objects.create(
            song=self.song,
            stage='label_recording',
            category='Recording Setup',
            item_name='Recording created',
            description='Create a recording entity',
            required=True,
            validation_type='auto_entity_exists',
            validation_rule={'entity': 'recording'},
            order=1
        )

        # No recordings linked
        self.assertFalse(item.validate())

        # Link recording
        self.song.recordings.add(self.recording)

        self.assertTrue(item.validate())

    def test_validate_auto_field_exists(self):
        """Test auto validation for field existence."""
        self.song.work = self.work
        self.song.save()

        # Create ISWC identifier
        Identifier.objects.create(
            scheme='ISWC',
            value='T-123.456.789-0',
            owner_type='work',
            owner_id=self.work.id
        )

        item = SongChecklistItem.objects.create(
            song=self.song,
            stage='publishing',
            category='Work Setup',
            item_name='ISWC assigned',
            description='Assign ISWC to work',
            required=True,
            validation_type='auto_field_exists',
            validation_rule={'entity': 'work', 'field': 'iswc'},
            order=1
        )

        # ISWC exists via get_iswc() method
        self.assertTrue(item.validate())

    def test_validate_auto_split_validated(self):
        """Test auto validation for splits = 100%."""
        self.song.work = self.work
        self.song.save()

        # Create writer entity
        writer_entity = Entity.objects.create(
            kind='PF',
            display_name='Test Writer',
            created_by=self.user
        )

        # Create 100% writer split
        Split.objects.create(
            scope='work',
            object_id=self.work.id,
            entity=writer_entity,
            right_type='writer',
            share=Decimal('100.00')
        )

        item = SongChecklistItem.objects.create(
            song=self.song,
            stage='publishing',
            category='Writer Splits',
            item_name='Writer splits = 100%',
            description='All writer splits must equal 100%',
            required=True,
            validation_type='auto_split_validated',
            validation_rule={'entity': 'work', 'split_type': 'writer'},
            order=1
        )

        self.assertTrue(item.validate())

    def test_validate_auto_count_minimum(self):
        """Test auto validation for minimum count."""
        self.song.work = self.work
        self.song.save()

        # Create writer entity
        writer_entity = Entity.objects.create(
            kind='PF',
            display_name='Test Writer',
            created_by=self.user
        )

        # Create writer split
        Split.objects.create(
            scope='work',
            object_id=self.work.id,
            entity=writer_entity,
            right_type='writer',
            share=Decimal('100.00')
        )

        item = SongChecklistItem.objects.create(
            song=self.song,
            stage='publishing',
            category='Writer Splits',
            item_name='At least 1 writer',
            description='Work must have at least 1 writer',
            required=True,
            validation_type='auto_count_minimum',
            validation_rule={'entity': 'work_writers', 'min_count': 1},
            order=1
        )

        self.assertTrue(item.validate())


class SongStageTransitionModelTestCase(TestCase):
    """Test SongStageTransition audit log model."""

    def setUp(self):
        """Set up test data."""
        self.admin_role = Role.objects.create(
            code='administrator',
            name='Administrator',
            level=1000
        )
        self.user = User.objects.create_user(
            email='user@test.com',
            password='test123'
        )
        UserProfile.objects.create(
            user=self.user,
            role=self.admin_role,
            setup_completed=True
        )

        self.song = Song.objects.create(
            title='Test Song',
            created_by=self.user,
            stage='draft'
        )

    def test_transition_creation(self):
        """Test creating a stage transition record."""
        transition = SongStageTransition.objects.create(
            song=self.song,
            from_stage='draft',
            to_stage='publishing',
            transitioned_by=self.user,
            transition_type='forward',
            notes='Moving to publishing',
            checklist_completion_at_transition=100.0
        )

        self.assertEqual(transition.song, self.song)
        self.assertEqual(transition.from_stage, 'draft')
        self.assertEqual(transition.to_stage, 'publishing')
        self.assertEqual(transition.transitioned_by, self.user)
        self.assertIsNotNone(transition.transitioned_at)

    def test_transition_str_representation(self):
        """Test transition string representation."""
        transition = SongStageTransition.objects.create(
            song=self.song,
            from_stage='draft',
            to_stage='publishing',
            transitioned_by=self.user,
            checklist_completion_at_transition=100.0
        )

        self.assertEqual(str(transition), 'Test Song - draft → publishing')

    def test_transition_history(self):
        """Test tracking transition history."""
        # Create multiple transitions
        SongStageTransition.objects.create(
            song=self.song,
            from_stage='draft',
            to_stage='publishing',
            transitioned_by=self.user,
            checklist_completion_at_transition=100.0
        )
        SongStageTransition.objects.create(
            song=self.song,
            from_stage='publishing',
            to_stage='label_recording',
            transitioned_by=self.user,
            checklist_completion_at_transition=100.0
        )

        history = self.song.stage_transitions.all()
        self.assertEqual(history.count(), 2)
        self.assertEqual(history[0].to_stage, 'label_recording')  # Most recent first


class SongAssetModelTestCase(TestCase):
    """Test SongAsset model."""

    def setUp(self):
        """Set up test data."""
        self.admin_role = Role.objects.create(
            code='administrator',
            name='Administrator',
            level=1000
        )
        self.user = User.objects.create_user(
            email='user@test.com',
            password='test123'
        )
        UserProfile.objects.create(
            user=self.user,
            role=self.admin_role,
            setup_completed=True
        )

        self.song = Song.objects.create(
            title='Test Song',
            created_by=self.user,
            stage='marketing_assets'
        )

    def test_asset_creation(self):
        """Test creating a song asset."""
        asset = SongAsset.objects.create(
            song=self.song,
            asset_type='cover_art',
            google_drive_url='https://drive.google.com/file/d/abc123',
            file_format='png',
            width=3000,
            height=3000,
            uploaded_by=self.user
        )

        self.assertEqual(asset.song, self.song)
        self.assertEqual(asset.asset_type, 'cover_art')
        self.assertEqual(asset.review_status, 'pending')
        self.assertIsNotNone(asset.uploaded_at)

    def test_asset_review_status_change(self):
        """Test changing asset review status."""
        asset = SongAsset.objects.create(
            song=self.song,
            asset_type='cover_art',
            google_drive_url='https://drive.google.com/file/d/abc123',
            uploaded_by=self.user
        )

        # Approve asset
        asset.review_status = 'approved'
        asset.reviewed_by = self.user
        asset.reviewed_at = timezone.now()
        asset.review_notes = 'Looks great!'
        asset.save()

        self.assertEqual(asset.review_status, 'approved')
        self.assertEqual(asset.reviewed_by, self.user)
        self.assertIsNotNone(asset.reviewed_at)

    def test_dimensions_property(self):
        """Test dimensions property."""
        asset = SongAsset.objects.create(
            song=self.song,
            asset_type='cover_art',
            google_drive_url='https://drive.google.com/file/d/abc123',
            width=3000,
            height=3000,
            uploaded_by=self.user
        )

        self.assertEqual(asset.dimensions, '3000x3000')

        # Asset without dimensions
        asset_no_dims = SongAsset.objects.create(
            song=self.song,
            asset_type='press_photo',
            google_drive_url='https://drive.google.com/file/d/xyz789',
            uploaded_by=self.user
        )

        self.assertIsNone(asset_no_dims.dimensions)


class SongNoteModelTestCase(TestCase):
    """Test SongNote model."""

    def setUp(self):
        """Set up test data."""
        self.admin_role = Role.objects.create(
            code='administrator',
            name='Administrator',
            level=1000
        )
        self.user = User.objects.create_user(
            email='user@test.com',
            password='test123'
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

    def test_note_creation(self):
        """Test creating a song note."""
        note = SongNote.objects.create(
            song=self.song,
            author=self.user,
            note_type='comment',
            content='This is a test note'
        )

        self.assertEqual(note.song, self.song)
        self.assertEqual(note.author, self.user)
        self.assertEqual(note.note_type, 'comment')
        self.assertIsNotNone(note.created_at)

    def test_sales_pitch_note(self):
        """Test creating a sales pitch note."""
        note = SongNote.objects.create(
            song=self.song,
            author=self.user,
            note_type='sales_pitch',
            content='Pitched to major artist',
            pitched_to_artist='Famous Artist',
            pitch_outcome='interested'
        )

        self.assertEqual(note.note_type, 'sales_pitch')
        self.assertEqual(note.pitched_to_artist, 'Famous Artist')
        self.assertEqual(note.pitch_outcome, 'interested')


class SongAlertModelTestCase(TestCase):
    """Test SongAlert model."""

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
        self.user = User.objects.create_user(
            email='user@test.com',
            password='test123'
        )
        UserProfile.objects.create(
            user=self.user,
            role=self.admin_role,
            department=self.digital_dept,
            setup_completed=True
        )

        self.song = Song.objects.create(
            title='Test Song',
            created_by=self.user,
            stage='digital_distribution'
        )

    def test_alert_creation(self):
        """Test creating an alert."""
        alert = SongAlert.objects.create(
            song=self.song,
            alert_type='stage_transition',
            target_department=self.digital_dept,
            title='New Song in Digital Queue',
            message='Test Song has been moved to Digital Distribution',
            action_url=f'/songs/{self.song.id}/',
            action_label='View Song',
            priority='important'
        )

        self.assertEqual(alert.song, self.song)
        self.assertEqual(alert.target_department, self.digital_dept)
        self.assertFalse(alert.is_read)
        self.assertIsNotNone(alert.created_at)

    def test_alert_mark_read(self):
        """Test marking an alert as read."""
        alert = SongAlert.objects.create(
            song=self.song,
            alert_type='stage_transition',
            target_user=self.user,
            title='Test Alert',
            message='Test message',
            priority='info'
        )

        alert.is_read = True
        alert.read_at = timezone.now()
        alert.save()

        self.assertTrue(alert.is_read)
        self.assertIsNotNone(alert.read_at)
