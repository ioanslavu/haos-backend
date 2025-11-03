"""
Permission classes for CRM extensions (Tasks, Activities, EntityChangeRequests).
"""
from rest_framework import permissions
from api.permissions import OwnershipPermission, DepartmentScopedPermission, BaseResourcePermission


class TaskPermission(OwnershipPermission):
    """
    Task permissions with ownership and assignment.

    Inherits from OwnershipPermission which provides:
    - Admins: Full access to all tasks
    - Department check: Task must be in same department
    - Managers: Full access to all tasks in their department
    - Employees: Only tasks they created or are assigned to

    No hardcoded role checks - all logic handled by parent class.

    Note: Tasks use direct M2M (assigned_to_users) not through model.
    The BaseViewSet handles this automatically via assigned_through_field=None.
    """
    pass  # No custom logic needed!


class ActivityPermission(DepartmentScopedPermission):
    """
    Activity permissions.

    All department users can view/create/edit activities in their department.
    No ownership restrictions - activities are shared within the department.

    Inherits from DepartmentScopedPermission which provides:
    - Admins: Full access to all activities
    - Department users: Can access activities in their department
    """
    pass  # No custom logic needed!


class EntityChangeRequestPermission(BaseResourcePermission):
    """
    EntityChangeRequest permissions.

    Simple ownership-based permission:
    - Admins: Can view all requests and approve/reject
    - Regular users: Can create requests and view their own requests
    - Only admins can approve/reject requests

    No department scoping - requests are global but ownership-based.
    """

    def has_object_permission(self, request, view, obj):
        """
        Check if user can access this change request.

        - Admins: Full access
        - Owner: Can view their own requests
        - Others: No access
        """
        user = request.user
        profile = user.profile

        # Admins have full access
        if profile.is_admin:
            return True

        # Read access: users can view their own requests
        if request.method in permissions.SAFE_METHODS:
            return obj.requested_by == user

        # Write access: users can update their own requests (if not yet processed)
        # Note: approve/reject actions have additional checks in the action methods
        return obj.requested_by == user
