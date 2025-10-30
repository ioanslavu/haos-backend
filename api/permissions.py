from rest_framework import permissions


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
