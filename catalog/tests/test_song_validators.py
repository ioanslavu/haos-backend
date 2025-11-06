"""
Tests for Song Workflow validators.

Tests validation functions from validators.py:
- validate_auto_entity_exists()
- validate_auto_field_exists()
- validate_auto_split_validated()
- validate_auto_count_minimum()
- run_validation()
- revalidate_song_checklist()
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal

from catalog.models import Work, Recording, Release, Song, SongChecklistItem
from catalog import validators
from api.models import Department, Role, UserProfile
from identity.models import Entity, Identifier
from rights.models import Split, Credit

User = get_user_model()


class ValidateAutoEntityExistsTestCase(TestCase):
    """Test validate_auto_entity_exists() function."""

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
        self.release = Release.objects.create(
            title='Test Release',
            type='single'
        )

    def test_work_exists(self):
        """Test validation when work exists."""
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

        # No work linked
        result = validators.validate_auto_entity_exists(item)
        self.assertFalse(result)

        # Link work
        self.song.work = self.work
        self.song.save()

        result = validators.validate_auto_entity_exists(item)
        self.assertTrue(result)

    def test_recording_exists(self):
        """Test validation when recording exists."""
        item = SongChecklistItem.objects.create(
            song=self.song,
            stage='label_recording',
            category='Recording Setup',
            item_name='Recording created',
            description='Create recording',
            required=True,
            validation_type='auto_entity_exists',
            validation_rule={'entity': 'recording'},
            order=1
        )

        # No recordings linked
        result = validators.validate_auto_entity_exists(item)
        self.assertFalse(result)

        # Link recording
        self.song.recordings.add(self.recording)

        result = validators.validate_auto_entity_exists(item)
        self.assertTrue(result)

    def test_release_exists(self):
        """Test validation when release exists."""
        item = SongChecklistItem.objects.create(
            song=self.song,
            stage='digital_distribution',
            category='Release Setup',
            item_name='Release created',
            description='Create release',
            required=True,
            validation_type='auto_entity_exists',
            validation_rule={'entity': 'release'},
            order=1
        )

        # No releases linked
        result = validators.validate_auto_entity_exists(item)
        self.assertFalse(result)

        # Link release
        self.song.releases.add(self.release)

        result = validators.validate_auto_entity_exists(item)
        self.assertTrue(result)


class ValidateAutoFieldExistsTestCase(TestCase):
    """Test validate_auto_field_exists() function."""

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

        self.work = Work.objects.create(
            title='Test Work'
        )

        self.song = Song.objects.create(
            title='Test Song',
            created_by=self.user,
            stage='publishing',
            work=self.work
        )

    def test_iswc_field_exists(self):
        """Test ISWC field validation."""
        item = SongChecklistItem.objects.create(
            song=self.song,
            stage='publishing',
            category='Work Setup',
            item_name='ISWC assigned',
            description='Assign ISWC',
            required=True,
            validation_type='auto_field_exists',
            validation_rule={'entity': 'work', 'field': 'iswc'},
            order=1
        )

        # No ISWC
        result = validators.validate_auto_field_exists(item)
        self.assertFalse(result)

        # Create ISWC
        Identifier.objects.create(
            scheme='ISWC',
            value='T-123.456.789-0',
            owner_type='work',
            owner_id=self.work.id
        )

        result = validators.validate_auto_field_exists(item)
        self.assertTrue(result)

    def test_regular_field_exists(self):
        """Test regular field validation."""
        item = SongChecklistItem.objects.create(
            song=self.song,
            stage='publishing',
            category='Work Setup',
            item_name='Genre set',
            description='Set genre',
            required=True,
            validation_type='auto_field_exists',
            validation_rule={'entity': 'work', 'field': 'genre'},
            order=1
        )

        # No genre
        result = validators.validate_auto_field_exists(item)
        self.assertFalse(result)

        # Set genre
        self.work.genre = 'Pop'
        self.work.save()

        result = validators.validate_auto_field_exists(item)
        self.assertTrue(result)

    def test_missing_entity(self):
        """Test validation when entity doesn't exist."""
        self.song.work = None
        self.song.save()

        item = SongChecklistItem.objects.create(
            song=self.song,
            stage='publishing',
            category='Work Setup',
            item_name='ISWC assigned',
            description='Assign ISWC',
            required=True,
            validation_type='auto_field_exists',
            validation_rule={'entity': 'work', 'field': 'iswc'},
            order=1
        )

        result = validators.validate_auto_field_exists(item)
        self.assertFalse(result)


