"""
Comprehensive tests for base permission classes.

Tests cover:
- BaseResourcePermission enforcement
- DepartmentScopedPermission scenarios
- OwnershipPermission scenarios
- Edge cases and security vulnerabilities
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory
from rest_framework import permissions
from unittest.mock import Mock

from api.permissions import (
    BaseResourcePermission,
    DepartmentScopedPermission,
    OwnershipPermission
)
from api.models import Department, Role, UserProfile


User = get_user_model()


class BaseResourcePermissionTestCase(TestCase):
    """Test that BaseResourcePermission enforces has_object_permission implementation."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.department, _ = Department.objects.get_or_create(code='test', defaults={'name': 'Test Dept'})
        self.profile = self.user.profile
        self.profile.department = self.department
        self.profile.role = Role.objects.get(code='digital_employee')
        self.profile.save()

    def test_base_permission_raises_not_implemented_error(self):
        """BaseResourcePermission must raise NotImplementedError for has_object_permission."""
        permission = BaseResourcePermission()
        request = self.factory.get('/')
        request.user = self.user

        mock_view = Mock()
        mock_obj = Mock()

        with self.assertRaises(NotImplementedError) as cm:
            permission.has_object_permission(request, mock_view, mock_obj)

        self.assertIn('must implement has_object_permission', str(cm.exception))

    def test_subclass_must_implement_has_object_permission(self):
        """Subclasses that don't implement has_object_permission should fail."""

        class IncompletePermission(BaseResourcePermission):
            pass

        permission = IncompletePermission()
        request = self.factory.get('/')
        request.user = self.user

        mock_view = Mock()
        mock_obj = Mock()

        with self.assertRaises(NotImplementedError):
            permission.has_object_permission(request, mock_view, mock_obj)


