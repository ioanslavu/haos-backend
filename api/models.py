from django.db import models
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

User = get_user_model()


class UserProfile(models.Model):
    """
    User profile to extend Django User with role-based access control.
    """

    # Role choices
    ROLE_CHOICES = [
        ('guest', 'Guest'),
        ('administrator', 'Administrator'),
        ('digital_manager', 'Digital Manager'),
        ('digital_employee', 'Digital Employee'),
        ('sales_manager', 'Sales Manager'),
        ('sales_employee', 'Sales Employee'),
    ]

    # Department choices
    DEPARTMENT_CHOICES = [
        (None, 'None'),
        ('digital', 'Digital'),
        ('sales', 'Sales'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )

    role = models.CharField(
        max_length=50,
        choices=ROLE_CHOICES,
        default='guest',
        db_index=True,
        help_text="User role for access control"
    )

    department = models.CharField(
        max_length=50,
        choices=DEPARTMENT_CHOICES,
        blank=True,
        null=True,
        db_index=True,
        help_text="Department: Digital or Sales"
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
        return f"{self.user.email} - {self.get_role_display()}"

    @property
    def is_admin(self):
        return self.role == 'administrator'

    @property
    def is_manager(self):
        return self.role in ['digital_manager', 'sales_manager']

    @property
    def is_employee(self):
        return self.role in ['digital_employee', 'sales_employee']

    @property
    def is_guest(self):
        return self.role == 'guest'

    @property
    def has_department_access(self):
        """Check if user has department access (not guest)."""
        return self.role != 'guest' and self.department is not None


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
        UserProfile.objects.create(user=instance, role='guest')


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Save the UserProfile when the User is saved.
    """
    if hasattr(instance, 'profile'):
        instance.profile.save()


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
