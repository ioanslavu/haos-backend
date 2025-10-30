from rest_framework import permissions


class IsAdministrator(permissions.BasePermission):
    """
    Permission to check if user is an Administrator.
    """

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            hasattr(request.user, 'profile') and
            request.user.profile.role == 'administrator'
        )


class IsAdministratorOrManager(permissions.BasePermission):
    """
    Permission to check if user is an Administrator or Manager.
    """

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            hasattr(request.user, 'profile') and
            request.user.profile.role in [
                'administrator',
                'digital_manager',
                'sales_manager'
            ]
        )


class IsNotGuest(permissions.BasePermission):
    """
    Permission to check if user is not a guest (has department access).
    """

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            hasattr(request.user, 'profile') and
            request.user.profile.role != 'guest'
        )


class HasDepartmentAccess(permissions.BasePermission):
    """
    Permission to check if user has department access.
    """

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            hasattr(request.user, 'profile') and
            request.user.profile.has_department_access
        )


class IsAdminOrSuperuser(permissions.BasePermission):
    """
    Allow only platform administrators (profile.role == 'administrator')
    or Django superusers.
    """

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return False
        if getattr(user, 'is_superuser', False):
            return True
        prof = getattr(user, 'profile', None)
        return bool(prof and getattr(prof, 'role', None) == 'administrator')


class IsSelfOrAdmin(permissions.BasePermission):
    """
    Allow access if the target user in the URL is the authenticated user,
    or if the requester is an admin/superuser.
    Expects a `user_id` kwarg in the view's URL pattern.
    """

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return False

        # Admins and superusers always allowed
        if getattr(user, 'is_superuser', False):
            return True
        prof = getattr(user, 'profile', None)
        if prof and getattr(prof, 'role', None) == 'administrator':
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
    - Superusers and platform administrators (profile.role == 'administrator')
      are always allowed.
    - Otherwise, authorization is driven by DB policies in
      identity.SensitiveAccessPolicy (department + role + field).

    This design avoids dependency on Django Groups/Admin, and lets
    operators change access via a CLI without code changes or redeploys.
    """

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return False
        if getattr(user, 'is_superuser', False):
            return True
        prof = getattr(user, 'profile', None)
        if prof and getattr(prof, 'role', None) == 'administrator':
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
