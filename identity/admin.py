from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Entity, EntityRole, SensitiveIdentity, Identifier, AuditLogSensitive,
    SocialMediaAccount, ContactPerson, ContactEmail, ContactPhone
)


class EntityRoleInline(admin.TabularInline):
    model = EntityRole
    extra = 1
    fields = ['role', 'primary_role', 'is_internal']


class IdentifierInline(admin.TabularInline):
    model = Identifier
    extra = 1
    fields = ['scheme', 'value', 'pii_flag', 'issued_by', 'issued_date', 'expiry_date']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Filter to only show identifiers for this entity
        return qs.filter(owner_type='entity')

    def save_model(self, request, obj, form, change):
        obj.owner_type = 'entity'
        obj.owner_id = obj.entity.id
        super().save_model(request, obj, form, change)


class SocialMediaAccountInline(admin.TabularInline):
    model = SocialMediaAccount
    extra = 1
    fields = ['platform', 'handle', 'url', 'is_verified', 'is_primary', 'follower_count']


@admin.register(Entity)
class EntityAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'kind', 'email', 'phone', 'get_roles', 'created_at']
    list_filter = ['kind', 'created_at', 'entity_roles__role']
    search_fields = ['display_name', 'email', 'phone', 'notes']
    readonly_fields = ['created_at', 'updated_at', 'created_by']

    fieldsets = (
        ('Basic Information', {
            'fields': ('kind', 'display_name', 'email', 'phone')
        }),
        ('Address', {
            'fields': ('address', 'city', 'state', 'zip_code', 'country'),
            'classes': ('collapse',)
        }),
        ('Business Information', {
            'fields': ('company_registration_number', 'vat_number'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('notes', 'created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    inlines = [EntityRoleInline, SocialMediaAccountInline]  # Removed IdentifierInline - uses generic FK not direct FK

    def get_roles(self, obj):
        roles = obj.entity_roles.all()
        return ', '.join([r.get_role_display() for r in roles])
    get_roles.short_description = 'Roles'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(EntityRole)
class EntityRoleAdmin(admin.ModelAdmin):
    list_display = ['entity', 'role', 'primary_role', 'is_internal', 'created_at']
    list_filter = ['role', 'primary_role', 'is_internal', 'created_at']
    search_fields = ['entity__display_name']
    autocomplete_fields = ['entity']


@admin.register(SensitiveIdentity)
class SensitiveIdentityAdmin(admin.ModelAdmin):
    list_display = ['entity', 'get_entity_kind', 'has_cnp', 'date_of_birth', 'created_at']
    list_filter = ['created_at']
    search_fields = ['entity__display_name']
    readonly_fields = ['created_at', 'updated_at', 'get_masked_cnp_display']
    autocomplete_fields = ['entity']

    fieldsets = (
        ('Entity', {
            'fields': ('entity',)
        }),
        ('Personal Information', {
            'fields': ('date_of_birth', 'place_of_birth', 'get_masked_cnp_display')
        }),
        ('ID Card Information', {
            'fields': ('id_series', 'id_number', 'id_issued_by', 'id_issued_date', 'id_expiry_date'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_entity_kind(self, obj):
        return obj.entity.get_kind_display()
    get_entity_kind.short_description = 'Entity Type'

    def has_cnp(self, obj):
        return bool(obj._cnp_encrypted)
    has_cnp.boolean = True
    has_cnp.short_description = 'Has CNP'

    def get_masked_cnp_display(self, obj):
        return obj.get_masked_cnp() or 'Not set'
    get_masked_cnp_display.short_description = 'CNP (Masked)'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Only show PF entities
        return qs.filter(entity__kind='PF')


@admin.register(Identifier)
class IdentifierAdmin(admin.ModelAdmin):
    list_display = ['scheme', 'value', 'owner_type', 'get_owner_display', 'pii_flag', 'issued_by', 'created_at']
    list_filter = ['scheme', 'owner_type', 'pii_flag', 'created_at']
    search_fields = ['value', 'issued_by']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Identifier Information', {
            'fields': ('scheme', 'value', 'pii_flag')
        }),
        ('Owner', {
            'fields': ('owner_type', 'owner_id')
        }),
        ('Issuing Information', {
            'fields': ('issued_by', 'issued_date', 'expiry_date'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_owner_display(self, obj):
        if obj.owner_type == 'entity':
            from .models import Entity
            entity = Entity.objects.filter(id=obj.owner_id).first()
            if entity:
                return format_html('<a href="/admin/identity/entity/{}/change/">{}</a>',
                                   entity.id, entity.display_name)
        elif obj.owner_type == 'work':
            from catalog.models import Work
            work = Work.objects.filter(id=obj.owner_id).first()
            if work:
                return format_html('<a href="/admin/catalog/work/{}/change/">{}</a>',
                                   work.id, work.title)
        elif obj.owner_type == 'recording':
            from catalog.models import Recording
            recording = Recording.objects.filter(id=obj.owner_id).first()
            if recording:
                return format_html('<a href="/admin/catalog/recording/{}/change/">{}</a>',
                                   recording.id, recording.title)
        elif obj.owner_type == 'release':
            from catalog.models import Release
            release = Release.objects.filter(id=obj.owner_id).first()
            if release:
                return format_html('<a href="/admin/catalog/release/{}/change/">{}</a>',
                                   release.id, release.title)
        return f"{obj.owner_type} #{obj.owner_id}"
    get_owner_display.short_description = 'Owner'


@admin.register(AuditLogSensitive)
class AuditLogSensitiveAdmin(admin.ModelAdmin):
    list_display = ['entity', 'field', 'action', 'viewer_user', 'viewed_at', 'ip_address']
    list_filter = ['field', 'action', 'viewed_at']
    search_fields = ['entity__display_name', 'viewer_user__username', 'reason']
    readonly_fields = ['entity', 'field', 'action', 'viewer_user', 'reason',
                       'viewed_at', 'ip_address', 'user_agent', 'session_key']
    date_hierarchy = 'viewed_at'

    def has_add_permission(self, request):
        # Audit logs should not be manually created
        return False

    def has_delete_permission(self, request, obj=None):
        # Audit logs should not be deleted
        return False

    def has_change_permission(self, request, obj=None):
        # Audit logs should be read-only
        return False


@admin.register(SocialMediaAccount)
class SocialMediaAccountAdmin(admin.ModelAdmin):
    list_display = ['entity', 'platform', 'handle', 'is_verified', 'is_primary', 'follower_count', 'created_at']
    list_filter = ['platform', 'is_verified', 'is_primary', 'created_at']
    search_fields = ['entity__display_name', 'handle', 'url', 'display_name']
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['entity']

    fieldsets = (
        ('Account Information', {
            'fields': ('entity', 'platform', 'handle', 'url', 'display_name')
        }),
        ('Metrics', {
            'fields': ('follower_count', 'is_verified', 'is_primary')
        }),
        ('Additional', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class ContactEmailInline(admin.TabularInline):
    model = ContactEmail
    extra = 1
    fields = ['email', 'label', 'is_primary']


class ContactPhoneInline(admin.TabularInline):
    model = ContactPhone
    extra = 1
    fields = ['phone', 'label', 'is_primary']


@admin.register(ContactPerson)
class ContactPersonAdmin(admin.ModelAdmin):
    list_display = ['name', 'entity', 'role', 'engagement_stage', 'sentiment', 'created_at']
    list_filter = ['role', 'engagement_stage', 'sentiment', 'created_at']
    search_fields = ['name', 'notes', 'entity__display_name']
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['entity']

    fieldsets = (
        ('Basic Information', {
            'fields': ('entity', 'name')
        }),
        ('Relationship', {
            'fields': ('role', 'engagement_stage', 'sentiment', 'notes')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    inlines = [ContactEmailInline, ContactPhoneInline]