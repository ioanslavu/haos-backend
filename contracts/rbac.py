from dataclasses import dataclass
from typing import List
from django.db import models
from django.contrib.auth import get_user_model
from .models import Contract

User = get_user_model()


class ContractTypePolicy(models.Model):
    """
    Policy matrix at role+department+contract_type level controlling actions.
    DEPRECATED: This model will be replaced with the new PolicyRule system.
    Kept temporarily for backward compatibility during migration.
    """
    ROLE_CHOICES = [
        ('guest', 'Guest'),
        ('administrator', 'Administrator'),
        ('digital_manager', 'Digital Manager'),
        ('digital_employee', 'Digital Employee'),
        ('sales_manager', 'Sales Manager'),
        ('sales_employee', 'Sales Employee'),
    ]

    DEPARTMENT_CHOICES = [
        ('digital', 'Digital'),
        ('sales', 'Sales'),
        ('publishing', 'Publishing'),
    ]

    role = models.CharField(max_length=50, choices=ROLE_CHOICES, db_index=True)
    department = models.CharField(max_length=50, choices=DEPARTMENT_CHOICES, db_index=True)
    contract_type = models.CharField(max_length=30, choices=Contract.CONTRACT_TYPE_CHOICES, db_index=True)

    # Action flags
    can_view = models.BooleanField(default=True)
    can_publish = models.BooleanField(default=False)
    can_send = models.BooleanField(default=False)
    can_update = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)
    can_regenerate = models.BooleanField(default=False)

    class Meta:
        unique_together = [('role', 'department', 'contract_type')]
        indexes = [
            models.Index(fields=['role', 'department']),
        ]


@dataclass
class ContractsRBAC:
    user: User

    def _is_admin(self) -> bool:
        if not self.user or not self.user.is_authenticated:
            return False
        if getattr(self.user, 'is_superuser', False):
            return True
        prof = getattr(self.user, 'profile', None)
        return bool(prof and prof.role and prof.role.code == 'administrator')

    def _user_role_dept(self):
        prof = getattr(self.user, 'profile', None)
        if not prof:
            return (None, None)
        role_code = prof.role.code if prof.role else None
        dept_code = prof.department.code if prof.department else None
        return (role_code, dept_code)

    def _policy(self, contract_type: str):
        role, dept = self._user_role_dept()
        if not role or not dept:
            return None
        try:
            return ContractTypePolicy.objects.get(role=role, department=dept, contract_type=contract_type)
        except ContractTypePolicy.DoesNotExist:
            return None

    def can_view(self, obj: Contract) -> bool:
        if self._is_admin():
            return True
        role, dept = self._user_role_dept()
        if not role or not dept:
            return False
        # Must match department of object (reject if no department or different department)
        if not obj.department or obj.department.code != dept:
            return False
        pol = self._policy(obj.contract_type or '')
        return bool(pol and pol.can_view)

    def can_publish(self, obj: Contract) -> bool:
        if self._is_admin():
            return True
        role, dept = self._user_role_dept()
        if not role or not dept:
            return False
        if not obj.department or obj.department.code != dept:
            return False
        pol = self._policy(obj.contract_type or '')
        return bool(pol and pol.can_publish)

    def can_send(self, obj: Contract) -> bool:
        if self._is_admin():
            return True
        role, dept = self._user_role_dept()
        if not role or not dept:
            return False
        if not obj.department or obj.department.code != dept:
            return False
        pol = self._policy(obj.contract_type or '')
        return bool(pol and pol.can_send)

    def can_update(self, obj: Contract) -> bool:
        if self._is_admin():
            return True
        role, dept = self._user_role_dept()
        if not role or not dept:
            return False
        if not obj.department or obj.department.code != dept:
            return False
        pol = self._policy(obj.contract_type or '')
        return bool(pol and pol.can_update)

    def can_delete(self, obj: Contract) -> bool:
        if self._is_admin():
            return True
        role, dept = self._user_role_dept()
        if not role or not dept:
            return False
        if not obj.department or obj.department.code != dept:
            return False
        pol = self._policy(obj.contract_type or '')
        return bool(pol and pol.can_delete)

    def can_regenerate(self, obj: Contract) -> bool:
        if self._is_admin():
            return True
        role, dept = self._user_role_dept()
        if not role or not dept:
            return False
        if not obj.department or obj.department.code != dept:
            return False
        pol = self._policy(obj.contract_type or '')
        return bool(pol and pol.can_regenerate)
