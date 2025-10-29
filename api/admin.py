from django.contrib import admin
from django.contrib.auth import get_user_model
from .models import CompanySettings, UserProfile, DepartmentRequest

User = get_user_model()


class UserProfileInline(admin.StackedInline):
    """Inline admin for UserProfile within User admin."""
    model = UserProfile
    can_delete = False
    verbose_name = 'Profile'
    verbose_name_plural = 'Profile'
    fields = ['role', 'department', 'profile_picture', 'setup_completed']


class UserAdmin(admin.ModelAdmin):
    """Enhanced User admin with profile information."""
    list_display = ['email', 'first_name', 'last_name', 'get_role', 'get_department', 'is_active', 'date_joined']
    list_filter = ['is_active', 'profile__role', 'profile__department']
    search_fields = ['email', 'first_name', 'last_name']
    inlines = [UserProfileInline]
    ordering = ['-date_joined']

    def get_role(self, obj):
        return obj.profile.get_role_display() if hasattr(obj, 'profile') else 'No Profile'
    get_role.short_description = 'Role'
    get_role.admin_order_field = 'profile__role'

    def get_department(self, obj):
        if hasattr(obj, 'profile') and obj.profile.department:
            return obj.profile.get_department_display()
        return 'None'
    get_department.short_description = 'Department'
    get_department.admin_order_field = 'profile__department'


# Unregister the default User admin and register our enhanced version
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin interface for UserProfile."""
    list_display = ['user', 'role', 'department', 'setup_completed', 'created_at']
    list_filter = ['role', 'department', 'setup_completed']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Role & Department', {
            'fields': ('role', 'department')
        }),
        ('Profile', {
            'fields': ('profile_picture', 'setup_completed')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(DepartmentRequest)
class DepartmentRequestAdmin(admin.ModelAdmin):
    """Admin interface for DepartmentRequest."""
    list_display = ['user', 'requested_department', 'status', 'created_at', 'reviewed_by', 'reviewed_at']
    list_filter = ['status', 'requested_department', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'message']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    fieldsets = (
        ('Request', {
            'fields': ('user', 'requested_department', 'message', 'status')
        }),
        ('Review', {
            'fields': ('reviewed_by', 'reviewed_at', 'rejection_reason')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        """Auto-assign reviewed_by when changing status."""
        if change and 'status' in form.changed_data:
            from django.utils import timezone
            obj.reviewed_by = request.user
            obj.reviewed_at = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(CompanySettings)
class CompanySettingsAdmin(admin.ModelAdmin):
    """
    Admin interface for CompanySettings (singleton).
    """
    list_display = ['company_name', 'email', 'phone', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('company_name', 'legal_name')
        }),
        ('Registration', {
            'fields': ('registration_number', 'vat_number')
        }),
        ('Contact Information', {
            'fields': ('email', 'phone', 'website')
        }),
        ('Address', {
            'fields': ('address', 'city', 'state', 'zip_code', 'country')
        }),
        ('Bank Details', {
            'fields': ('bank_name', 'bank_account', 'bank_swift')
        }),
        ('System Settings', {
            'fields': ('timezone', 'currency', 'language')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['created_at', 'updated_at']

    def has_add_permission(self, request):
        """
        Prevent adding more than one instance (singleton).
        """
        return not CompanySettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        """
        Prevent deletion of the singleton instance.
        """
        return False
