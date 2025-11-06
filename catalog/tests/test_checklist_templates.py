"""
Tests for checklist templates.

Tests checklist generation from checklist_templates.py:
- generate_checklist_for_stage() creates correct items
- Each stage template has correct number of items
- Required vs optional items
- Validation rules are properly configured
"""

from django.test import TestCase
from django.contrib.auth import get_user_model

from catalog.models import Song, SongChecklistItem
from catalog import checklist_templates
from api.models import Department, Role, UserProfile

User = get_user_model()


class ChecklistTemplateTestCase(TestCase):
    """Test checklist template functions."""

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

    def test_get_template_for_stage_publishing(self):
        """Test getting template for Publishing stage."""
        template = checklist_templates.get_template_for_stage('publishing')

        self.assertIsInstance(template, list)
        self.assertGreater(len(template), 0)

        # Verify template structure
        for item in template:
            self.assertIn('category', item)
            self.assertIn('item_name', item)
            self.assertIn('description', item)
            self.assertIn('required', item)
            self.assertIn('validation_type', item)
            self.assertIn('order', item)

    def test_get_template_for_stage_label_recording(self):
        """Test getting template for Label Recording stage."""
        template = checklist_templates.get_template_for_stage('label_recording')

        self.assertIsInstance(template, list)
        self.assertGreater(len(template), 0)

        # Check for specific items
        item_names = [item['item_name'] for item in template]
        self.assertIn('Recording entity created', item_names)
        self.assertIn('ISRC assigned', item_names)

    def test_get_template_for_stage_marketing(self):
        """Test getting template for Marketing stage."""
        template = checklist_templates.get_template_for_stage('marketing_assets')

        self.assertIsInstance(template, list)
        self.assertGreater(len(template), 0)

        # Check for marketing-specific items
        item_names = [item['item_name'] for item in template]
        self.assertIn('Cover artwork uploaded', item_names)

    def test_get_template_for_stage_digital(self):
        """Test getting template for Digital Distribution stage."""
        template = checklist_templates.get_template_for_stage('digital_distribution')

        self.assertIsInstance(template, list)
        self.assertGreater(len(template), 0)

        # Check for digital-specific items
        item_names = [item['item_name'] for item in template]
        self.assertIn('UPC/EAN assigned', item_names)

    def test_draft_stage_has_no_checklist(self):
        """Test that draft stage has no checklist items."""
        template = checklist_templates.get_template_for_stage('draft')
        self.assertEqual(len(template), 0)

    def test_released_stage_has_no_checklist(self):
        """Test that released stage has no checklist items."""
        template = checklist_templates.get_template_for_stage('released')
        self.assertEqual(len(template), 0)

    def test_archived_stage_has_no_checklist(self):
        """Test that archived stage has no checklist items."""
        template = checklist_templates.get_template_for_stage('archived')
        self.assertEqual(len(template), 0)

    def test_generate_checklist_for_stage(self):
        """Test generating checklist items from template."""
        items_data = checklist_templates.generate_checklist_for_stage(
            self.song, 'publishing'
        )

        self.assertIsInstance(items_data, list)
        self.assertGreater(len(items_data), 0)

        # Verify item structure
        for item_data in items_data:
            self.assertEqual(item_data['song'], self.song)
            self.assertEqual(item_data['stage'], 'publishing')
            self.assertIn('category', item_data)
            self.assertIn('item_name', item_data)
            self.assertIn('required', item_data)
            self.assertFalse(item_data['is_complete'])

    def test_publishing_checklist_items(self):
        """Test Publishing stage checklist items."""
        template = checklist_templates.PUBLISHING_CHECKLIST_TEMPLATE

        # Verify expected items
        item_names = [item['item_name'] for item in template]
        self.assertIn('Work entity created', item_names)
        self.assertIn('ISWC assigned', item_names)
        self.assertIn('At least 1 writer added', item_names)
        self.assertIn('Writer splits = 100%', item_names)

        # Verify required/optional flags
        work_created = next(i for i in template if i['item_name'] == 'Work entity created')
        self.assertTrue(work_created['required'])

        # Optional item
        publisher_splits = next(
            i for i in template
            if i['item_name'] == 'Publisher splits = 100% (if publishers exist)'
        )
        self.assertFalse(publisher_splits['required'])

    def test_label_recording_checklist_items(self):
        """Test Label Recording stage checklist items."""
        template = checklist_templates.LABEL_RECORDING_CHECKLIST_TEMPLATE

        # Verify expected items
        item_names = [item['item_name'] for item in template]
        self.assertIn('Recording entity created', item_names)
        self.assertIn('ISRC assigned', item_names)
        self.assertIn('Master audio uploaded', item_names)
        self.assertIn('Master splits = 100%', item_names)

        # Verify validation types
        recording_created = next(i for i in template if i['item_name'] == 'Recording entity created')
        self.assertEqual(recording_created['validation_type'], 'auto_entity_exists')
        self.assertEqual(recording_created['validation_rule']['entity'], 'recording')

    def test_marketing_checklist_items(self):
        """Test Marketing Assets stage checklist items."""
        template = checklist_templates.MARKETING_ASSETS_CHECKLIST_TEMPLATE

        # Verify expected items
        item_names = [item['item_name'] for item in template]
        self.assertIn('Cover artwork uploaded', item_names)
        self.assertIn('Press photo uploaded', item_names)

        # Verify custom validation
        cover_art = next(i for i in template if i['item_name'] == 'Cover artwork uploaded')
        self.assertEqual(cover_art['validation_type'], 'auto_custom')
        self.assertEqual(cover_art['validation_rule']['function'], 'validate_cover_artwork')

    def test_digital_checklist_items(self):
        """Test Digital Distribution stage checklist items."""
        template = checklist_templates.DIGITAL_DISTRIBUTION_CHECKLIST_TEMPLATE

        # Verify expected items
        item_names = [item['item_name'] for item in template]
        self.assertIn('Release entity created', item_names)
        self.assertIn('UPC/EAN assigned', item_names)
        self.assertIn('Release metadata complete', item_names)

    def test_all_templates_have_correct_structure(self):
        """Test that all templates have correct structure."""
        all_templates = checklist_templates.get_all_templates()

        for stage, template in all_templates.items():
            if len(template) > 0:  # Skip empty templates (draft, released, archived)
                for item in template:
                    # Required fields
                    self.assertIn('category', item)
                    self.assertIn('item_name', item)
                    self.assertIn('description', item)
                    self.assertIn('required', item)
                    self.assertIn('validation_type', item)
                    self.assertIn('order', item)

                    # Validation type must be valid
                    valid_types = [
                        'manual',
                        'auto_entity_exists',
                        'auto_field_exists',
                        'auto_split_validated',
                        'auto_count_minimum',
                        'auto_file_exists',
                        'auto_custom'
                    ]
                    self.assertIn(item['validation_type'], valid_types)

    def test_items_have_sequential_order(self):
        """Test that checklist items have sequential order numbers."""
        template = checklist_templates.PUBLISHING_CHECKLIST_TEMPLATE

        orders = [item['order'] for item in template]
        self.assertEqual(orders, sorted(orders))  # Should be in order

    def test_validation_rules_present_for_auto_validations(self):
        """Test that auto validation items have validation_rule."""
        template = checklist_templates.PUBLISHING_CHECKLIST_TEMPLATE

        for item in template:
            if item['validation_type'].startswith('auto'):
                if item['validation_type'] != 'auto_custom':
                    self.assertIn('validation_rule', item)
                    self.assertIsInstance(item['validation_rule'], dict)

    def test_help_text_present_where_appropriate(self):
        """Test that complex items have help_text."""
        template = checklist_templates.PUBLISHING_CHECKLIST_TEMPLATE

        # ISWC item should have help text
        iswc_item = next(i for i in template if i['item_name'] == 'ISWC assigned')
        self.assertIn('help_text', iswc_item)
        self.assertGreater(len(iswc_item['help_text']), 0)

    def test_get_all_templates(self):
        """Test getting all templates."""
        all_templates = checklist_templates.get_all_templates()

        self.assertIsInstance(all_templates, dict)
        self.assertIn('publishing', all_templates)
        self.assertIn('label_recording', all_templates)
        self.assertIn('marketing_assets', all_templates)
        self.assertIn('digital_distribution', all_templates)

    def test_template_counts(self):
        """Test that each stage has expected number of items."""
        # Publishing should have 6 items
        self.assertEqual(
            len(checklist_templates.PUBLISHING_CHECKLIST_TEMPLATE),
            6
        )

        # Label Recording should have 8 items
        self.assertEqual(
            len(checklist_templates.LABEL_RECORDING_CHECKLIST_TEMPLATE),
            8
        )

        # Marketing should have 5 items
        self.assertEqual(
            len(checklist_templates.MARKETING_ASSETS_CHECKLIST_TEMPLATE),
            5
        )

        # Label Review should have 4 items
        self.assertEqual(
            len(checklist_templates.LABEL_REVIEW_CHECKLIST_TEMPLATE),
            4
        )

        # Ready for Digital should have 3 items
        self.assertEqual(
            len(checklist_templates.READY_FOR_DIGITAL_CHECKLIST_TEMPLATE),
            3
        )

        # Digital Distribution should have 6 items
        self.assertEqual(
            len(checklist_templates.DIGITAL_DISTRIBUTION_CHECKLIST_TEMPLATE),
            6
        )
