"""
Base ViewSet classes with automatic RBAC queryset filtering.

Provides clean separation of concerns:
- Queryset filtering: "what rows exist" (data visibility)
- Permission classes: "who may act" (authorization)

Defense in depth:
- get_queryset() filters visible data
- Permission class checks authorization
- has_object_permission() double-checks on retrieve/update/destroy
"""
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from .scoping import QuerysetScoping
from .utils import has_model_field, get_m2m_lookup
from .permissions import (
    BaseResourcePermission,
    DepartmentScopedPermission,
    OwnershipPermission,
)


class BaseViewSet(viewsets.ModelViewSet):
    """
    Base ViewSet with automatic RBAC queryset filtering.

    Separates concerns:
    - Queryset filtering: "what rows exist" (data visibility)
    - Permission classes: "who may act" (authorization)

    Configuration attributes (override in subclass):
    - queryset_scoping: QuerysetScoping enum (default: DEPARTMENT_WITH_OWNERSHIP)
    - ownership_field: Field name for owner (default: 'created_by')
    - assigned_field: M2M field for assignment (default: None)
    - assigned_through_field: FK name in through model (default: 'user', None for direct M2M)
    - select_related_fields: List of fields for select_related optimization
    - prefetch_related_fields: List of fields for prefetch_related optimization

    Defense in depth:
    - get_queryset() filters data visibility
    - Permission class checks authorization (REQUIRED!)
    - has_object_permission() double-checks on retrieve/update/destroy

    ⚠️  CRITICAL SECURITY REQUIREMENT:
    ==================================================================================
    DRF only calls has_object_permission() if you use get_object().

    ALWAYS use standard DRF patterns in detail actions:
    - ✓ Correct: self.get_object() in retrieve/update/destroy/custom actions
    - ✗ WRONG: Model.objects.get(pk=pk) - BYPASSES object-level permissions!

    If you manually fetch objects, you MUST manually call check_object_permissions():
        obj = Model.objects.get(pk=pk)
        self.check_object_permissions(self.request, obj)  # Required!

    But prefer using self.get_object() whenever possible.
    ==================================================================================

    Example usage:
        class CampaignViewSet(BaseViewSet):
            queryset = Campaign.objects.all()
            permission_classes = [IsAuthenticated, OwnershipPermission]
            queryset_scoping = QuerysetScoping.DEPARTMENT_WITH_OWNERSHIP
            assigned_field = 'handlers'
            assigned_through_field = 'user'  # CampaignHandler.user
            select_related_fields = ['client', 'created_by', 'department']
            prefetch_related_fields = ['handlers__user']
    """

    permission_classes = [IsAuthenticated]  # Override in subclass
    queryset_scoping = QuerysetScoping.DEPARTMENT_WITH_OWNERSHIP
    ownership_field = 'created_by'
    assigned_field = None
    assigned_through_field = 'user'  # Set to None for direct M2M
    select_related_fields = []
    prefetch_related_fields = []

    def get_queryset(self):
        """
        Apply queryset scoping based on configuration.

        This handles "what rows exist" (data visibility).
        Permission classes handle "who may act" (authorization).

        Scoping modes:
        - NONE: No filtering (permission class returns 403 for unauthorized)
        - GLOBAL: All authenticated users see all records
        - DEPARTMENT: Filter by user's department
        - DEPARTMENT_WITH_OWNERSHIP: Department + ownership/assignment logic

        Returns:
            QuerySet: Filtered queryset based on user role and scoping mode
        """
        queryset = super().get_queryset()
        user = self.request.user

        # Apply query optimizations first
        if self.select_related_fields:
            queryset = queryset.select_related(*self.select_related_fields)
        if self.prefetch_related_fields:
            queryset = queryset.prefetch_related(*self.prefetch_related_fields)

        # No profile = no access
        if not hasattr(user, 'profile'):
            return queryset.none()

        profile = user.profile

        # Admins always see everything
        if profile.is_admin:
            return queryset

        # Apply scoping based on configuration
        if self.queryset_scoping == QuerysetScoping.NONE:
            # Admin-only endpoint
            # Permission class should return 403 for non-admins
            # Don't return none() here - let permission class handle it
            return queryset

        elif self.queryset_scoping == QuerysetScoping.GLOBAL:
            # All employees can see everything
            if profile.is_employee:
                return queryset
            return queryset.none()

        elif self.queryset_scoping == QuerysetScoping.DEPARTMENT:
            # Filter by department only
            if not profile.department:
                return queryset.none()
            return queryset.filter(department=profile.department)

        elif self.queryset_scoping == QuerysetScoping.DEPARTMENT_WITH_OWNERSHIP:
            # Department + ownership/assignment
            if not profile.department:
                return queryset.none()

            # Managers see everything in department
            if profile.is_manager:
                return queryset.filter(department=profile.department)

            # Employees see what they own or are assigned to
            if profile.is_employee:
                return self._apply_ownership_filters(queryset, user, profile)

            return queryset.none()

        # Unknown scoping mode - fail safe
        return queryset.none()

    def _apply_ownership_filters(self, queryset, user, profile):
        """
        Apply ownership filters for employees.

        Returns queryset filtered by:
        - Department AND (created_by OR assigned)

        Args:
            queryset: Base queryset to filter
            user: Current user
            profile: User profile

        Returns:
            QuerySet: Filtered queryset with ownership logic applied
        """
        filters = []

        # Add ownership filter
        if self.ownership_field and has_model_field(queryset.model, self.ownership_field):
            filters.append(Q(**{self.ownership_field: user}))

        # Add assignment filter
        if self.assigned_field and has_model_field(queryset.model, self.assigned_field):
            try:
                lookup = get_m2m_lookup(
                    queryset.model,
                    self.assigned_field,
                    self.assigned_through_field
                )
                filters.append(Q(**{lookup: user}))
            except ValueError:
                # Field doesn't exist or isn't M2M - skip
                pass

        # Combine filters: department AND (owned OR assigned)
        if filters:
            ownership_q = filters[0]
            for f in filters[1:]:
                ownership_q |= f

            final_q = Q(department=profile.department) & ownership_q

            # Only use distinct() if we joined through M2M
            if self.assigned_field:
                return queryset.filter(final_q).distinct()
            else:
                return queryset.filter(final_q)
        else:
            # No ownership/assignment fields configured - just filter by department
            return queryset.filter(department=profile.department)


