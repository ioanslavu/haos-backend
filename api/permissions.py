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
