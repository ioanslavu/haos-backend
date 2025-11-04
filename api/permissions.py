"""
Permission classes for API endpoints.

Legacy permission classes (kept for backwards compatibility):
- IsAdministrator, IsAdministratorOrManager, IsNotGuest, etc.

New DRF-compliant permission classes with object-level checks:
- BaseResourcePermission, DepartmentScopedPermission, OwnershipPermission
"""
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import permissions
from .utils import has_model_field


class IsAdministrator(permissions.BasePermission):
    """
    Permission to check if user is an Administrator (level >= 1000).
    Uses the role hierarchy system.
    """

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            hasattr(request.user, 'profile') and
            request.user.profile.is_admin
        )


class IsAdministratorOrManager(permissions.BasePermission):
    """
    Permission to check if user is an Administrator or Manager (level >= 300).
    Uses the role hierarchy system.
    """

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            hasattr(request.user, 'profile') and
            request.user.profile.is_manager
        )


class IsNotGuest(permissions.BasePermission):
    """
    Permission to check if user is not a guest (level > 100).
    """

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            hasattr(request.user, 'profile') and
            request.user.profile.role and
            request.user.profile.role.level > 100
        )


class HasDepartmentAccess(permissions.BasePermission):
    """
    Permission to check if user has department access.
    Superusers and staff always have access.
    """

    def has_permission(self, request, view):
        import logging
        logger = logging.getLogger(__name__)

        if not request.user or not request.user.is_authenticated:
            logger.warning(f"HasDepartmentAccess: User not authenticated")
            return False

        # Superusers and staff always have access
        if request.user.is_superuser or request.user.is_staff:
            logger.info(f"HasDepartmentAccess: Allowing {request.user.email} (superuser={request.user.is_superuser}, staff={request.user.is_staff})")
            return True

        # Check department access for regular users
        has_access = (
            hasattr(request.user, 'profile') and
            request.user.profile.has_department_access
        )
        logger.warning(f"HasDepartmentAccess: User {request.user.email} has_access={has_access}")
        return has_access


class IsAdminOrSuperuser(permissions.BasePermission):
    """
    Allow only platform administrators (level >= 1000) or Django superusers.
    Uses the role hierarchy system.
    """

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return False
        if getattr(user, 'is_superuser', False):
            return True
        prof = getattr(user, 'profile', None)
        return bool(prof and prof.is_admin)


class IsSelfOrAdmin(permissions.BasePermission):
    """
    Allow access if the target user in the URL is the authenticated user,
    or if the requester is an admin/superuser (level >= 1000).
    Expects a `user_id` kwarg in the view's URL pattern.
    Uses the role hierarchy system.
    """

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return False

        # Admins and superusers always allowed
        if getattr(user, 'is_superuser', False):
            return True
        prof = getattr(user, 'profile', None)
        if prof and prof.is_admin:
            return True

        # Self-access only
        user_id = getattr(view, 'kwargs', {}).get('user_id') if hasattr(view, 'kwargs') else None
        try:
            return str(user.id) == str(user_id)
        except Exception:
            return False


class CanRevealSensitiveIdentity(permissions.BasePermission):
    """
    Gatekeeper for revealing sensitive identity (e.g., CNP/passport).

    Source of truth:
    - Superusers and platform administrators (level >= 1000) are always allowed.
    - Otherwise, authorization is driven by DB policies in
      identity.SensitiveAccessPolicy (department + role + field).

    This design avoids dependency on Django Groups/Admin, and lets
    operators change access via a CLI without code changes or redeploys.
    Uses the role hierarchy system.
    """

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return False
        if getattr(user, 'is_superuser', False):
            return True
        prof = getattr(user, 'profile', None)
        if prof and prof.is_admin:
            return True

        # Policy-driven check: department + role must be explicitly allowed
        try:
            from identity.policies import SensitiveAccessPolicy
        except Exception:
            # If model not available (e.g., before migrations), fail closed
            return False

        dept = getattr(prof, 'department', None) if prof else None
        role = getattr(prof, 'role', None) if prof else None
        # Current action reveals CNP; future fields can reuse same policy model
        field = 'cnp'
        return SensitiveAccessPolicy.check_allowed(dept, role, field)


# ============================================================================
# New DRF-Compliant Permission Classes (with object-level checks)
# ============================================================================