class DepartmentScopedViewSet(BaseViewSet):
    """
    ViewSet for resources scoped to departments.
    Managers and employees see all resources in their department.

    Example:
        class ActivityViewSet(DepartmentScopedViewSet):
            queryset = Activity.objects.all()
            select_related_fields = ['department', 'created_by']
    """
    queryset_scoping = QuerysetScoping.DEPARTMENT
    permission_classes = [IsAuthenticated, DepartmentScopedPermission]


class OwnedResourceViewSet(BaseViewSet):
    """
    ViewSet for resources with ownership and assignment.
    Employees see only what they created or are assigned to.
    Managers see all resources in their department.

    Example:
        class CampaignViewSet(OwnedResourceViewSet):
            queryset = Campaign.objects.all()
            assigned_field = 'handlers'
            assigned_through_field = 'user'
    """
    queryset_scoping = QuerysetScoping.DEPARTMENT_WITH_OWNERSHIP
    permission_classes = [IsAuthenticated, OwnershipPermission]


class GlobalResourceViewSet(BaseViewSet):
    """
    ViewSet for global resources.
    All employees can see all records.

    Example:
        class WorkViewSet(GlobalResourceViewSet):
            queryset = Work.objects.all()
    """
    queryset_scoping = QuerysetScoping.GLOBAL
    permission_classes = [IsAuthenticated]
