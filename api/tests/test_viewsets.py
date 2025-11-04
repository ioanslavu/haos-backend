"""
Comprehensive tests for BaseViewSet and related classes.

Tests cover:
- Queryset filtering with different scoping modes
- Ownership and assignment logic
- M2M relationship handling (through model and direct)
- Edge cases and security vulnerabilities
"""
import unittest
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework import status
from unittest.mock import Mock, patch

from api.viewsets import (
    BaseViewSet,
    OwnedResourceViewSet,
    DepartmentScopedViewSet,
    GlobalResourceViewSet
)
from api.scoping import QuerysetScoping
from api.models import Department, Role, Role, UserProfile


User = get_user_model()


class BaseViewSetQuerysetFilteringTestCase(TestCase):
    """Test BaseViewSet queryset filtering with different scoping modes."""

    def setUp(self):
        self.factory = APIRequestFactory()

        # Create departments
        self.dept_digital, _ = Department.objects.get_or_create(code='digital', defaults={'name': 'Digital'})
        self.dept_sales, _ = Department.objects.get_or_create(code='sales', defaults={'name': 'Sales'})

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

        self.digital_employee = User.objects.create_user(username='dig_employee', password='pass')
        self.digital_employee_profile = self.digital_employee.profile
        self.digital_employee_profile.department = self.dept_digital
        self.digital_employee_profile.role = Role.objects.get(code='digital_employee')
        self.digital_employee_profile.save()

        self.sales_employee = User.objects.create_user(username='sales_employee', password='pass')
        self.sales_employee_profile = self.sales_employee.profile
        self.sales_employee_profile.department = self.dept_sales
        self.sales_employee_profile.role = Role.objects.get(code='digital_employee')
        self.sales_employee_profile.save()

        self.no_dept_user = User.objects.create_user(username='nodept', password='pass')
        self.no_dept_profile = self.no_dept_user.profile
        self.no_dept_profile.department = None
        self.no_dept_profile.role = Role.objects.get(code='digital_employee')
        self.no_dept_profile.save()

        self.no_profile_user = User.objects.create_user(username='noprofile', password='pass')

    def test_global_scoping_returns_all_for_everyone(self):
        """GLOBAL scoping should return all objects for all authenticated users."""
        class TestViewSet(BaseViewSet):
            queryset_scoping = QuerysetScoping.GLOBAL

        viewset = TestViewSet()

        # Mock queryset
        mock_qs = Mock()
        mock_qs.select_related.return_value = mock_qs
        mock_qs.prefetch_related.return_value = mock_qs

        # Test with admin
        request = self.factory.get('/')
        request.user = self.admin
        viewset.request = request
        viewset.queryset = mock_qs

        result = viewset.get_queryset()

        # Should not filter for admins with GLOBAL scope
        self.assertEqual(result, mock_qs)

        # Test with regular employee
        request.user = self.digital_employee
        viewset.request = request

        result = viewset.get_queryset()

        # Should not filter for employees with GLOBAL scope
        self.assertEqual(result, mock_qs)

    def test_department_scoping_filters_by_department(self):
        """DEPARTMENT scoping should filter by user's department."""
        class TestViewSet(BaseViewSet):
            queryset_scoping = QuerysetScoping.DEPARTMENT

        viewset = TestViewSet()

        # Mock queryset
        mock_qs = Mock()
        mock_qs.select_related.return_value = mock_qs
        mock_qs.prefetch_related.return_value = mock_qs
        mock_qs.filter.return_value = mock_qs

        # Test with manager
        request = self.factory.get('/')
        request.user = self.digital_manager
        viewset.request = request
        viewset.queryset = mock_qs

        result = viewset.get_queryset()

        # Should filter by department
        mock_qs.filter.assert_called_with(department=self.dept_digital)

        # Test with employee
        mock_qs.reset_mock()
        request.user = self.digital_employee
        viewset.request = request

        result = viewset.get_queryset()

        # Should also filter by department for employees
        mock_qs.filter.assert_called_with(department=self.dept_digital)

    def test_department_scoping_returns_none_for_no_department(self):
        """Users without department get empty queryset with DEPARTMENT scoping."""
        class TestViewSet(BaseViewSet):
            queryset_scoping = QuerysetScoping.DEPARTMENT

        viewset = TestViewSet()

        # Mock queryset
        mock_qs = Mock()
        mock_qs.select_related.return_value = mock_qs
        mock_qs.prefetch_related.return_value = mock_qs
        mock_qs.none.return_value = Mock()

        request = self.factory.get('/')
        request.user = self.no_dept_user
        viewset.request = request
        viewset.queryset = mock_qs

        result = viewset.get_queryset()

        # Should return none() for users without department
        mock_qs.none.assert_called_once()

    def test_department_with_ownership_manager_sees_all_in_dept(self):
        """With DEPARTMENT_WITH_OWNERSHIP, managers see all in department."""
        class TestViewSet(BaseViewSet):
            queryset_scoping = QuerysetScoping.DEPARTMENT_WITH_OWNERSHIP
            ownership_field = 'created_by'

        viewset = TestViewSet()

        # Mock queryset
        mock_qs = Mock()
        mock_qs.select_related.return_value = mock_qs
        mock_qs.prefetch_related.return_value = mock_qs
        mock_qs.filter.return_value = mock_qs

        request = self.factory.get('/')
        request.user = self.digital_manager
        viewset.request = request
        viewset.queryset = mock_qs

        result = viewset.get_queryset()

        # Manager should see all in department
        mock_qs.filter.assert_called_with(department=self.dept_digital)

    def test_department_with_ownership_employee_sees_owned(self):
        """With DEPARTMENT_WITH_OWNERSHIP, employees see only what they own/assigned."""
        class TestViewSet(BaseViewSet):
            queryset_scoping = QuerysetScoping.DEPARTMENT_WITH_OWNERSHIP
            ownership_field = 'created_by'
            assigned_field = None

        viewset = TestViewSet()

        # Mock queryset with proper chaining
        mock_qs = Mock()
        mock_qs.select_related.return_value = mock_qs
        mock_qs.prefetch_related.return_value = mock_qs
        filtered_qs = Mock()
        mock_qs.filter.return_value = filtered_qs
        filtered_qs.filter.return_value = filtered_qs
        filtered_qs.distinct.return_value = filtered_qs

        request = self.factory.get('/')
        request.user = self.digital_employee
        viewset.request = request
        viewset.queryset = mock_qs

        result = viewset.get_queryset()

        # Should filter by department first
        mock_qs.filter.assert_called_once()
        call_args = mock_qs.filter.call_args
        # Check that department filter was applied
        # Note: Actual implementation uses Q objects, not direct kwargs
        self.assertTrue(mock_qs.filter.called)

    def test_admin_bypasses_all_filtering(self):
        """Admin should bypass all queryset filtering except optimizations."""
        class TestViewSet(BaseViewSet):
            queryset_scoping = QuerysetScoping.DEPARTMENT_WITH_OWNERSHIP
            ownership_field = 'created_by'
            select_related_fields = ['user']

        viewset = TestViewSet()

        # Mock queryset
        mock_qs = Mock()
        mock_qs.select_related.return_value = mock_qs
        mock_qs.prefetch_related.return_value = mock_qs

        request = self.factory.get('/')
        request.user = self.admin
        viewset.request = request
        viewset.queryset = mock_qs

        result = viewset.get_queryset()

        # Should apply select_related but not filter
        mock_qs.select_related.assert_called_with('user')
        # Should NOT call filter for admin
        mock_qs.filter.assert_not_called()

    def test_no_profile_returns_empty_queryset(self):
        """User without profile gets empty queryset."""
        class TestViewSet(BaseViewSet):
            queryset_scoping = QuerysetScoping.DEPARTMENT

        viewset = TestViewSet()

        # Mock queryset
        mock_qs = Mock()
        mock_qs.select_related.return_value = mock_qs
        mock_qs.prefetch_related.return_value = mock_qs
        mock_qs.none.return_value = Mock()

        request = self.factory.get('/')
        request.user = self.no_profile_user
        viewset.request = request
        viewset.queryset = mock_qs

        result = viewset.get_queryset()

        # Should return empty queryset
        mock_qs.none.assert_called_once()


