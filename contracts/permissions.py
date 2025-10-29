from django.contrib.auth import get_user_model
from rest_framework.permissions import BasePermission
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

