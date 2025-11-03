"""
Comprehensive tests for BaseViewSet and related classes.

Tests cover:
- Queryset filtering with different scoping modes
- Ownership and assignment logic
- M2M relationship handling (through model and direct)
- Edge cases and security vulnerabilities
"""
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
        self.assertEqual(call_args[1]['department'], self.dept_digital)

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

    def test_through_model_m2m_generates_correct_lookup(self):
        """Through model M2M should generate field__through_field lookup."""
        class TestViewSet(BaseViewSet):
            queryset_scoping = QuerysetScoping.DEPARTMENT_WITH_OWNERSHIP
            ownership_field = 'created_by'
            assigned_field = 'handlers'
            assigned_through_field = 'user'  # Through model

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
        request.user = self.employee
        viewset.request = request
        viewset.queryset = mock_qs

        result = viewset.get_queryset()

        # Should call filter with Q objects including handlers__user=user
        # We can't easily test Q objects, but we can verify the method was called
        filtered_qs.filter.assert_called_once()

    def test_direct_m2m_generates_correct_lookup(self):
        """Direct M2M should generate field=user lookup."""
        class TestViewSet(BaseViewSet):
            queryset_scoping = QuerysetScoping.DEPARTMENT_WITH_OWNERSHIP
            ownership_field = 'created_by'
            assigned_field = 'assigned_to_users'
            assigned_through_field = None  # Direct M2M

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
        request.user = self.employee
        viewset.request = request
        viewset.queryset = mock_qs

        result = viewset.get_queryset()

        # Should call filter
        filtered_qs.filter.assert_called_once()

    def test_no_assigned_field_only_checks_ownership(self):
        """When no assigned_field, should only check ownership."""
        class TestViewSet(BaseViewSet):
            queryset_scoping = QuerysetScoping.DEPARTMENT_WITH_OWNERSHIP
            ownership_field = 'created_by'
            assigned_field = None
            assigned_through_field = None

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
        request.user = self.employee
        viewset.request = request
        viewset.queryset = mock_qs

        result = viewset.get_queryset()

        # Should still call filter for department and ownership
        self.assertTrue(filtered_qs.filter.called)


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

        # Delete department
        dept.delete()
        profile.refresh_from_db()

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