class DepartmentScopedPermissionTestCase(TestCase):
    """Comprehensive tests for DepartmentScopedPermission."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.permission = DepartmentScopedPermission()

        # Create departments
        self.dept_digital, _ = Department.objects.get_or_create(code='digital', defaults={'name': 'Digital'})
        self.dept_sales, _ = Department.objects.get_or_create(code='sales', defaults={'name': 'Sales'})

        # Create users with different roles
        self.admin = User.objects.create_user(username='admin', password='pass')
        self.admin_profile = self.admin.profile
        self.admin_profile.department = self.dept_digital
        self.admin_profile.role = Role.objects.get(code='administrator')
        self.admin_profile.save()

        self.manager = User.objects.create_user(username='manager', password='pass')
        self.manager_profile = self.manager.profile
        self.manager_profile.department = self.dept_digital
        self.manager_profile.role = Role.objects.get(code='digital_manager')
        self.manager_profile.save()

        self.employee = User.objects.create_user(username='employee', password='pass')
        self.employee_profile = self.employee.profile
        self.employee_profile.department = self.dept_digital
        self.employee_profile.role = Role.objects.get(code='digital_employee')
        self.employee_profile.save()

        self.other_dept_employee = User.objects.create_user(username='other', password='pass')
        self.other_profile = self.other_dept_employee.profile
        self.other_profile.department = self.dept_sales
        self.other_profile.role = Role.objects.get(code='digital_employee')
        self.other_profile.save()

        self.no_dept_user = User.objects.create_user(username='nodept', password='pass')
        self.no_dept_profile = self.no_dept_user.profile
        self.no_dept_profile.department = None
        self.no_dept_profile.role = Role.objects.get(code='digital_employee')
        self.no_dept_profile.save()

        self.no_profile_user = User.objects.create_user(username='noprofile', password='pass')

        # Create mock objects
        self.obj_with_dept = Mock()
        self.obj_with_dept.department = self.dept_digital

        self.obj_other_dept = Mock()
        self.obj_other_dept.department = self.dept_sales

        self.obj_no_dept = Mock()
        self.obj_no_dept.department = None

    def test_admin_can_access_any_department(self):
        """Admin can access objects from any department."""
        request = self.factory.get('/')
        request.user = self.admin
        mock_view = Mock()

        # Admin can access own department
        self.assertTrue(
            self.permission.has_object_permission(request, mock_view, self.obj_with_dept)
        )

        # Admin can access other department
        self.assertTrue(
            self.permission.has_object_permission(request, mock_view, self.obj_other_dept)
        )

        # Admin can access no department objects
        self.assertTrue(
            self.permission.has_object_permission(request, mock_view, self.obj_no_dept)
        )

    def test_manager_can_access_own_department(self):
        """Manager can access objects in their department."""
        request = self.factory.get('/')
        request.user = self.manager
        mock_view = Mock()

        self.assertTrue(
            self.permission.has_object_permission(request, mock_view, self.obj_with_dept)
        )

    def test_manager_cannot_access_other_department(self):
        """Manager cannot access objects from other departments."""
        request = self.factory.get('/')
        request.user = self.manager
        mock_view = Mock()

        self.assertFalse(
            self.permission.has_object_permission(request, mock_view, self.obj_other_dept)
        )

    def test_employee_can_access_own_department(self):
        """Employee can access objects in their department."""
        request = self.factory.get('/')
        request.user = self.employee
        mock_view = Mock()

        self.assertTrue(
            self.permission.has_object_permission(request, mock_view, self.obj_with_dept)
        )

    def test_employee_cannot_access_other_department(self):
        """Employee cannot access objects from other departments."""
        request = self.factory.get('/')
        request.user = self.employee
        mock_view = Mock()

        self.assertFalse(
            self.permission.has_object_permission(request, mock_view, self.obj_other_dept)
        )

    def test_user_without_department_denied(self):
        """User without department cannot access any objects."""
        request = self.factory.get('/')
        request.user = self.no_dept_user
        mock_view = Mock()

        self.assertFalse(
            self.permission.has_object_permission(request, mock_view, self.obj_with_dept)
        )

    def test_user_without_profile_denied(self):
        """User without profile cannot access any objects."""
        request = self.factory.get('/')
        request.user = self.no_profile_user
        mock_view = Mock()

        self.assertFalse(
            self.permission.has_object_permission(request, mock_view, self.obj_with_dept)
        )

    def test_object_without_department_denied(self):
        """Objects without department are denied to non-admins."""
        request = self.factory.get('/')
        request.user = self.employee
        mock_view = Mock()

        self.assertFalse(
            self.permission.has_object_permission(request, mock_view, self.obj_no_dept)
        )

    def test_safe_methods_same_as_write_methods(self):
        """DepartmentScopedPermission treats all methods equally."""
        get_request = self.factory.get('/')
        get_request.user = self.employee

        post_request = self.factory.post('/')
        post_request.user = self.employee

        mock_view = Mock()

        # Both should have same result
        self.assertEqual(
            self.permission.has_object_permission(get_request, mock_view, self.obj_with_dept),
            self.permission.has_object_permission(post_request, mock_view, self.obj_with_dept)
        )


class OwnershipPermissionTestCase(TestCase):
    """Comprehensive tests for OwnershipPermission."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.permission = OwnershipPermission()

        # Create departments
        self.dept_digital, _ = Department.objects.get_or_create(code='digital', defaults={'name': 'Digital'})
        self.dept_sales, _ = Department.objects.get_or_create(code='sales', defaults={'name': 'Sales'})

        # Create users
        self.admin = User.objects.create_user(username='admin', password='pass')
        self.admin_profile = self.admin.profile
        self.admin_profile.department = self.dept_digital
        self.admin_profile.role = Role.objects.get(code='administrator')
        self.admin_profile.save()

        self.manager = User.objects.create_user(username='manager', password='pass')
        self.manager_profile = self.manager.profile
        self.manager_profile.department = self.dept_digital
        self.manager_profile.role = Role.objects.get(code='digital_manager')
        self.manager_profile.save()

        self.employee_owner = User.objects.create_user(username='owner', password='pass')
        self.owner_profile = self.employee_owner.profile
        self.owner_profile.department = self.dept_digital
        self.owner_profile.role = Role.objects.get(code='digital_employee')
        self.owner_profile.save()

        self.employee_assigned = User.objects.create_user(username='assigned', password='pass')
        self.assigned_profile = self.employee_assigned.profile
        self.assigned_profile.department = self.dept_digital
        self.assigned_profile.role = Role.objects.get(code='digital_employee')
        self.assigned_profile.save()

        self.employee_other = User.objects.create_user(username='other', password='pass')
        self.other_profile = self.employee_other.profile
        self.other_profile.department = self.dept_digital
        self.other_profile.role = Role.objects.get(code='digital_employee')
        self.other_profile.save()

        self.wrong_dept_employee = User.objects.create_user(username='wrongdept', password='pass')
        self.wrong_dept_profile = self.wrong_dept_employee.profile
        self.wrong_dept_profile.department = self.dept_sales
        self.wrong_dept_profile.role = Role.objects.get(code='digital_employee')
        self.wrong_dept_profile.save()

    def test_admin_bypass_ownership_checks(self):
        """Admin can access any object regardless of ownership."""
        obj = Mock()
        obj.department = self.dept_digital
        obj.created_by = self.employee_owner

        request = self.factory.get('/')
        request.user = self.admin
        mock_view = Mock()

        self.assertTrue(
            self.permission.has_object_permission(request, mock_view, obj)
        )

    def test_manager_can_access_all_in_department(self):
        """Manager can access all objects in their department regardless of ownership."""
        obj = Mock()
        obj.department = self.dept_digital
        obj.created_by = self.employee_owner

        request = self.factory.get('/')
        request.user = self.manager
        mock_view = Mock()

        self.assertTrue(
            self.permission.has_object_permission(request, mock_view, obj)
        )

    def test_manager_cannot_access_other_department(self):
        """Manager cannot access objects from other departments."""
        obj = Mock()
        obj.department = self.dept_sales
        obj.created_by = self.employee_owner

        request = self.factory.get('/')
        request.user = self.manager
        mock_view = Mock()

        self.assertFalse(
            self.permission.has_object_permission(request, mock_view, obj)
        )

    def test_employee_can_access_owned_object(self):
        """Employee can access objects they created."""
        obj = Mock()
        obj.department = self.dept_digital
        obj.created_by = self.employee_owner

        request = self.factory.get('/')
        request.user = self.employee_owner
        mock_view = Mock()

        self.assertTrue(
            self.permission.has_object_permission(request, mock_view, obj)
        )

    def test_employee_cannot_access_not_owned_object(self):
        """Employee cannot access objects they didn't create and aren't assigned to."""
        obj = Mock()
        obj.department = self.dept_digital
        obj.created_by = self.employee_owner

        request = self.factory.get('/')
        request.user = self.employee_other
        mock_view = Mock()
        mock_view.assigned_field = None  # No assignment field

        self.assertFalse(
            self.permission.has_object_permission(request, mock_view, obj)
        )

    def test_employee_wrong_department_denied(self):
        """Employee from wrong department cannot access even if they're the owner."""
        obj = Mock()
        obj.department = self.dept_digital
        obj.created_by = self.wrong_dept_employee

        request = self.factory.get('/')
        request.user = self.wrong_dept_employee
        mock_view = Mock()

        self.assertFalse(
            self.permission.has_object_permission(request, mock_view, obj)
        )

    def test_employee_can_access_assigned_object_through_model(self):
        """Employee can access objects they're assigned to via through model."""
        # Mock object with through model assignment
        obj = Mock()
        obj.department = self.dept_digital
        obj.created_by = self.employee_owner

        # Mock the through model queryset
        mock_through_qs = Mock()
        mock_through_qs.filter.return_value.exists.return_value = True
        obj.handlers = mock_through_qs

        request = self.factory.get('/')
        request.user = self.employee_assigned
        mock_view = Mock()
        mock_view.assigned_field = 'handlers'
        mock_view.assigned_through_field = 'user'

        self.assertTrue(
            self.permission.has_object_permission(request, mock_view, obj)
        )

    def test_employee_can_access_assigned_object_direct_m2m(self):
        """Employee can access objects they're assigned to via direct M2M."""
        # Mock object with direct M2M assignment
        obj = Mock()
        obj.department = self.dept_digital
        obj.created_by = self.employee_owner

        # Mock direct M2M queryset
        mock_m2m_qs = Mock()
        mock_m2m_qs.filter.return_value.exists.return_value = True
        obj.assigned_to_users = mock_m2m_qs

        request = self.factory.get('/')
        request.user = self.employee_assigned
        mock_view = Mock()
        mock_view.assigned_field = 'assigned_to_users'
        mock_view.assigned_through_field = None  # Direct M2M

        self.assertTrue(
            self.permission.has_object_permission(request, mock_view, obj)
        )

    def test_employee_not_assigned_via_through_model_denied(self):
        """Employee not assigned via through model is denied."""
        obj = Mock()
        obj.department = self.dept_digital
        obj.created_by = self.employee_owner

        # Mock assignment check returning False
        mock_through_qs = Mock()
        mock_through_qs.filter.return_value.exists.return_value = False
        obj.handlers = mock_through_qs

        request = self.factory.get('/')
        request.user = self.employee_other
        mock_view = Mock()
        mock_view.assigned_field = 'handlers'
        mock_view.assigned_through_field = 'user'

        self.assertFalse(
            self.permission.has_object_permission(request, mock_view, obj)
        )

    def test_read_write_distinction_for_employees(self):
        """For employees, read and write permissions should be the same (both require ownership/assignment)."""
        obj = Mock()
        obj.department = self.dept_digital
        obj.created_by = self.employee_owner

        get_request = self.factory.get('/')
        get_request.user = self.employee_owner

        post_request = self.factory.post('/')
        post_request.user = self.employee_owner

        mock_view = Mock()

        # Both should pass for owner
        self.assertTrue(
            self.permission.has_object_permission(get_request, mock_view, obj)
        )
        self.assertTrue(
            self.permission.has_object_permission(post_request, mock_view, obj)
        )

    def test_no_created_by_field_handled_gracefully(self):
        """Objects without created_by field should not crash."""
        obj = Mock()
        obj.department = self.dept_digital
        obj.created_by = None

        request = self.factory.get('/')
        request.user = self.employee_other
        mock_view = Mock()
        mock_view.assigned_field = None

        # Should deny access when no owner and not assigned
        self.assertFalse(
            self.permission.has_object_permission(request, mock_view, obj)
        )

    def test_no_department_field_denies_access(self):
        """Objects without department field deny access to non-admins."""
        obj = Mock()
        obj.department = None
        obj.created_by = self.employee_owner

        request = self.factory.get('/')
        request.user = self.employee_owner
        mock_view = Mock()

        self.assertFalse(
            self.permission.has_object_permission(request, mock_view, obj)
        )

    def test_admin_can_access_object_without_department(self):
        """Admin can access objects even without department."""
        obj = Mock()
        obj.department = None
        obj.created_by = self.employee_owner

        request = self.factory.get('/')
        request.user = self.admin
        mock_view = Mock()

        self.assertTrue(
            self.permission.has_object_permission(request, mock_view, obj)
        )