class ValidateAutoSplitValidatedTestCase(TestCase):
    """Test validate_auto_split_validated() function."""

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

        self.work = Work.objects.create(
            title='Test Work'
        )

        self.song = Song.objects.create(
            title='Test Song',
            created_by=self.user,
            stage='publishing',
            work=self.work
        )

        self.writer = Entity.objects.create(
            kind='PF',
            display_name='Test Writer',
            created_by=self.user
        )

    def test_splits_equal_100_percent(self):
        """Test validation when splits = 100%."""
        item = SongChecklistItem.objects.create(
            song=self.song,
            stage='publishing',
            category='Writer Splits',
            item_name='Writer splits = 100%',
            description='Splits must equal 100%',
            required=True,
            validation_type='auto_split_validated',
            validation_rule={'entity': 'work', 'split_type': 'writer'},
            order=1
        )

        # No splits
        result = validators.validate_auto_split_validated(item)
        self.assertFalse(result)

        # Create 100% split
        Split.objects.create(
            scope='work',
            object_id=self.work.id,
            entity=self.writer,
            right_type='writer',
            share=Decimal('100.00')
        )

        result = validators.validate_auto_split_validated(item)
        self.assertTrue(result)

    def test_splits_not_equal_100_percent(self):
        """Test validation fails when splits != 100%."""
        item = SongChecklistItem.objects.create(
            song=self.song,
            stage='publishing',
            category='Writer Splits',
            item_name='Writer splits = 100%',
            description='Splits must equal 100%',
            required=True,
            validation_type='auto_split_validated',
            validation_rule={'entity': 'work', 'split_type': 'writer'},
            order=1
        )

        # Create 99% split (invalid)
        Split.objects.create(
            scope='work',
            object_id=self.work.id,
            entity=self.writer,
            right_type='writer',
            share=Decimal('99.00')
        )

        result = validators.validate_auto_split_validated(item)
        self.assertFalse(result)

    def test_splits_over_100_percent(self):
        """Test validation fails when splits > 100%."""
        item = SongChecklistItem.objects.create(
            song=self.song,
            stage='publishing',
            category='Writer Splits',
            item_name='Writer splits = 100%',
            description='Splits must equal 100%',
            required=True,
            validation_type='auto_split_validated',
            validation_rule={'entity': 'work', 'split_type': 'writer'},
            order=1
        )

        # Create 101% split (invalid)
        Split.objects.create(
            scope='work',
            object_id=self.work.id,
            entity=self.writer,
            right_type='writer',
            share=Decimal('101.00')
        )

        result = validators.validate_auto_split_validated(item)
        self.assertFalse(result)

    def test_multiple_splits_equal_100(self):
        """Test validation with multiple splits totaling 100%."""
        item = SongChecklistItem.objects.create(
            song=self.song,
            stage='publishing',
            category='Writer Splits',
            item_name='Writer splits = 100%',
            description='Splits must equal 100%',
            required=True,
            validation_type='auto_split_validated',
            validation_rule={'entity': 'work', 'split_type': 'writer'},
            order=1
        )

        writer2 = Entity.objects.create(
            kind='PF',
            display_name='Test Writer 2',
            created_by=self.user
        )

        # Create 50% + 50% = 100%
        Split.objects.create(
            scope='work',
            object_id=self.work.id,
            entity=self.writer,
            right_type='writer',
            share=Decimal('50.00')
        )
        Split.objects.create(
            scope='work',
            object_id=self.work.id,
            entity=writer2,
            right_type='writer',
            share=Decimal('50.00')
        )

        result = validators.validate_auto_split_validated(item)
        self.assertTrue(result)

    def test_skip_if_empty_allows_zero(self):
        """Test skip_if_empty option allows 0% splits."""
        item = SongChecklistItem.objects.create(
            song=self.song,
            stage='publishing',
            category='Publisher Splits',
            item_name='Publisher splits = 100% (if exists)',
            description='Splits must equal 100% if publishers exist',
            required=False,
            validation_type='auto_split_validated',
            validation_rule={'entity': 'work', 'split_type': 'publisher', 'skip_if_empty': True},
            order=1
        )

        # No publisher splits (0%)
        result = validators.validate_auto_split_validated(item)
        self.assertTrue(result)  # Should pass because skip_if_empty=True