class BaseResourcePermission(permissions.BasePermission):
    """
    Base permission class that enforces object-level permission checks.

    All resource-specific permission classes should inherit from this to ensure
    proper implementation of both view-level and object-level authorization.

    Defense in depth:
    - has_permission(): View-level check (can user access endpoint?)
    - has_object_permission(): Object-level check (can user access THIS object?)

    IMPORTANT: DRF only calls has_object_permission() if the object is fetched
    via get_object(). Always use standard DRF patterns:
    - ✓ Correct: self.get_object() in retrieve/update/destroy
    - ✗ Wrong: Model.objects.get(pk=pk) (bypasses object-level check!)

    Subclasses MUST implement has_object_permission() or this will raise
    NotImplementedError as a safety guard.
    """

    def has_permission(self, request, view):
        """
        View-level permission check.

        Default: User must be authenticated and have a profile.
        Override in subclasses for more specific checks.
        """
        if not request.user or not request.user.is_authenticated:
            return False

        if not hasattr(request.user, 'profile'):
            return False

        return True

    def has_object_permission(self, request, view, obj):
        """
        Object-level permission check.

        MUST be overridden in subclasses. Raising NotImplementedError ensures
        developers don't forget to implement this critical security layer.

        Args:
            request: DRF request object
            view: ViewSet instance
            obj: Model instance being accessed

        Returns:
            bool: True if user can access object, False otherwise

        Raises:
            NotImplementedError: If subclass doesn't implement this method
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement has_object_permission(). "
            f"This is required for defense-in-depth security."
        )


class DepartmentScopedPermission(BaseResourcePermission):
    """
    Permission for resources scoped to departments.

    Access rules:
    - Admins: Bypass all checks (global access)
    - Users with department: Can access objects in their department
    - Users without department: Denied

    Object-level check:
    - Object must have 'department' field
    - Object's department must match user's department (or user is admin)

    Usage:
        class ContractViewSet(BaseViewSet):
            permission_classes = [IsAuthenticated, DepartmentScopedPermission]
    """

    def has_object_permission(self, request, view, obj):
        """
        Check if user can access object based on department scoping.

        Returns:
            bool: True if admin or same department, False otherwise
        """
        user = request.user

        # User must have a profile
        try:
            profile = user.profile
        except (AttributeError, ObjectDoesNotExist):
            return False

        # Admins bypass all checks
        if profile.is_admin:
            return True

        # Must have department
        if not profile.department:
            return False

        # Object must have department field
        obj_dept = getattr(obj, 'department', None)
        if obj_dept is None:
            # Object doesn't have department field - this is a configuration error
            # Deny access to be safe
            return False

        # Department must match (returns False = 403, not 404)
        return obj_dept == profile.department


class OwnershipPermission(DepartmentScopedPermission):
    """
    Permission for resources with ownership and assignment.

    Access rules (in addition to department scoping):
    - Admins: Bypass all checks
    - Managers: Can access any object in their department
    - Employees: Can only access objects they created or are assigned to

    This class handles the department check via parent class, then adds
    ownership/assignment logic for employees.

    Note: Assignment checking is delegated to the ViewSet's queryset filtering.
    If the object appears in get_queryset(), the employee can access it.

    Usage:
        class CampaignViewSet(OwnedResourceViewSet):
            permission_classes = [IsAuthenticated, OwnershipPermission]
            assigned_field = 'handlers'  # ViewSet config
    """

    def has_object_permission(self, request, view, obj):
        """
        Check if user can access object based on ownership/assignment.

        First checks department scoping (via parent), then adds ownership logic.

        Returns:
            bool: True if user can access, False otherwise
        """
        # First check department scoping
        if not super().has_object_permission(request, view, obj):
            return False

        user = request.user
        profile = user.profile

        # Admins and managers in same dept can access
        if profile.is_admin or profile.is_manager:
            return True

        # Employees and guests: check ownership or assignment
        if profile.is_employee or profile.is_guest:
            # Check ownership
            created_by = getattr(obj, 'created_by', None)
            if created_by == user:
                return True

            # Check assignment via M2M relationship (only for employees, not guests)
            if profile.is_employee:
                assigned_field = getattr(view, 'assigned_field', None)
                if assigned_field:
                    # Check if object is a real Django model (not a Mock)
                    if hasattr(obj.__class__, '_meta'):
                        if has_model_field(obj.__class__, assigned_field):
                            assigned_through_field = getattr(view, 'assigned_through_field', None)

                            # Get the M2M manager
                            m2m_manager = getattr(obj, assigned_field, None)
                            if m2m_manager:
                                try:
                                    # Check if user is in the M2M relationship
                                    if assigned_through_field:
                                        # Through model pattern: handlers.filter(user=user)
                                        lookup = {assigned_through_field: user}
                                        if m2m_manager.filter(**lookup).exists():
                                            return True
                                    else:
                                        # Direct M2M pattern: assigned_to_users.filter(id=user.id)
                                        if m2m_manager.filter(id=user.id).exists():
                                            return True
                                except Exception:
                                    # If any error occurs during M2M check, deny access
                                    pass
                    else:
                        # For test mocks, check if the field exists and query it
                        m2m_manager = getattr(obj, assigned_field, None)
                        if m2m_manager:
                            try:
                                assigned_through_field = getattr(view, 'assigned_through_field', None)
                                if assigned_through_field:
                                    # Through model pattern
                                    lookup = {assigned_through_field: user}
                                    if m2m_manager.filter(**lookup).exists():
                                        return True
                                else:
                                    # Direct M2M pattern
                                    if m2m_manager.filter(id=user.id).exists():
                                        return True
                            except Exception:
                                # If any error occurs, deny access
                                pass

            # Not owner and not assigned - deny access
            return False

        # Default deny (unknown role level)
        return False
