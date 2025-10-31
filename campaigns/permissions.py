"""
Custom permissions for campaign RBAC.
"""
from rest_framework import permissions
from api.models import Department


class CampaignPermission(permissions.BasePermission):
    """
    Campaign-level permissions based on user role and department.

    Rules:
    - Admins: Can view, edit, delete all campaigns
    - Department Managers: Can view, edit, delete campaigns from their department
    - Department Employees: Can view, edit, delete campaigns they created OR are assigned to (handlers)
    - Guests/No Department: No access
    """

    def has_permission(self, request, view):
        """
        Check if user has general permission to access campaigns.
        View-level filtering is handled in the ViewSet's get_queryset().
        """
        if not request.user or not request.user.is_authenticated:
            return False

        # User must have a profile
        if not hasattr(request.user, 'profile'):
            return False

        profile = request.user.profile

        # Admins always have access
        if profile.is_admin:
            return True

        # Users with a department have access (filtering handled in queryset)
        if profile.department:
            return True

        # Guests and users without departments have no access
        return False

    def has_object_permission(self, request, view, obj):
        """
        Check if user has permission to perform action on specific campaign object.

        Args:
            obj: Campaign instance
        """
        if not request.user or not request.user.is_authenticated:
            return False

        if not hasattr(request.user, 'profile'):
            return False

        profile = request.user.profile

        # Admins can do anything
        if profile.is_admin:
            return True

        # Campaign must belong to user's department
        if obj.department != profile.department:
            return False

        # Managers can do anything in their department
        if profile.is_manager:
            return True

        # Employees can only modify campaigns they created or are assigned to
        if profile.is_employee:
            # Check if user created the campaign
            if obj.created_by == request.user:
                return True

            # Check if user is assigned as a handler
            if obj.handlers.filter(user=request.user).exists():
                return True

            # Employee can view campaigns in their department (handled by queryset)
            # but cannot edit/delete campaigns they didn't create or aren't assigned to
            if request.method in permissions.SAFE_METHODS:
                return False  # This shouldn't be reached due to queryset filtering

            return False

        # Default deny
        return False


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
