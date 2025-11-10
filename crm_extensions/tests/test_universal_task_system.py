"""
Integration tests for the Universal Task Automation System.

Tests cover:
- Automatic task creation via FlowTriggers
- Task updates via signal handlers
- Manual trigger execution
- Task-entity synchronization
- Checklist-task bidirectional sync
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status as http_status

from crm_extensions.models import Task, FlowTrigger, ManualTrigger
from catalog.models import Song, Work, Recording, SongChecklistItem
from artist_sales.models import Opportunity, OpportunityDeliverable
from api.models import Department
from identity.models import Entity

User = get_user_model()


class UniversalTaskSystemIntegrationTest(TestCase):
    """Test end-to-end task automation workflows."""

    def setUp(self):
        self.client = APIClient()

        # Create departments
        self.dept_publishing = Department.objects.get_or_create(
            code='publishing',
            defaults={'name': 'Publishing'}
        )[0]
        self.dept_marketing = Department.objects.get_or_create(
            code='marketing',
            defaults={'name': 'Marketing'}
        )[0]
        self.dept_digital = Department.objects.get_or_create(
            code='digital',
            defaults={'name': 'Digital'}
        )[0]

        # Create test user
        self.user = User.objects.create_user(username='testuser', password='pass')
        self.user.profile.department = self.dept_publishing
        self.user.profile.save()

        # Create test entity (artist)
        self.artist = Entity.objects.create(display_name='Test Artist', kind='PF')

    def test_song_creation_triggers_publishing_task(self):
        """Test that creating a song automatically creates a publishing task."""
        # Create a FlowTrigger for song creation
        trigger = FlowTrigger.objects.create(
            name='Song Created - Publishing Setup',
            trigger_entity_type='song',
            trigger_type='on_create',
            conditions={},
            action_type='create_task',
            action_config={
                'task_title_template': 'Set up publishing for "{entity.title}"',
                'task_type': 'registration',
                'target_department_code': 'publishing',
                'priority': 2,
            },
            is_active=True
        )

        initial_task_count = Task.objects.count()

        # Create a song
        song = Song.objects.create(
            title='Test Song',
            artist=self.artist,
            stage='publishing'
        )

        # Verify task was created
        tasks = Task.objects.filter(song=song)
        self.assertEqual(tasks.count(), 1)
        task = tasks.first()
        self.assertEqual(task.title, 'Set up publishing for "Test Song"')
        self.assertEqual(task.task_type, 'registration')
        self.assertEqual(task.department, self.dept_publishing)
        self.assertEqual(task.status, 'todo')

    def test_song_stage_change_creates_digital_task(self):
        """Test that moving song to digital stage creates digital manager task."""
        # Create song in label stage
        song = Song.objects.create(
            title='Test Song',
            artist=self.artist,
            stage='label_recording'
        )

        initial_task_count = Task.objects.filter(song=song).count()

        # Move to digital_distribution stage
        song.stage = 'digital_distribution'
        song.save()

        # Verify digital release task was created
        tasks = Task.objects.filter(
            song=song,
            department=self.dept_digital,
            task_type='platform_setup'
        )
        self.assertEqual(tasks.count(), 1)
        task = tasks.first()
        self.assertIn('Release', task.title)
        self.assertIn('digital platforms', task.title)

    def test_checklist_item_creates_and_syncs_task(self):
        """Test bidirectional sync between checklist items and tasks."""
        song = Song.objects.create(
            title='Test Song',
            artist=self.artist,
            stage='marketing_assets'
        )

        # Create a required checklist item
        checklist_item = SongChecklistItem.objects.create(
            song=song,
            checklist_name='marketing_assets',
            item_name='Cover Art',
            required=True,
            is_complete=False
        )

        # Verify task was created
        tasks = Task.objects.filter(song_checklist_item=checklist_item)
        self.assertEqual(tasks.count(), 1)
        task = tasks.first()
        self.assertEqual(task.status, 'todo')

        # Complete the checklist item
        checklist_item.is_complete = True
        checklist_item.save()

        # Verify task status updated to done
        task.refresh_from_db()
        self.assertEqual(task.status, 'done')

    def test_deliverable_asset_upload_completes_task(self):
        """Test that uploading deliverable asset marks task as done."""
        # Create opportunity and deliverable
        account = Entity.objects.create(display_name='Client Account', kind='PJ')
        opportunity = Opportunity.objects.create(
            title='Test Opportunity',
            account=account,
            owner=self.user,
            stage='negotiation'
        )

        deliverable = OpportunityDeliverable.objects.create(
            opportunity=opportunity,
            deliverable_type='video_ad',
            quantity=1,
            status='planned'
        )

        # Create a task for this deliverable
        task = Task.objects.create(
            title=f'Create {deliverable.deliverable_type}',
            deliverable=deliverable,
            department=self.dept_marketing,
            task_type='content_creation',
            status='in_progress'
        )

        # Upload asset
        deliverable.asset_url = 'https://example.com/video.mp4'
        deliverable.save()

        # Verify task was marked as done
        task.refresh_from_db()
        self.assertEqual(task.status, 'done')
        self.assertIn('Asset uploaded', task.notes)

    def test_deliverable_revision_requested_reopens_task(self):
        """Test that requesting revision reopens completed task."""
        # Create deliverable with completed task
        account = Entity.objects.create(display_name='Client Account', kind='PJ')
        opportunity = Opportunity.objects.create(
            title='Test Opportunity',
            account=account,
            owner=self.user,
            stage='negotiation'
        )

        deliverable = OpportunityDeliverable.objects.create(
            opportunity=opportunity,
            deliverable_type='social_media_content',
            quantity=1,
            status='approved',
            asset_url='https://example.com/content.jpg'
        )

        task = Task.objects.create(
            title=f'Create {deliverable.deliverable_type}',
            deliverable=deliverable,
            department=self.dept_marketing,
            task_type='content_creation',
            status='done'
        )

        # Request revision
        deliverable.status = 'revision_requested'
        deliverable.save()

        # Verify task was reopened
        task.refresh_from_db()
        self.assertEqual(task.status, 'in_progress')
        self.assertIn('Reopened: Revision requested', task.notes)

    def test_manual_trigger_execution_creates_task(self):
        """Test manual trigger button creates task via API."""
        # Create a manual trigger
        trigger = ManualTrigger.objects.create(
            name='Request Marketing',
            button_label='Send to Marketing',
            button_style='primary',
            entity_type='song',
            context='label_recording_stage',
            action_type='create_task',
            action_config={
                'task_title_template': 'Create marketing materials for "{entity.title}"',
                'task_type': 'content_creation',
                'target_department_code': 'marketing',
                'priority': 3,
            },
            is_active=True
        )
        trigger.visible_to_departments.add(self.dept_publishing)

        # Create a song
        song = Song.objects.create(
            title='Test Song',
            artist=self.artist,
            stage='label_recording'
        )

        # Authenticate
        self.client.force_authenticate(user=self.user)

        # Execute trigger via API
        response = self.client.post(
            f'/api/v1/crm/manual-triggers/{trigger.id}/execute/',
            {
                'entity_id': song.id,
                'context_data': {}
            },
            format='json'
        )

        self.assertEqual(response.status_code, http_status.HTTP_201_CREATED)

        # Verify task was created
        tasks = Task.objects.filter(
            song=song,
            department=self.dept_marketing,
            task_type='content_creation'
        )
        self.assertEqual(tasks.count(), 1)
        task = tasks.first()
        self.assertIn('marketing materials', task.title)
        self.assertEqual(task.priority, 3)

    def test_task_title_updates_when_entity_changes(self):
        """Test that task titles update when entity name changes."""
        # Create song with task
        song = Song.objects.create(
            title='Original Title',
            artist=self.artist,
            stage='publishing'
        )

        task = Task.objects.create(
            title='Set up publishing for "Original Title"',
            song=song,
            department=self.dept_publishing,
            task_type='registration',
            status='todo'
        )

        # Rename song
        song.title = 'New Title'
        song.save()

        # Verify task title was updated (if title update logic exists in signals)
        # Note: This requires implementing title update logic in catalog/signals.py
        # For now, this test documents the expected behavior


class TaskAPIFilteringTest(TestCase):
    """Test API filtering for universal task system."""

    def setUp(self):
        self.client = APIClient()

        # Create departments
        self.dept_marketing = Department.objects.get_or_create(
            code='marketing',
            defaults={'name': 'Marketing'}
        )[0]

        # Create user
        self.user = User.objects.create_user(username='testuser', password='pass')
        self.user.profile.department = self.dept_marketing
        self.user.profile.save()

        # Create test data
        self.artist = Entity.objects.create(display_name='Test Artist', kind='PF')
        self.song1 = Song.objects.create(title='Song 1', artist=self.artist, stage='marketing_assets')
        self.song2 = Song.objects.create(title='Song 2', artist=self.artist, stage='publishing')

        self.task1 = Task.objects.create(
            title='Task for Song 1',
            song=self.song1,
            department=self.dept_marketing,
            task_type='content_creation',
            status='in_progress'
        )

        self.task2 = Task.objects.create(
            title='Task for Song 2',
            song=self.song2,
            department=self.dept_marketing,
            task_type='content_creation',
            status='todo'
        )

    def test_filter_tasks_by_entity_type(self):
        """Test filtering tasks by entity_type parameter."""
        self.client.force_authenticate(user=self.user)

        # Filter by entity_type=song
        response = self.client.get('/api/v1/crm/tasks/?entity_type=song')
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_filter_tasks_by_specific_song(self):
        """Test filtering tasks by specific song FK."""
        self.client.force_authenticate(user=self.user)

        # Filter by song ID
        response = self.client.get(f'/api/v1/crm/tasks/?song={self.song1.id}')
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['song'], self.song1.id)

    def test_task_detail_includes_entity_details(self):
        """Test that task detail includes populated entity detail fields."""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(f'/api/v1/crm/tasks/{self.task1.id}/')
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)

        # Verify song_detail is populated
        self.assertIn('song_detail', response.data)
        self.assertIsNotNone(response.data['song_detail'])
        self.assertEqual(response.data['song_detail']['title'], 'Song 1')
        self.assertEqual(response.data['song_detail']['stage'], 'marketing_assets')
