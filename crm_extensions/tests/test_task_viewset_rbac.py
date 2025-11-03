"""
Comprehensive RBAC tests for TaskViewSet.

Tests cover:
- List filtering by role and department
- Direct M2M assignment (assigned_to_users)
- Retrieve/Update/Delete permissions
- Edge cases specific to direct M2M
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from crm_extensions.models import Task
from identity.models import Entity
from campaigns.models import Campaign
from api.models import Department, Role, Role, UserProfile


User = get_user_model()


class TaskViewSetListFilteringTestCase(TestCase):
    """Test list endpoint filtering based on RBAC with direct M2M."""

    def setUp(self):
        self.client = APIClient()

        # Create departments
        self.dept_digital, _ = Department.objects.get_or_create(code='digital', defaults={'name': 'Digital'})
        self.dept_sales, _ = Department.objects.get_or_create(code='sales', defaults={'name': 'Sales'})

        # Create entity
        self.entity = Entity.objects.create(display_name='Entity', kind='PJ')

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

        self.employee1 = User.objects.create_user(username='emp1', password='pass')
        self.employee1_profile = self.employee1.profile
        self.employee1_profile.department = self.dept_digital
        self.employee1_profile.role = Role.objects.get(code='digital_employee')
        self.employee1_profile.save()

        self.employee2 = User.objects.create_user(username='emp2', password='pass')
        self.employee2_profile = self.employee2.profile
        self.employee2_profile.department = self.dept_digital
        self.employee2_profile.role = Role.objects.get(code='digital_employee')
        self.employee2_profile.save()

        self.sales_employee = User.objects.create_user(username='sales_emp', password='pass')
        self.sales_employee_profile = self.sales_employee.profile
        self.sales_employee_profile.department = self.dept_sales
        self.sales_employee_profile.role = Role.objects.get(code='digital_employee')
        self.sales_employee_profile.save()

        # Create tasks
        self.task_emp1_created = Task.objects.create(
            title='Task created by emp1',
            department=self.dept_digital,
            created_by=self.employee1
        )
        # Auto-assigns creator
        self.task_emp1_created.assigned_to_users.add(self.employee1)

        self.task_emp2_created = Task.objects.create(
            title='Task created by emp2',
            department=self.dept_digital,
            created_by=self.employee2
        )
        self.task_emp2_created.assigned_to_users.add(self.employee2)

        # Create task where emp1 is assigned but not creator
        self.task_assigned_to_emp1 = Task.objects.create(
            title='Task assigned to emp1',
            department=self.dept_digital,
            created_by=self.employee2
        )
        self.task_assigned_to_emp1.assigned_to_users.add(self.employee1)

        # Create sales task
        self.task_sales = Task.objects.create(
            title='Sales task',
            department=self.dept_sales,
            created_by=self.sales_employee
        )
        self.task_sales.assigned_to_users.add(self.sales_employee)

    def test_admin_sees_all_tasks(self):
        """Admin should see all tasks across all departments."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/tasks/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should see all 4 tasks
        self.assertEqual(response.data['count'], 4)

    def test_manager_sees_department_tasks(self):
        """Manager should see all tasks in their department."""
        self.client.force_authenticate(user=self.digital_manager)
        response = self.client.get('/api/tasks/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should see 3 digital tasks
        self.assertEqual(response.data['count'], 3)

    def test_employee_sees_created_tasks(self):
        """Employee should see tasks they created."""
        self.client.force_authenticate(user=self.employee1)
        response = self.client.get('/api/tasks/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        task_ids = [t['id'] for t in response.data['results']]
        self.assertIn(self.task_emp1_created.id, task_ids)

    def test_employee_sees_assigned_tasks_direct_m2m(self):
        """Employee should see tasks they're assigned to via direct M2M."""
        self.client.force_authenticate(user=self.employee1)
        response = self.client.get('/api/tasks/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        task_ids = [t['id'] for t in response.data['results']]
        # Should see both created and assigned task
        self.assertIn(self.task_emp1_created.id, task_ids)
        self.assertIn(self.task_assigned_to_emp1.id, task_ids)

    def test_employee_does_not_see_unrelated_task(self):
        """Employee should not see tasks they're not related to."""
        self.client.force_authenticate(user=self.employee1)
        response = self.client.get('/api/tasks/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        task_ids = [t['id'] for t in response.data['results']]
        # Should not see emp2's task (where emp1 is not assigned)
        self.assertNotIn(self.task_emp2_created.id, task_ids)

    def test_employee_does_not_see_other_department(self):
        """Employee should not see tasks from other departments."""
        self.client.force_authenticate(user=self.employee1)
        response = self.client.get('/api/tasks/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        task_ids = [t['id'] for t in response.data['results']]
        self.assertNotIn(self.task_sales.id, task_ids)


class TaskDirectM2MAssignmentTestCase(TestCase):
    """Test direct M2M assignment specific behavior."""

    def setUp(self):
        self.client = APIClient()

        self.dept, _ = Department.objects.get_or_create(code='test', defaults={'name': 'Test'})

        self.user1 = User.objects.create_user(username='user1', password='pass')
        self.user1_profile = self.user1.profile
        self.user1_profile.department = self.dept
        self.user1_profile.role = Role.objects.get(code='digital_employee')
        self.user1_profile.save()

        self.user2 = User.objects.create_user(username='user2', password='pass')
        self.user2_profile = self.user2.profile
        self.user2_profile.department = self.dept
        self.user2_profile.role = Role.objects.get(code='digital_employee')
        self.user2_profile.save()

        self.user3 = User.objects.create_user(username='user3', password='pass')
        self.user3_profile = self.user3.profile
        self.user3_profile.department = self.dept
        self.user3_profile.role = Role.objects.get(code='digital_employee')
        self.user3_profile.save()

        self.task = Task.objects.create(
            title='Multi-assigned task',
            department=self.dept,
            created_by=self.user1
        )

        # Assign multiple users via direct M2M
        self.task.assigned_to_users.add(self.user1, self.user2)

    def test_multiple_users_can_be_assigned(self):
        """Multiple users can be assigned to same task via direct M2M."""
        # Both user1 and user2 should see the task
        self.client.force_authenticate(user=self.user1)
        response = self.client.get('/api/tasks/')
        task_ids = [t['id'] for t in response.data['results']]
        self.assertIn(self.task.id, task_ids)

        self.client.force_authenticate(user=self.user2)
        response = self.client.get('/api/tasks/')
        task_ids = [t['id'] for t in response.data['results']]
        self.assertIn(self.task.id, task_ids)

    def test_adding_user_grants_access(self):
        """Adding user to assigned_to_users grants them access."""
        # user3 initially cannot see
        self.client.force_authenticate(user=self.user3)
        response = self.client.get('/api/tasks/')
        task_ids = [t['id'] for t in response.data['results']]
        self.assertNotIn(self.task.id, task_ids)

        # Assign user3
        self.task.assigned_to_users.add(self.user3)

        # Now user3 can see
        response = self.client.get('/api/tasks/')
        task_ids = [t['id'] for t in response.data['results']]
        self.assertIn(self.task.id, task_ids)

    def test_removing_user_revokes_access(self):
        """Removing user from assigned_to_users revokes access (if not creator)."""
        # user2 can initially see
        self.client.force_authenticate(user=self.user2)
        response = self.client.get('/api/tasks/')
        task_ids = [t['id'] for t in response.data['results']]
        self.assertIn(self.task.id, task_ids)

        # Remove user2
        self.task.assigned_to_users.remove(self.user2)

        # Now user2 cannot see (not creator)
        response = self.client.get('/api/tasks/')
        task_ids = [t['id'] for t in response.data['results']]
        self.assertNotIn(self.task.id, task_ids)

    def test_creator_retains_access_even_if_removed_from_assigned(self):
        """Creator retains access even if removed from assigned_to_users."""
        # Remove user1 from assigned
        self.task.assigned_to_users.remove(self.user1)

        # user1 is creator, should still see it
        self.client.force_authenticate(user=self.user1)
        response = self.client.get('/api/tasks/')
        task_ids = [t['id'] for t in response.data['results']]
        self.assertIn(self.task.id, task_ids)

    def test_empty_assigned_to_users_shows_only_to_creator(self):
        """Task with empty assigned_to_users is only visible to creator."""
        # Remove all assigned users
        self.task.assigned_to_users.clear()

        # Creator can still see
        self.client.force_authenticate(user=self.user1)
        response = self.client.get('/api/tasks/')
        task_ids = [t['id'] for t in response.data['results']]
        self.assertIn(self.task.id, task_ids)

        # Others cannot see
        self.client.force_authenticate(user=self.user2)
        response = self.client.get('/api/tasks/')
        task_ids = [t['id'] for t in response.data['results']]
        self.assertNotIn(self.task.id, task_ids)


class TaskViewSetPermissionsTestCase(TestCase):
    """Test retrieve/update/delete permissions."""

    def setUp(self):
        self.client = APIClient()

        self.dept, _ = Department.objects.get_or_create(code='test', defaults={'name': 'Test'})

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

        self.task = Task.objects.create(
            title='Test Task',
            department=self.dept,
            created_by=self.owner
        )
        self.task.assigned_to_users.add(self.owner, self.assigned)

    def test_owner_can_retrieve(self):
        """Owner can retrieve their task."""
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(f'/api/tasks/{self.task.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_assigned_user_can_retrieve(self):
        """Assigned user can retrieve task."""
        self.client.force_authenticate(user=self.assigned)
        response = self.client.get(f'/api/tasks/{self.task.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_other_user_cannot_retrieve(self):
        """Unrelated user cannot retrieve task."""
        self.client.force_authenticate(user=self.other)
        response = self.client.get(f'/api/tasks/{self.task.id}/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_owner_can_update(self):
        """Owner can update their task."""
        self.client.force_authenticate(user=self.owner)

        data = {'title': 'Updated Title'}
        response = self.client.patch(f'/api/tasks/{self.task.id}/', data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.task.refresh_from_db()
        self.assertEqual(self.task.title, 'Updated Title')

    def test_assigned_user_can_update(self):
        """Assigned user can update task."""
        self.client.force_authenticate(user=self.assigned)

        data = {'title': 'Updated by Assigned'}
        response = self.client.patch(f'/api/tasks/{self.task.id}/', data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.task.refresh_from_db()
        self.assertEqual(self.task.title, 'Updated by Assigned')

    def test_other_user_cannot_update(self):
        """Unrelated user cannot update task."""
        self.client.force_authenticate(user=self.other)

        data = {'title': 'Hacked'}
        response = self.client.patch(f'/api/tasks/{self.task.id}/', data)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.task.refresh_from_db()
        self.assertEqual(self.task.title, 'Test Task')  # Unchanged

    def test_manager_can_access_any_task_in_dept(self):
        """Manager can access any task in their department."""
        manager = User.objects.create_user(username='manager', password='pass')
        manager_profile = manager.profile

        manager_profile.department = self.dept

        manager_profile.role = Role.objects.get(code='digital_manager')

        manager_profile.save()

        self.client.force_authenticate(user=manager)
        response = self.client.get(f'/api/tasks/{self.task.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TaskViewSetCreateTestCase(TestCase):
    """Test task creation."""

    def setUp(self):
        self.client = APIClient()

        self.dept, _ = Department.objects.get_or_create(code='digital', defaults={'name': 'Digital'})

        self.user = User.objects.create_user(username='user', password='pass')
        self.user_profile = self.user.profile
        self.user_profile.department = self.dept
        self.user_profile.role = Role.objects.get(code='digital_employee')
        self.user_profile.save()

    def test_create_auto_assigns_creator(self):
        """Creating task should auto-assign creator."""
        self.client.force_authenticate(user=self.user)

        data = {
            'title': 'New Task',
            'status': 'todo'
        }

        response = self.client.post('/api/tasks/', data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify creator is assigned
        task = Task.objects.get(id=response.data['id'])
        self.assertEqual(task.created_by, self.user)
        self.assertIn(self.user, task.assigned_to_users.all())

    def test_create_with_specific_assignees(self):
        """Can create task with specific assignees."""
        other_user = User.objects.create_user(username='other', password='pass')
        other_profile = other_user.profile

        other_profile.department = self.dept

        other_profile.role = Role.objects.get(code='digital_employee')

        other_profile.save()

        self.client.force_authenticate(user=self.user)

        data = {
            'title': 'Task with assignees',
            'status': 'todo',
            'assigned_to_users': [other_user.id]
        }

        response = self.client.post('/api/tasks/', data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        task = Task.objects.get(id=response.data['id'])
        # Should have the specified assignee
        self.assertIn(other_user, task.assigned_to_users.all())


class TaskViewSetEdgeCasesTestCase(TestCase):
    """Test edge cases for Task ViewSet."""

    def setUp(self):
        self.client = APIClient()
        self.dept, _ = Department.objects.get_or_create(code='test', defaults={'name': 'Test'})

    def test_task_without_department_only_admin(self):
        """Task without department only accessible to admin."""
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

        task = Task.objects.create(
            title='No dept task',
            department=None,
            created_by=employee
        )
        task.assigned_to_users.add(employee)

        # Admin can see
        self.client.force_authenticate(user=admin)
        response = self.client.get(f'/api/tasks/{task.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Employee cannot (even though creator)
        self.client.force_authenticate(user=employee)
        response = self.client.get(f'/api/tasks/{task.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_without_profile_gets_empty_list(self):
        """User without profile gets empty list."""
        user = User.objects.create_user(username='noprofile', password='pass')

        Task.objects.create(
            title='Task',
            department=self.dept,
            created_by=user
        )

        self.client.force_authenticate(user=user)
        response = self.client.get('/api/tasks/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)

    def test_task_with_no_assigned_users_visible_to_creator(self):
        """Task with no assigned users is visible to creator."""
        user = User.objects.create_user(username='user', password='pass')
        profile = user.profile

        profile.department = self.dept

        profile.role = Role.objects.get(code='digital_employee')

        profile.save()

        task = Task.objects.create(
            title='No assignees',
            department=self.dept,
            created_by=user
        )
        # Explicitly clear assigned users
        task.assigned_to_users.clear()

        self.client.force_authenticate(user=user)
        response = self.client.get('/api/tasks/')

        task_ids = [t['id'] for t in response.data['results']]
        self.assertIn(task.id, task_ids)

    def test_distinct_prevents_duplicate_results(self):
        """Tasks should not appear multiple times if user matches multiple criteria."""
        user = User.objects.create_user(username='user', password='pass')
        profile = user.profile

        profile.department = self.dept

        profile.role = Role.objects.get(code='digital_employee')

        profile.save()

        # Create task where user is both creator AND assigned
        task = Task.objects.create(
            title='Task',
            department=self.dept,
            created_by=user
        )
        task.assigned_to_users.add(user)

        self.client.force_authenticate(user=user)
        response = self.client.get('/api/tasks/')

        # Count how many times this task appears
        task_ids = [t['id'] for t in response.data['results']]
        count = task_ids.count(task.id)

        # Should appear only once
        self.assertEqual(count, 1)
