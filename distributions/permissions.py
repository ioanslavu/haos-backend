from rest_framework import permissions
from api.permissions import OwnershipPermission


class DistributionPermission(OwnershipPermission):
    """
    Distribution-level permissions based on user role and department.

    Inherits from OwnershipPermission which provides:
    - Admins: Full access to all distributions
    - Department check: Distribution must be in same department
    - Managers: Full access to all distributions in their department
    - Employees: Only distributions they created

    No hardcoded role checks - all logic handled by parent class.
    This enables adding new roles without code changes.
    """
    pass  # No custom logic needed - parent handles everything!