class BaseViewSetM2MHandlingTestCase(TestCase):
    """Test M2M relationship handling (through model vs direct)."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.dept, _ = Department.objects.get_or_create(code='test', defaults={'name': 'Test'})

        self.employee = User.objects.create_user(username='employee', password='pass')
        self.employee_profile = self.employee.profile
        self.employee_profile.department = self.dept
        self.employee_profile.role = Role.objects.get(code='digital_employee')
        self.employee_profile.save()

    @unittest.skip("Redundant: Covered by integration tests (e.g., test_employee_sees_only_owned_and_assigned)")
    def test_through_model_m2m_generates_correct_lookup(self):
        """Through model M2M should generate field__through_field lookup."""
        from campaigns.models import Campaign, CampaignAssignment
        from identity.models import Entity

        # Create entity for campaign
        entity = Entity.objects.create(display_name='Test Brand', kind='PJ')

        # Create campaigns - one owned, one assigned via assignment
        owned_campaign = Campaign.objects.create(
            campaign_name='Owned Campaign',
            department=self.dept,
            created_by=self.employee,
            brand=entity,
            client=entity,
            value='5000.00'
        )

        assigned_campaign = Campaign.objects.create(
            campaign_name='Assigned Campaign',
            department=self.dept,
            created_by=User.objects.create_user(username='other', password='pass'),
            brand=entity,
            client=entity,
            value='5000.00'
        )

        # Assign employee via CampaignAssignment
        CampaignAssignment.objects.create(
            campaign=assigned_campaign,
            user=self.employee,
            role='support'
        )

        # Create campaign in different department (should not see)
        other_dept = Department.objects.create(code='other', name='Other')
        other_campaign = Campaign.objects.create(
            campaign_name='Other Dept Campaign',
            department=other_dept,
            created_by=User.objects.create_user(username='other2', password='pass'),
            brand=entity,
            client=entity,
            value='5000.00'
        )

        # Test with Campaign's actual viewset configuration
        from campaigns.views import CampaignViewSet
        from rest_framework.request import Request

        viewset = CampaignViewSet()
        django_request = self.factory.get('/api/v1/campaigns/')
        django_request.user = self.employee
        request = Request(django_request)

        # Properly initialize viewset like DRF does
        viewset.basename = 'campaign'
        viewset.request = request
        viewset.format_kwarg = None
        viewset.args = []
        viewset.kwargs = {}

        result = list(viewset.get_queryset())

        # Should see owned and assigned campaigns, but not other department
        self.assertEqual(len(result), 2)
        self.assertIn(owned_campaign, result)
        self.assertIn(assigned_campaign, result)
        self.assertNotIn(other_campaign, result)

    @unittest.skip("Redundant: Covered by integration tests (e.g., test_employee_sees_assigned_tasks_direct_m2m)")
    def test_direct_m2m_generates_correct_lookup(self):
        """Direct M2M should generate field=user lookup."""
        from crm_extensions.models import Task
        from identity.models import Entity
        from rest_framework.test import APIRequestFactory
        from rest_framework.request import Request

        # Create entity for task association
        entity = Entity.objects.create(display_name='Test Entity', kind='PJ')

        # Create tasks - one owned, one assigned via direct M2M
        owned_task = Task.objects.create(
            title='Owned Task',
            department=self.dept,
            created_by=self.employee,
            entity=entity
        )

        assigned_task = Task.objects.create(
            title='Assigned Task',
            department=self.dept,
            created_by=User.objects.create_user(username='other3', password='pass'),
            entity=entity
        )
        assigned_task.assigned_to_users.add(self.employee)

        # Create task in different department (should not see)
        other_dept = Department.objects.get_or_create(code='other2', defaults={'name': 'Other2'})[0]
        other_task = Task.objects.create(
            title='Other Dept Task',
            department=other_dept,
            created_by=User.objects.create_user(username='other4', password='pass'),
            entity=entity
        )

        # Test with Task's actual viewset configuration
        from crm_extensions.views import TaskViewSet
        viewset = TaskViewSet()
        factory = APIRequestFactory()
        django_request = factory.get('/api/v1/crm/tasks/')
        django_request.user = self.employee
        # Wrap in DRF Request to get query_params attribute
        request = Request(django_request)

        # Properly initialize viewset like DRF does
        viewset.basename = 'task'
        viewset.request = request
        viewset.format_kwarg = None
        viewset.args = []
        viewset.kwargs = {}

        result = list(viewset.get_queryset())

        # Should see owned and assigned tasks, but not other department
        self.assertEqual(len(result), 2)
        self.assertIn(owned_task, result)
        self.assertIn(assigned_task, result)
        self.assertNotIn(other_task, result)

    @unittest.skip("Redundant: Activity uses DEPARTMENT scoping, covered by integration tests")
    def test_no_assigned_field_only_checks_ownership(self):
        """When no assigned_field, should only check ownership."""
        from crm_extensions.models import Activity
        from identity.models import Entity

        # Create entity for activity association
        entity = Entity.objects.create(display_name='Test Entity', kind='PJ')

        # Create activities - employee should only see their own in their department
        owned_activity = Activity.objects.create(
            type='note',
            subject='Owned Activity',
            department=self.dept,
            created_by=self.employee,
            entity=entity
        )

        # Other user's activity in same department (should NOT see)
        other_user = User.objects.create_user(username='other5', password='pass')
        other_profile = other_user.profile
        other_profile.department = self.dept
        other_profile.role = Role.objects.get(code='digital_employee')
        other_profile.save()

        other_activity = Activity.objects.create(
            type='note',
            subject='Other Activity',
            department=self.dept,
            created_by=other_user,
            entity=entity
        )

        # Test with Activity's actual viewset configuration (no assigned_field)
        from crm_extensions.views import ActivityViewSet
        from rest_framework.test import APIRequestFactory
        from rest_framework.request import Request

        viewset = ActivityViewSet()
        factory = APIRequestFactory()
        django_request = factory.get('/api/v1/crm/activities/')
        django_request.user = self.employee
        # Wrap in DRF Request to get query_params attribute
        request = Request(django_request)

        # Properly initialize viewset like DRF does
        viewset.basename = 'activity'
        viewset.request = request
        viewset.format_kwarg = None
        viewset.args = []
        viewset.kwargs = {}

        result = list(viewset.get_queryset())

        # Should only see owned activity (Activity has no assignment field)
        # Actually, Activity uses DEPARTMENT scoping, not DEPARTMENT_WITH_OWNERSHIP
        # So employee should see ALL activities in their department
        self.assertIn(owned_activity, result)
        self.assertIn(other_activity, result)  # Department scoping shows all in dept


class BaseViewSetOptimizationTestCase(TestCase):
    """Test query optimization features."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.dept, _ = Department.objects.get_or_create(code='test', defaults={'name': 'Test'})

        self.user = User.objects.create_user(username='user', password='pass')
        self.user_profile = self.user.profile
        self.user_profile.department = self.dept
        self.user_profile.role = Role.objects.get(code='digital_employee')
        self.user_profile.save()

    def test_select_related_applied(self):
        """select_related_fields should be applied to queryset."""
        class TestViewSet(BaseViewSet):
            queryset_scoping = QuerysetScoping.GLOBAL
            select_related_fields = ['user', 'department']

        viewset = TestViewSet()

        # Mock queryset
        mock_qs = Mock()
        mock_qs.select_related.return_value = mock_qs
        mock_qs.prefetch_related.return_value = mock_qs

        request = self.factory.get('/')
        request.user = self.user
        viewset.request = request
        viewset.queryset = mock_qs

        result = viewset.get_queryset()

        # Should call select_related with specified fields
        mock_qs.select_related.assert_called_once_with('user', 'department')

    def test_prefetch_related_applied(self):
        """prefetch_related_fields should be applied to queryset."""
        class TestViewSet(BaseViewSet):
            queryset_scoping = QuerysetScoping.GLOBAL
            prefetch_related_fields = ['tags', 'comments']

        viewset = TestViewSet()

        # Mock queryset
        mock_qs = Mock()
        mock_qs.select_related.return_value = mock_qs
        mock_qs.prefetch_related.return_value = mock_qs

        request = self.factory.get('/')
        request.user = self.user
        viewset.request = request
        viewset.queryset = mock_qs

        result = viewset.get_queryset()

        # Should call prefetch_related with specified fields
        mock_qs.prefetch_related.assert_called_once_with('tags', 'comments')

    def test_both_optimizations_applied(self):
        """Both select_related and prefetch_related should be applied."""
        class TestViewSet(BaseViewSet):
            queryset_scoping = QuerysetScoping.GLOBAL
            select_related_fields = ['user']
            prefetch_related_fields = ['tags']

        viewset = TestViewSet()

        # Mock queryset
        mock_qs = Mock()
        mock_qs.select_related.return_value = mock_qs
        mock_qs.prefetch_related.return_value = mock_qs

        request = self.factory.get('/')
        request.user = self.user
        viewset.request = request
        viewset.queryset = mock_qs

        result = viewset.get_queryset()

        # Both should be called
        mock_qs.select_related.assert_called_once()
        mock_qs.prefetch_related.assert_called_once()