class PermissionEdgeCasesTestCase(TestCase):
    """Test edge cases and potential security vulnerabilities."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.dept, _ = Department.objects.get_or_create(code='test', defaults={'name': 'Test'})

    def test_user_with_deleted_profile(self):
        """User profiles cannot be deleted - ProtectedError should be raised."""
        user = User.objects.create_user(username='test', password='pass')
        profile = user.profile
        profile.department = self.dept
        profile.role = Role.objects.get(code='digital_employee')
        profile.save()

        # Attempt to delete profile should raise ProtectedError
        from django.db.models.deletion import ProtectedError
        with self.assertRaises(ProtectedError) as context:
            profile.delete()

        # Verify the error message is clear
        self.assertIn("Cannot delete UserProfile", str(context.exception))

    def test_user_with_deleted_department(self):
        """User whose department was deleted should be denied."""
        user = User.objects.create_user(username='test', password='pass')
        dept, _ = Department.objects.get_or_create(code='todelete', defaults={'name': 'ToDelete'})
        profile = user.profile
        profile.department = dept
        profile.role = Role.objects.get(code='digital_employee')
        profile.save()

        # Simulate deleted department by removing it from profile
        profile.department = None
        profile.save()

        permission = DepartmentScopedPermission()
        request = self.factory.get('/')
        request.user = user
        mock_view = Mock()
        mock_obj = Mock()
        mock_obj.department = self.dept

        self.assertFalse(
            permission.has_object_permission(request, mock_view, mock_obj)
        )

    def test_guest_role_with_department(self):
        """Guest role should behave like employee (no special treatment)."""
        user = User.objects.create_user(username='guest', password='pass')
        profile = user.profile
        profile.department = self.dept
        profile.role = Role.objects.get(code='guest')
        profile.save()

        obj = Mock()
        obj.department = self.dept
        obj.created_by = user

        permission = OwnershipPermission()
        request = self.factory.get('/')
        request.user = user
        mock_view = Mock()

        # Guest can access their own objects
        self.assertTrue(
            permission.has_object_permission(request, mock_view, obj)
        )

    def test_role_level_precedence(self):
        """Higher role levels should have more access."""
        admin = User.objects.create_user(username='admin', password='pass')
        admin_profile = admin.profile
        admin_profile.department = self.dept
        admin_profile.role = Role.objects.get(code='administrator')
        admin_profile.save()

        manager = User.objects.create_user(username='manager', password='pass')
        manager_profile = manager.profile
        manager_profile.department = self.dept
        manager_profile.role = Role.objects.get(code='digital_manager')
        manager_profile.save()

        employee = User.objects.create_user(username='employee', password='pass')
        employee_profile = employee.profile
        employee_profile.department = self.dept
        employee_profile.role = Role.objects.get(code='digital_employee')
        employee_profile.save()

        other_user = User.objects.create_user(username='other', password='pass')
        other_profile = other_user.profile
        other_profile.department = self.dept
        other_profile.role = Role.objects.get(code='digital_employee')
        other_profile.save()

        obj = Mock()
        obj.department = self.dept
        obj.created_by = other_user

        permission = OwnershipPermission()
        mock_view = Mock()
        mock_view.assigned_field = None

        # Admin can access
        admin_request = self.factory.get('/')
        admin_request.user = admin
        self.assertTrue(permission.has_object_permission(admin_request, mock_view, obj))

        # Manager can access
        manager_request = self.factory.get('/')
        manager_request.user = manager
        self.assertTrue(permission.has_object_permission(manager_request, mock_view, obj))

        # Employee (not owner) cannot access
        employee_request = self.factory.get('/')
        employee_request.user = employee
        self.assertFalse(permission.has_object_permission(employee_request, mock_view, obj))
