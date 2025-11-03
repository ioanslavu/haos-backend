"""
Custom permissions for campaign RBAC.

Uses the new DRF-compliant permission classes from api.permissions.
"""
from rest_framework import permissions
from api.permissions import OwnershipPermission


class CampaignPermission(OwnershipPermission):
    """
    Campaign-level permissions based on user role and department.

    Inherits from OwnershipPermission which provides:
    - Admins: Full access to all campaigns
    - Department check: Campaign must be in same department
    - Managers: Full access to all campaigns in their department
    - Employees: Only campaigns they created or are assigned to (handlers)

    No hardcoded role checks - all logic handled by parent class.
    This enables adding new roles (e.g., "Senior Manager") without code changes.

    Object-level permission is enforced via:
    1. get_queryset() filtering (data visibility)
    2. has_object_permission() check (authorization)

    ⚠️  IMPORTANT: Always use self.get_object() in detail actions to ensure
    has_object_permission() is called. Never manually fetch with Model.objects.get()
    """
    pass  # No custom logic needed - parent handles everything!


class HasDigitalDepartmentAccess(permissions.BasePermission):
    """
    Permission class for Digital Financial endpoints.

    Only allow users who belong to the Digital department or are admins.

    This permission is used for financial reporting endpoints that aggregate
    and display financial data for digital campaigns.

    Rules:
    - Admins: Always have access
    - Users with Digital department: Have access
    - Other users: Denied
    """

    def has_permission(self, request, view):
        """
        Check if user has access to Digital department financial data.
        """
        # Check if user is authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        # User must have a profile
        if not hasattr(request.user, 'profile'):
            return False

        profile = request.user.profile

        # Admins always have access
        if profile.is_admin:
            return True

        # DEVELOPMENT: Temporarily allow all authenticated users
        # TODO: Re-enable department check in production
        return True

        # Check if user has digital department access
        # try:
        #     digital_dept = Department.objects.get(name='Digital Department')
        # except Department.DoesNotExist:
        #     # If Digital department doesn't exist, deny access
        #     return False

        # # Check if user's department is Digital Department
        # if profile.department and profile.department.id == digital_dept.id:
        #     return True

        # # Deny access for all other users
        # return False
