"""
Permission classes for identity/entity management.
"""
from api.permissions import BaseResourcePermission


class EntityPermission(BaseResourcePermission):
    """
    Entity permissions.

    TODO: GLOBAL ACCESS - All authenticated users can access all entities
    Currently: Global access for all authenticated users.
    All employees and managers can view all entities (no department restrictions).
    This allows cross-department collaboration and entity reuse.

    Future (Phase 7 - if needed): Implement EntityUsage-based visibility.
    When EntityUsage is implemented, entities will be scoped by department
    and this permission class will enforce that scoping.
    See REFACTOR_PROGRESS.md for implementation plan.

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
