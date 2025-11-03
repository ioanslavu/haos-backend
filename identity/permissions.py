"""
Permission classes for identity/entity management.
"""
from api.permissions import BaseResourcePermission


class EntityPermission(BaseResourcePermission):
    """
    Entity permissions.

    Currently: Global access for all authenticated users.
    All employees can view all entities (no department restrictions yet).

    Future: Will check EntityUsage for department-scoped visibility.
    When EntityUsage is implemented, entities will be scoped by department
    and this permission class will enforce that scoping.

    For now, this provides object-level permission checks while allowing
    global access.
    """

    def has_object_permission(self, request, view, obj):
        """
        Check if user can access entity.

        Currently: All authenticated users with profiles can access.
        Future: Will check EntityUsage table for department access.
        """
        user = request.user
        profile = user.profile

        # Admins always have access
        if profile.is_admin:
            return True

        # Currently: all authenticated users can access
        # Future: Check EntityUsage here:
        # from identity.models import EntityUsage
        # if profile.department.access_type == 'support':
        #     return True  # Support depts see all entities
        # return EntityUsage.objects.filter(
        #     entity=obj,
        #     department=profile.department
        # ).exists()

        return True
