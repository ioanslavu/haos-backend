"""
Custom permissions for artist sales RBAC.

Uses the DRF-compliant permission classes from api.permissions.
"""
from rest_framework import permissions
from api.permissions import OwnershipPermission


class ArtistSalesPermission(OwnershipPermission):
    """
    Artist Sales-level permissions based on user role and department.

    Inherits from OwnershipPermission which provides:
    - Admins: Full access to all records
    - Department check: Record must be in same department
    - Managers: Full access to all records in their department
    - Employees: Only records they created or are assigned to

    No hardcoded role checks - all logic handled by parent class.

    Object-level permission is enforced via:
    1. get_queryset() filtering (data visibility)
    2. has_object_permission() check (authorization)

    ⚠️  IMPORTANT: Always use self.get_object() in detail actions to ensure
    has_object_permission() is called. Never manually fetch with Model.objects.get()
    """
    pass  # No custom logic needed - parent handles everything!
