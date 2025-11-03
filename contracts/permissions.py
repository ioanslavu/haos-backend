"""
Contract permission classes.

Legacy permissions (kept for backwards compatibility):
- CanViewContract, CanMakePublic, CanSendForSignature

New DRF-compliant permissions:
- ContractPermission, ContractTemplatePermission
"""
from django.contrib.auth import get_user_model
from rest_framework import permissions
from rest_framework.permissions import BasePermission
from api.permissions import OwnershipPermission, DepartmentScopedPermission
from .models import Contract
from .rbac import ContractsRBAC

User = get_user_model()


class CanViewContract(BasePermission):
    def has_object_permission(self, request, view, obj: Contract):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        # Admins bypass
        if getattr(user, 'is_superuser', False) or getattr(user, 'profile', None) and user.profile.role == 'administrator':
            return True
        return ContractsRBAC(user).can_view(obj)


class CanMakePublic(BasePermission):
    def has_object_permission(self, request, view, obj: Contract):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if getattr(user, 'is_superuser', False) or getattr(user, 'profile', None) and user.profile.role == 'administrator':
            return True
        return ContractsRBAC(user).can_publish(obj)


class CanSendForSignature(BasePermission):
    def has_object_permission(self, request, view, obj: Contract):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if getattr(user, 'is_superuser', False) or getattr(user, 'profile', None) and user.profile.role == 'administrator':
            return True
        return ContractsRBAC(user).can_send(obj)


# ============================================================================
# New DRF-Compliant Permission Classes
# ============================================================================


class ContractPermission(OwnershipPermission):
    """
    Contract permissions with policy-based access control.

    Inherits from OwnershipPermission which provides:
    - Admins: Full access to all contracts
    - Department check: Contract must be in same department
    - Managers: Full access to all contracts in their department
    - Employees: Only contracts they created

    Additionally checks ContractTypePolicy for contract type restrictions.

    Note: Policy checks are also applied in get_queryset() for list views.
    This provides defense-in-depth: queryset filtering + object-level check.
    """

    def has_object_permission(self, request, view, obj):
        """
        Check if user can access contract based on ownership and policy.

        First checks standard ownership rules (via parent), then adds
        policy-based contract type restrictions.
        """
        # First check standard ownership rules
        if not super().has_object_permission(request, view, obj):
            return False

        user = request.user
        profile = user.profile

        # Admins bypass policy checks
        if profile.is_admin:
            return True

        # Policy-based check for contract types
        # This is handled by the ContractsRBAC helper class
        rbac = ContractsRBAC(user)

        if request.method in permissions.SAFE_METHODS:
            # Read access
            return rbac.can_view(obj)
        else:
            # Write access
            return rbac.can_update(obj)


class ContractTemplatePermission(DepartmentScopedPermission):
    """
    Contract template permissions.

    All department users can view templates.
    Only managers can create/edit/delete templates.

    Templates are department-scoped but don't have ownership restrictions.
    """

    def has_object_permission(self, request, view, obj):
        """
        Check if user can access template.

        Read: All department users
        Write: Managers only
        """
        # Check department scoping
        if not super().has_object_permission(request, view, obj):
            return False

        user = request.user
        profile = user.profile

        # Admins can do anything
        if profile.is_admin:
            return True

        # Read: all department users
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write: managers only
        return profile.is_manager