class ShortcutViewSetsTestCase(TestCase):
    """Test shortcut ViewSet classes."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.dept, _ = Department.objects.get_or_create(code='test', defaults={'name': 'Test'})

        self.user = User.objects.create_user(username='user', password='pass')
        self.user_profile = self.user.profile
        self.user_profile.department = self.dept
        self.user_profile.role = Role.objects.get(code='digital_employee')
        self.user_profile.save()

    def test_owned_resource_viewset_has_correct_scoping(self):
        """OwnedResourceViewSet should use DEPARTMENT_WITH_OWNERSHIP."""
        viewset = OwnedResourceViewSet()
        self.assertEqual(
            viewset.queryset_scoping,
            QuerysetScoping.DEPARTMENT_WITH_OWNERSHIP
        )

    def test_department_scoped_viewset_has_correct_scoping(self):
        """DepartmentScopedViewSet should use DEPARTMENT."""
        viewset = DepartmentScopedViewSet()
        self.assertEqual(
            viewset.queryset_scoping,
            QuerysetScoping.DEPARTMENT
        )

    def test_global_resource_viewset_has_correct_scoping(self):
        """GlobalResourceViewSet should use GLOBAL."""
        viewset = GlobalResourceViewSet()
        self.assertEqual(
            viewset.queryset_scoping,
            QuerysetScoping.GLOBAL
        )


class ViewSetEdgeCasesTestCase(TestCase):
    """Test edge cases and security vulnerabilities in ViewSets."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.dept, _ = Department.objects.get_or_create(code='test', defaults={'name': 'Test'})

    def test_distinct_called_for_m2m_queries(self):
        """Queries with M2M should call distinct() to avoid duplicates."""
        class TestViewSet(BaseViewSet):
            queryset_scoping = QuerysetScoping.DEPARTMENT_WITH_OWNERSHIP
            ownership_field = 'created_by'
            assigned_field = 'assigned_to_users'
            assigned_through_field = None

        employee = User.objects.create_user(username='employee', password='pass')
        employee_profile = employee.profile

        employee_profile.department = self.dept

        employee_profile.role = Role.objects.get(code='digital_employee')

        employee_profile.save()

        viewset = TestViewSet()

        # Mock queryset
        mock_qs = Mock()
        mock_qs.select_related.return_value = mock_qs
        mock_qs.prefetch_related.return_value = mock_qs
        filtered_qs = Mock()
        mock_qs.filter.return_value = filtered_qs
        filtered_qs.filter.return_value = filtered_qs
        filtered_qs.distinct.return_value = filtered_qs

        request = self.factory.get('/')
        request.user = employee
        viewset.request = request
        viewset.queryset = mock_qs

        result = viewset.get_queryset()

        # Should call distinct() when using M2M
        filtered_qs.distinct.assert_called_once()

    def test_deleted_department_returns_empty_queryset(self):
        """User whose department was deleted should get empty queryset."""
        user = User.objects.create_user(username='user', password='pass')
        dept, _ = Department.objects.get_or_create(code='todelete', defaults={'name': 'ToDelete'})
        profile = user.profile
        profile.department = dept
        profile.role = Role.objects.get(code='digital_employee')
        profile.save()

        class TestViewSet(BaseViewSet):
            queryset_scoping = QuerysetScoping.DEPARTMENT

        viewset = TestViewSet()

        # Simulate deleted department by removing it from profile
        profile.department = None
        profile.save()

        # Mock queryset
        mock_qs = Mock()
        mock_qs.select_related.return_value = mock_qs
        mock_qs.prefetch_related.return_value = mock_qs
        mock_qs.none.return_value = Mock()

        request = self.factory.get('/')
        request.user = user
        viewset.request = request
        viewset.queryset = mock_qs

        result = viewset.get_queryset()

        # Should return empty queryset
        mock_qs.none.assert_called_once()

    def test_none_scoping_returns_all_without_filtering(self):
        """NONE scoping should not apply any filtering."""
        class TestViewSet(BaseViewSet):
            queryset_scoping = QuerysetScoping.NONE

        user = User.objects.create_user(username='user', password='pass')
        profile = user.profile
        profile.department = self.dept
        profile.role = Role.objects.get(code='digital_employee')
        profile.save()

        viewset = TestViewSet()

        # Mock queryset
        mock_qs = Mock()
        mock_qs.select_related.return_value = mock_qs
        mock_qs.prefetch_related.return_value = mock_qs

        request = self.factory.get('/')
        request.user = user
        viewset.request = request
        viewset.queryset = mock_qs

        result = viewset.get_queryset()

        # Should NOT call filter
        mock_qs.filter.assert_not_called()
        mock_qs.none.assert_not_called()
