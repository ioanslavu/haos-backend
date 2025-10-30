from django.db import models


class SensitiveAccessPolicy(models.Model):
    """
    Defines which department+role pairs are allowed to reveal specific
    sensitive fields (e.g., CNP). This enables CLI-driven, code-free
    changes to sensitive access control without relying on Django Admin
    or Groups.

    Authorization logic consuming this model is implemented in
    api.permissions.CanRevealSensitiveIdentity.
    """

    FIELD_CHOICES = [
        ('cnp', 'CNP'),
        # Extend with additional fields (e.g., 'passport', 'iban') when enabled
    ]

    department = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Department code (e.g., legal, finance, digital)"
    )

    role = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Role code within the department (e.g., manager, employee)"
    )

    field = models.CharField(
        max_length=20,
        choices=FIELD_CHOICES,
        db_index=True,
        help_text="Sensitive field governed by this policy"
    )

    can_reveal = models.BooleanField(
        default=True,
        help_text="Whether this department+role can reveal the field"
    )

    # Operational metadata
    updated_by = models.CharField(
        max_length=255,
        blank=True,
        help_text="Operator identifier (email/name) who last edited the policy"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('department', 'role', 'field')]
        indexes = [
            models.Index(fields=['department', 'role', 'field']),
        ]
        verbose_name = "Sensitive Access Policy"
        verbose_name_plural = "Sensitive Access Policies"

    def __str__(self):
        state = 'allow' if self.can_reveal else 'deny'
        return f"{self.department}:{self.role} {state} {self.field}"

    @classmethod
    def check_allowed(cls, department: str | None, role: str | None, field: str) -> bool:
        """
        Returns True if the given department+role is explicitly allowed to
        reveal the specified field.
        Fails closed on missing inputs or missing policy rows.
        """
        if not department or not role or not field:
            return False
        try:
            policy = cls.objects.filter(
                department=department,
                role=role,
                field=field,
            ).only('can_reveal').first()
            return bool(policy and policy.can_reveal)
        except Exception:
            # Fail closed on DB errors
            return False