class ValidateAutoCountMinimumTestCase(TestCase):
    """Test validate_auto_count_minimum() function."""

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

        self.work = Work.objects.create(
            title='Test Work'
        )
        self.recording = Recording.objects.create(
            title='Test Recording',
            work=self.work
        )

        self.song = Song.objects.create(
            title='Test Song',
            created_by=self.user,
            stage='publishing',
            work=self.work
        )
        self.song.recordings.add(self.recording)

        self.writer = Entity.objects.create(
            kind='PF',
            display_name='Test Writer',
            created_by=self.user
        )

    def test_minimum_count_met(self):
        """Test validation when minimum count is met."""
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

        # No writers
        result = validators.validate_auto_count_minimum(item)
        self.assertFalse(result)

        # Create 1 writer split
        Split.objects.create(
            scope='work',
            object_id=self.work.id,
            entity=self.writer,
            right_type='writer',
            share=Decimal('100.00')
        )

        result = validators.validate_auto_count_minimum(item)
        self.assertTrue(result)

    def test_minimum_count_not_met(self):
        """Test validation fails when minimum count not met."""
        item = SongChecklistItem.objects.create(
            song=self.song,
            stage='label_recording',
            category='Credits',
            item_name='At least 2 credits',
            description='Recording must have at least 2 credits',
            required=True,
            validation_type='auto_count_minimum',
            validation_rule={'entity': 'recording_credits', 'min_count': 2},
            order=1
        )

        # Create only 1 credit
        Credit.objects.create(
            scope='recording',
            object_id=self.recording.id,
            entity=self.writer,
            role='producer'
        )

        result = validators.validate_auto_count_minimum(item)
        self.assertFalse(result)

        # Create 2nd credit
        producer = Entity.objects.create(
            kind='PF',
            display_name='Test Producer',
            created_by=self.user
        )
        Credit.objects.create(
            scope='recording',
            object_id=self.recording.id,
            entity=producer,
            role='engineer'
        )

        result = validators.validate_auto_count_minimum(item)
        self.assertTrue(result)


class RunValidationTestCase(TestCase):
    """Test run_validation() dispatcher function."""

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

        self.work = Work.objects.create(
            title='Test Work'
        )

        self.song = Song.objects.create(
            title='Test Song',
            created_by=self.user,
            stage='publishing',
            work=self.work
        )

    def test_run_validation_manual(self):
        """Test run_validation() for manual validation type."""
        item = SongChecklistItem.objects.create(
            song=self.song,
            stage='publishing',
            category='Legal',
            item_name='Contracts signed',
            description='Sign contracts',
            required=True,
            validation_type='manual',
            is_complete=True,
            order=1
        )

        result = validators.run_validation(item)
        self.assertTrue(result)

        item.is_complete = False
        result = validators.run_validation(item)
        self.assertFalse(result)

    def test_run_validation_auto_entity_exists(self):
        """Test run_validation() for auto_entity_exists type."""
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

        # Work exists
        result = validators.run_validation(item)
        self.assertTrue(result)

    def test_run_validation_unknown_type(self):
        """Test run_validation() with unknown validation type."""
        item = SongChecklistItem.objects.create(
            song=self.song,
            stage='publishing',
            category='Test',
            item_name='Unknown test',
            description='Unknown',
            required=True,
            validation_type='unknown_type',
            order=1
        )

        result = validators.run_validation(item)
        self.assertFalse(result)


class RevalidateChecklistItemTestCase(TestCase):
    """Test revalidate_checklist_item() function."""

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

        self.work = Work.objects.create(
            title='Test Work'
        )

        self.song = Song.objects.create(
            title='Test Song',
            created_by=self.user,
            stage='publishing',
            work=self.work
        )

        self.writer = Entity.objects.create(
            kind='PF',
            display_name='Test Writer',
            created_by=self.user
        )

    def test_revalidate_updates_status(self):
        """Test that revalidate_checklist_item() updates is_complete status."""
        item = SongChecklistItem.objects.create(
            song=self.song,
            stage='publishing',
            category='Writer Splits',
            item_name='Writer splits = 100%',
            description='Splits must equal 100%',
            required=True,
            validation_type='auto_split_validated',
            validation_rule={'entity': 'work', 'split_type': 'writer'},
            is_complete=False,
            order=1
        )

        # Create 100% split
        Split.objects.create(
            scope='work',
            object_id=self.work.id,
            entity=self.writer,
            right_type='writer',
            share=Decimal('100.00')
        )

        # Revalidate
        result = validators.revalidate_checklist_item(item)
        self.assertTrue(result)

        # Check that item was updated
        item.refresh_from_db()
        self.assertTrue(item.is_complete)

    def test_revalidate_skips_manual_items(self):
        """Test that revalidate skips manual validation items."""
        item = SongChecklistItem.objects.create(
            song=self.song,
            stage='publishing',
            category='Legal',
            item_name='Contracts signed',
            description='Sign contracts',
            required=True,
            validation_type='manual',
            is_complete=False,
            order=1
        )

        # Revalidate should not change manual items
        result = validators.revalidate_checklist_item(item)
        self.assertFalse(result)

        item.refresh_from_db()
        self.assertFalse(item.is_complete)


class RevalidateSongChecklistTestCase(TestCase):
    """Test revalidate_song_checklist() function."""

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

        self.work = Work.objects.create(
            title='Test Work'
        )

        self.song = Song.objects.create(
            title='Test Song',
            created_by=self.user,
            stage='publishing',
            work=self.work
        )

    def test_revalidate_song_checklist(self):
        """Test revalidating all checklist items for a song."""
        # Note: Current implementation is a placeholder
        # This test verifies the function runs without error

        result = validators.revalidate_song_checklist(self.song)

        self.assertIsInstance(result, dict)
        self.assertIn('total', result)
        self.assertIn('passed', result)
        self.assertIn('failed', result)
        self.assertIn('updated', result)
