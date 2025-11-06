"""
Tests for Song Workflow permissions.

Tests permission functions from permissions.py:
- user_can_view_song()
- user_can_edit_song()
- user_can_transition_stage()
- user_can_view_splits()
- VISIBILITY_MATRIX enforcement
- EDIT_MATRIX enforcement
- VALID_TRANSITIONS enforcement
"""

from django.test import TestCase
from django.contrib.auth import get_user_model

from catalog.models import Song, SongChecklistItem
from catalog import permissions as song_permissions
from api.models import Department, Role, UserProfile
from identity.models import Entity

User = get_user_model()


class SongPermissionsTestCase(TestCase):
    """Test song permission functions."""

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
        self.sales_dept = Department.objects.create(
            code='sales',
            name='Sales Department'
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
        self.label_role = Role.objects.create(
            code='label_employee',
            name='Label Employee',
            level=200,
            department=self.label_dept
        )
        self.marketing_role = Role.objects.create(
            code='marketing_employee',
            name='Marketing Employee',
            level=200,
            department=self.marketing_dept
        )
        self.digital_role = Role.objects.create(
            code='digital_employee',
            name='Digital Employee',
            level=200,
            department=self.digital_dept
        )
        self.sales_role = Role.objects.create(
            code='sales_employee',
            name='Sales Employee',
            level=200,
            department=self.sales_dept
        )

        # Create users
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

        # Create a test song
        self.song_draft = Song.objects.create(
            title='Draft Song',
            created_by=self.publishing_user,
            stage='draft'
        )
        self.song_publishing = Song.objects.create(
            title='Publishing Song',
            created_by=self.publishing_user,
            stage='publishing'
        )
        self.song_label_recording = Song.objects.create(
            title='Label Recording Song',
            created_by=self.publishing_user,
            stage='label_recording'
        )
        self.song_marketing = Song.objects.create(
            title='Marketing Song',
            created_by=self.publishing_user,
            stage='marketing_assets'
        )

    # ========== VIEW PERMISSIONS ==========

    def test_admin_can_view_all_songs(self):
        """Test that admin can view songs at any stage."""
        self.assertTrue(song_permissions.user_can_view_song(self.admin_user, self.song_draft))
        self.assertTrue(song_permissions.user_can_view_song(self.admin_user, self.song_publishing))
        self.assertTrue(song_permissions.user_can_view_song(self.admin_user, self.song_label_recording))
        self.assertTrue(song_permissions.user_can_view_song(self.admin_user, self.song_marketing))

    def test_creator_can_always_view_their_songs(self):
        """Test that song creator can always view their songs."""
        self.assertTrue(song_permissions.user_can_view_song(self.publishing_user, self.song_draft))
        self.assertTrue(song_permissions.user_can_view_song(self.publishing_user, self.song_publishing))
        self.assertTrue(song_permissions.user_can_view_song(self.publishing_user, self.song_label_recording))

    def test_publishing_can_view_publishing_stage(self):
        """Test that Publishing department can view Publishing stage songs."""
        self.assertTrue(song_permissions.user_can_view_song(self.publishing_user, self.song_publishing))

    def test_publishing_cannot_view_label_recording_stage(self):
        """Test that Publishing cannot view Label Recording stage."""
        # Create song by different user
        song = Song.objects.create(
            title='Label Song',
            created_by=self.label_user,
            stage='label_recording'
        )
        self.assertFalse(song_permissions.user_can_view_song(self.publishing_user, song))

    def test_marketing_can_only_view_marketing_stage(self):
        """Test that Marketing can ONLY view MARKETING_ASSETS stage."""
        # Can view marketing stage
        self.assertTrue(song_permissions.user_can_view_song(self.marketing_user, self.song_marketing))

        # Cannot view other stages
        song_pub = Song.objects.create(
            title='Pub Song',
            created_by=self.label_user,
            stage='publishing'
        )
        self.assertFalse(song_permissions.user_can_view_song(self.marketing_user, song_pub))

    def test_sales_can_view_publishing_stage(self):
        """Test that Sales can see Publishing stage songs."""
        self.assertTrue(song_permissions.user_can_view_song(self.sales_user, self.song_publishing))

    def test_label_can_view_label_stages(self):
        """Test that Label can view their stages."""
        self.assertTrue(song_permissions.user_can_view_song(self.label_user, self.song_label_recording))

        song_review = Song.objects.create(
            title='Review Song',
            created_by=self.label_user,
            stage='label_review'
        )
        self.assertTrue(song_permissions.user_can_view_song(self.label_user, song_review))

    def test_digital_can_view_digital_stages(self):
        """Test that Digital can view their stages."""
        song_digital = Song.objects.create(
            title='Digital Song',
            created_by=self.label_user,
            stage='digital_distribution'
        )
        self.assertTrue(song_permissions.user_can_view_song(self.digital_user, song_digital))

    def test_archived_songs_only_visible_to_admin_and_creator(self):
        """Test that archived songs are only visible to admin and creator."""
        archived_song = Song.objects.create(
            title='Archived Song',
            created_by=self.publishing_user,
            stage='archived',
            is_archived=True
        )

        # Admin can view
        self.assertTrue(song_permissions.user_can_view_song(self.admin_user, archived_song))

        # Creator can view
        self.assertTrue(song_permissions.user_can_view_song(self.publishing_user, archived_song))

        # Others cannot view
        self.assertFalse(song_permissions.user_can_view_song(self.label_user, archived_song))

    # ========== EDIT PERMISSIONS ==========

    def test_admin_can_edit_all_songs(self):
        """Test that admin can edit songs at any stage."""
        self.assertTrue(song_permissions.user_can_edit_song(self.admin_user, self.song_draft))
        self.assertTrue(song_permissions.user_can_edit_song(self.admin_user, self.song_publishing))
        self.assertTrue(song_permissions.user_can_edit_song(self.admin_user, self.song_label_recording))

    def test_publishing_can_edit_publishing_stages(self):
        """Test that Publishing can edit draft and publishing stages."""
        self.assertTrue(song_permissions.user_can_edit_song(self.publishing_user, self.song_draft))
        self.assertTrue(song_permissions.user_can_edit_song(self.publishing_user, self.song_publishing))

    def test_publishing_cannot_edit_label_stage(self):
        """Test that Publishing cannot edit Label stage songs."""
        song = Song.objects.create(
            title='Label Song',
            created_by=self.label_user,
            stage='label_recording'
        )
        self.assertFalse(song_permissions.user_can_edit_song(self.publishing_user, song))

    def test_label_can_edit_label_stages(self):
        """Test that Label can edit their stages."""
        self.assertTrue(song_permissions.user_can_edit_song(self.label_user, self.song_label_recording))

    def test_marketing_can_edit_marketing_stage(self):
        """Test that Marketing can edit marketing_assets stage."""
        self.assertTrue(song_permissions.user_can_edit_song(self.marketing_user, self.song_marketing))

    def test_marketing_cannot_edit_other_stages(self):
        """Test that Marketing cannot edit other stages."""
        self.assertFalse(song_permissions.user_can_edit_song(self.marketing_user, self.song_publishing))

    def test_creator_can_only_edit_in_draft_stage(self):
        """Test that creator can only edit their song in draft stage."""
        # Can edit in draft
        self.assertTrue(song_permissions.user_can_edit_song(self.publishing_user, self.song_draft))

        # Cannot edit in other stages (unless department permission)
        song = Song.objects.create(
            title='Marketing Song',
            created_by=self.marketing_user,
            stage='marketing_assets'
        )
        # Marketing user can edit because they're in marketing dept
        self.assertTrue(song_permissions.user_can_edit_song(self.marketing_user, song))

    def test_no_editing_in_released_stage(self):
        """Test that no one can edit released songs (except admin)."""
        released_song = Song.objects.create(
            title='Released Song',
            created_by=self.publishing_user,
            stage='released'
        )

        # Admin can edit
        self.assertTrue(song_permissions.user_can_edit_song(self.admin_user, released_song))

        # Others cannot edit
        self.assertFalse(song_permissions.user_can_edit_song(self.publishing_user, released_song))
        self.assertFalse(song_permissions.user_can_edit_song(self.label_user, released_song))

    # ========== SPLIT VISIBILITY ==========

    def test_admin_can_view_all_splits(self):
        """Test that admin can view splits."""
        self.assertTrue(song_permissions.user_can_view_splits(self.admin_user, self.song_publishing))

    def test_publishing_can_view_splits_in_publishing_stage(self):
        """Test that Publishing can view splits in their stages."""
        self.assertTrue(song_permissions.user_can_view_splits(self.publishing_user, self.song_publishing))

    def test_label_can_view_splits_in_label_stages(self):
        """Test that Label can view splits in their stages."""
        self.assertTrue(song_permissions.user_can_view_splits(self.label_user, self.song_label_recording))

    def test_sales_cannot_view_splits(self):
        """Test that Sales CANNOT see splits (even in Publishing stage)."""
        self.assertFalse(song_permissions.user_can_view_splits(self.sales_user, self.song_publishing))

    def test_marketing_cannot_view_splits(self):
        """Test that Marketing cannot view splits."""
        self.assertFalse(song_permissions.user_can_view_splits(self.marketing_user, self.song_marketing))

    def test_digital_cannot_view_splits(self):
        """Test that Digital cannot view splits."""
        song_digital = Song.objects.create(
            title='Digital Song',
            created_by=self.label_user,
            stage='digital_distribution'
        )
        self.assertFalse(song_permissions.user_can_view_splits(self.digital_user, song_digital))

    # ========== STAGE TRANSITIONS ==========

    def test_admin_can_always_transition(self):
        """Test that admin can always transition (admin override)."""
        can_transition, reason = song_permissions.user_can_transition_stage(
            self.admin_user, self.song_publishing, 'label_recording'
        )
        self.assertTrue(can_transition)

    def test_valid_transition_with_complete_checklist(self):
        """Test valid transition with complete checklist."""
        # Create complete checklist
        SongChecklistItem.objects.create(
            song=self.song_publishing,
            stage='publishing',
            category='Work Setup',
            item_name='Work created',
            description='Create work',
            required=True,
            validation_type='manual',
            is_complete=True,
            order=1
        )

        can_transition, reason = song_permissions.user_can_transition_stage(
            self.publishing_user, self.song_publishing, 'label_recording'
        )
        self.assertTrue(can_transition)

    def test_transition_fails_with_incomplete_checklist(self):
        """Test transition fails when checklist incomplete."""
        # Create incomplete checklist
        SongChecklistItem.objects.create(
            song=self.song_publishing,
            stage='publishing',
            category='Work Setup',
            item_name='Work created',
            description='Create work',
            required=True,
            validation_type='manual',
            is_complete=False,  # Not complete
            order=1
        )

        can_transition, reason = song_permissions.user_can_transition_stage(
            self.publishing_user, self.song_publishing, 'label_recording'
        )
        self.assertFalse(can_transition)
        self.assertIn('Checklist', reason)

    def test_transition_fails_for_invalid_stage(self):
        """Test transition fails for invalid stage progression."""
        can_transition, reason = song_permissions.user_can_transition_stage(
            self.publishing_user, self.song_draft, 'label_recording'  # Cannot skip publishing
        )
        self.assertFalse(can_transition)
        self.assertIn('Cannot transition', reason)

    def test_transition_fails_without_edit_permission(self):
        """Test transition fails without edit permission."""
        can_transition, reason = song_permissions.user_can_transition_stage(
            self.marketing_user, self.song_publishing, 'label_recording'
        )
        self.assertFalse(can_transition)
        self.assertIn('permission', reason)

    def test_label_can_send_back_to_marketing(self):
        """Test that Label can send song back to Marketing from label_review."""
        song_review = Song.objects.create(
            title='Review Song',
            created_by=self.label_user,
            stage='label_review'
        )

        # Complete checklist (admin override in this case)
        can_transition, reason = song_permissions.user_can_transition_stage(
            self.admin_user, song_review, 'marketing_assets'
        )
        self.assertTrue(can_transition)

    def test_archiving_allowed_from_any_stage(self):
        """Test that archiving is allowed from any stage."""
        # Admin can archive from any stage
        can_transition, _ = song_permissions.user_can_transition_stage(
            self.admin_user, self.song_publishing, 'archived'
        )
        self.assertTrue(can_transition)

    # ========== HELPER FUNCTIONS ==========

    def test_get_visible_stages_for_user(self):
        """Test getting visible stages for each department."""
        # Publishing
        stages = song_permissions.get_visible_stages_for_user(self.publishing_user)
        self.assertIn('draft', stages)
        self.assertIn('publishing', stages)
        self.assertNotIn('label_recording', stages)

        # Marketing
        stages = song_permissions.get_visible_stages_for_user(self.marketing_user)
        self.assertIn('marketing_assets', stages)
        self.assertEqual(len(stages), 2)  # marketing_assets and label_review

        # Label
        stages = song_permissions.get_visible_stages_for_user(self.label_user)
        self.assertIn('label_recording', stages)
        self.assertIn('label_review', stages)

        # Admin sees all
        stages = song_permissions.get_visible_stages_for_user(self.admin_user)
        self.assertEqual(len(stages), 9)  # All stages

    def test_get_editable_stages_for_user(self):
        """Test getting editable stages for each department."""
        # Publishing
        stages = song_permissions.get_editable_stages_for_user(self.publishing_user)
        self.assertIn('draft', stages)
        self.assertIn('publishing', stages)

        # Marketing
        stages = song_permissions.get_editable_stages_for_user(self.marketing_user)
        self.assertIn('marketing_assets', stages)
        self.assertEqual(len(stages), 1)

        # Label
        stages = song_permissions.get_editable_stages_for_user(self.label_user)
        self.assertIn('label_recording', stages)
        self.assertIn('label_review', stages)

    def test_get_department_for_stage(self):
        """Test getting responsible department for each stage."""
        self.assertEqual(song_permissions.get_department_for_stage('draft'), 'publishing')
        self.assertEqual(song_permissions.get_department_for_stage('publishing'), 'publishing')
        self.assertEqual(song_permissions.get_department_for_stage('label_recording'), 'label')
        self.assertEqual(song_permissions.get_department_for_stage('marketing_assets'), 'marketing')
        self.assertEqual(song_permissions.get_department_for_stage('digital_distribution'), 'digital')
        self.assertIsNone(song_permissions.get_department_for_stage('released'))

    # ========== VISIBILITY MATRIX ==========

    def test_visibility_matrix_publishing(self):
        """Test VISIBILITY_MATRIX for Publishing department."""
        allowed = song_permissions.VISIBILITY_MATRIX['publishing']
        self.assertIn('publishing', allowed)
        self.assertIn('sales', allowed)

    def test_visibility_matrix_marketing(self):
        """Test VISIBILITY_MATRIX for Marketing - limited access."""
        allowed = song_permissions.VISIBILITY_MATRIX['marketing_assets']
        self.assertIn('label', allowed)
        self.assertIn('marketing', allowed)
        self.assertEqual(len(allowed), 2)

    def test_edit_matrix_released_no_one(self):
        """Test EDIT_MATRIX - released stage has no editors."""
        allowed = song_permissions.EDIT_MATRIX['released']
        self.assertEqual(len(allowed), 0)

    # ========== VALID TRANSITIONS ==========

    def test_valid_transitions_draft(self):
        """Test valid transitions from draft stage."""
        valid = song_permissions.VALID_TRANSITIONS['draft']
        self.assertIn('publishing', valid)
        self.assertIn('archived', valid)
        self.assertNotIn('label_recording', valid)  # Cannot skip

    def test_valid_transitions_label_review_can_go_back(self):
        """Test that label_review can send back to marketing."""
        valid = song_permissions.VALID_TRANSITIONS['label_review']
        self.assertIn('marketing_assets', valid)  # Can send back
        self.assertIn('ready_for_digital', valid)  # Can move forward
