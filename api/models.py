from django.db import models
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save, pre_delete
from django.db.models.deletion import ProtectedError
from django.dispatch import receiver

User = get_user_model()


class Department(models.Model):
    """
    Department model for organizational structure.
    Replaces hardcoded DEPARTMENT_CHOICES.
    """
    code = models.SlugField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Unique department code (e.g., 'digital', 'sales', 'publishing')"
    )
    name = models.CharField(
        max_length=100,
        help_text="Display name for the department"
    )
    description = models.TextField(
        blank=True,
        help_text="Optional description of the department"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this department is active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Department"
        verbose_name_plural = "Departments"
        ordering = ['code']

    def __str__(self):
        return self.name


class Role(models.Model):
    """
    Role model for user roles.
    Replaces hardcoded ROLE_CHOICES.
    """
    code = models.SlugField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Unique role code (e.g., 'digital_manager', 'administrator')"
    )
    name = models.CharField(
        max_length=100,
        help_text="Display name for the role"
    )
    description = models.TextField(
        blank=True,
        help_text="Optional description of the role"
    )
    level = models.IntegerField(
        db_index=True,
        help_text="Role hierarchy level: 100=guest, 200=employee, 300=manager, 1000=admin"
    )
    department = models.ForeignKey(
        'Department',
        on_delete=models.PROTECT,
        related_name='roles',
        null=True,
        blank=True,
        help_text="If set, this role can only be assigned to users in this specific department"
    )
    is_system_role = models.BooleanField(
        default=False,
        help_text="System roles cannot be deleted via UI"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this role is active and assignable"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Role"
        verbose_name_plural = "Roles"
        ordering = ['level', 'code']

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    """
    User profile to extend Django User with role-based access control.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )

    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name='users',
        help_text="User's role in the system"
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name='users',
        null=True,
        blank=True,
        help_text="User's department (employees/managers require department)"
    )

    profile_picture = models.ImageField(
        upload_to='profile_pictures/',
        blank=True,
        null=True,
        help_text="User profile picture"
    )

    setup_completed = models.BooleanField(
        default=False,
        help_text="Has user completed initial setup?"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['role']),
            models.Index(fields=['department']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.role.name if self.role else 'No Role'}"

    # Backward compatibility properties
    @property
    def role_code(self):
        """Returns role code for backward compatibility."""
        return self.role.code if self.role else 'guest'

    @property
    def department_code(self):
        """Returns department code for backward compatibility."""
        return self.department.code if self.department else None

    # Role hierarchy checks
    @property
    def is_admin(self):
        """Check if user is administrator (level >= 1000)."""
        return self.role and self.role.level >= 1000

    @property
    def is_manager(self):
        """Check if user is manager (level >= 300)."""
        return self.role and self.role.level >= 300

    @property
    def is_employee(self):
        """Check if user is employee (level 200-299)."""
        return self.role and 200 <= self.role.level < 300

    @property
    def is_guest(self):
        """Check if user is guest (level < 200)."""
        return self.role and self.role.level < 200

    @property
    def has_department_access(self):
        """Check if user has department access (not guest and has department)."""
        return not self.is_guest and self.department is not None


class DepartmentRequest(models.Model):
    """
    Department access requests from users.
    Used when a user wants to join a department or change departments.
    """

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='department_requests'
    )

    requested_department = models.CharField(
        max_length=50,
        choices=[
            ('digital', 'Digital'),
            ('sales', 'Sales'),
            ('legal', 'Legal'),
            ('publishing', 'Publishing'),
            ('label', 'Label'),
            ('marketing', 'Marketing'),
            ('finance', 'Finance'),
            ('special_operations', 'Special Operations'),
        ],
        db_index=True,
        help_text="Requested department"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )

    message = models.TextField(
        blank=True,
        help_text="Optional message from user explaining the request"
    )

    # Approval tracking
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_department_requests',
        help_text="Admin/Manager who reviewed this request"
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the request was reviewed"
    )

    rejection_reason = models.TextField(
        blank=True,
        help_text="Reason for rejection (if rejected)"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Department Request"
        verbose_name_plural = "Department Requests"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['user', 'status']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.requested_department} ({self.status})"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Automatically create a UserProfile when a new User is created.
    Default role is 'guest'.
    """
    if created:
        try:
            guest_role = Role.objects.get(code='guest')
            UserProfile.objects.create(user=instance, role=guest_role)
        except Role.DoesNotExist:
            # During migrations or if guest role doesn't exist yet
            # Skip profile creation - it will be handled manually
            pass


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Save the UserProfile when the User is saved.
    """
    if hasattr(instance, 'profile'):
        instance.profile.save()


@receiver(pre_delete, sender='api.UserProfile')
def prevent_profile_deletion(sender, instance, **kwargs):
    """
    Prevent UserProfile deletion to avoid orphaned users.

    User profiles should never be deleted directly. Instead:
    - Deactivate the user: user.is_active = False
    - Change role to guest: profile.role = guest_role
    - Remove department: profile.department = None

    This prevents "ghost" users and maintains data integrity.
    """
    raise ProtectedError(
        "Cannot delete UserProfile. User profiles must not be deleted. "
        "To deactivate a user, set user.is_active=False instead.",
        {instance}
    )


class CompanySettings(models.Model):
    """
    Singleton model to store company settings.
    Only one instance should exist in the database.
    """
    # Basic Information
    company_name = models.CharField(max_length=255, help_text="Trading/Brand name")
    legal_name = models.CharField(max_length=255, blank=True, help_text="Official registered legal name")

    # Company Representative / Administrator
    admin_name = models.CharField(max_length=255, blank=True, help_text="Name of company administrator/representative (e.g., Maria Filip George)")
    admin_role = models.CharField(max_length=100, blank=True, help_text="Role/title of administrator (e.g., Administrator, Director General)")

    # Registration (Romanian-specific fields)
    registration_number = models.CharField(max_length=100, blank=True, help_text="Trade Registry number (e.g., J40/12345/2020)")
    cif = models.CharField(max_length=50, blank=True, help_text="C.I.F. - Cod de Identificare Fiscală (e.g., 12345678 or RO12345678)")
    vat_number = models.CharField(max_length=100, blank=True, help_text="VAT number (optional, if different from C.I.F.)")

    # Contact Information
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    website = models.URLField(blank=True)

    # Address
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True)

    # Bank Details
    bank_name = models.CharField(max_length=255, blank=True)
    bank_account = models.CharField(max_length=100, blank=True, help_text="IBAN or account number")
    bank_swift = models.CharField(max_length=20, blank=True, help_text="SWIFT/BIC code")

    # System Settings
    timezone = models.CharField(max_length=50, default='UTC')
    currency = models.CharField(max_length=3, default='EUR')
    language = models.CharField(max_length=10, default='en')

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Company Settings"
        verbose_name_plural = "Company Settings"

    def __str__(self):
        return self.company_name or "Company Settings"

    def save(self, *args, **kwargs):
        """
        Ensure only one instance exists (singleton pattern).
        """
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """
        Prevent deletion of the singleton instance.
        """
        pass

    @classmethod
    def load(cls):
        """
        Load the singleton instance, creating it if it doesn't exist.
        """
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    def get_placeholders(self):
        """
        Returns a dictionary of placeholders for contract generation.
        Uses 'maincompany' prefix for HaHaHa Production (first party).

        Romanian business registration:
        - registration_number: J40/XXXXX/2020 (Trade Registry)
        - cif: 12345678 or RO12345678 (Tax ID / C.I.F.)
        - vat_number: Optional, if different from C.I.F.
        """
        return {
            # HaHaHa Production placeholders (first party)
            'maincompany.name': self.company_name,
            'maincompany.legal_name': self.legal_name,
            'maincompany.admin_name': self.admin_name,
            'maincompany.admin_role': self.admin_role,
            'maincompany.registration_number': self.registration_number,  # J40/XXXXX/2020
            'maincompany.cif': self.cif,  # 12345678 or RO12345678
            'maincompany.vat_number': self.vat_number if self.vat_number else self.cif,  # Use C.I.F. if VAT not set
            'maincompany.email': self.email,
            'maincompany.phone': self.phone,
            'maincompany.website': self.website,
            'maincompany.address': self.address,
            'maincompany.city': self.city,
            'maincompany.state': self.state,
            'maincompany.zip_code': self.zip_code,
            'maincompany.country': self.country,
            'maincompany.bank_name': self.bank_name,
            'maincompany.bank_account': self.bank_account,
            'maincompany.iban': self.bank_account,
            'maincompany.bank_swift': self.bank_swift,
        }
