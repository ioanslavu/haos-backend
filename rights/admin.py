from django.contrib import admin
from django.utils.html import format_html
from django import forms
from .models import Credit, Split, SplitValidation


class CreditAdminForm(forms.ModelForm):
    class Meta:
        model = Credit
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        # Model's clean method will handle the validation
        return cleaned_data


class SplitAdminForm(forms.ModelForm):
    class Meta:
        model = Split
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        # Model's clean method will handle the validation
        return cleaned_data


@admin.register(Credit)
class CreditAdmin(admin.ModelAdmin):
    form = CreditAdminForm
    list_display = ['get_object_display', 'entity', 'role', 'share_kind',
                    'share_value', 'credited_as', 'created_at']
    list_filter = ['scope', 'role', 'share_kind', 'created_at']
    search_fields = ['entity__display_name', 'credited_as', 'notes']
    autocomplete_fields = ['entity']
    readonly_fields = ['created_at', 'updated_at', 'get_object_display']

    fieldsets = (
        ('Scope', {
            'fields': ('scope', 'object_id', 'get_object_display')
        }),
        ('Credit Information', {
            'fields': ('entity', 'role', 'credited_as')
        }),
        ('Share Information', {
            'fields': ('share_kind', 'share_value')
        }),
        ('Additional', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_object_display(self, obj):
        if obj.scope == 'work':
            work = obj.get_work
            if work:
                return format_html('<a href="/admin/catalog/work/{}/change/">Work: {}</a>',
                                   work.id, work.title)
        elif obj.scope == 'recording':
            recording = obj.get_recording
            if recording:
                return format_html('<a href="/admin/catalog/recording/{}/change/">Recording: {}</a>',
                                   recording.id, recording.title)
        return f"{obj.scope} #{obj.object_id}"
    get_object_display.short_description = 'Object'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('entity')


@admin.register(Split)
class SplitAdmin(admin.ModelAdmin):
    form = SplitAdminForm
    list_display = ['get_object_display', 'entity', 'right_type', 'share',
                    'source', 'is_locked', 'created_at']
    list_filter = ['scope', 'right_type', 'is_locked', 'created_at']
    search_fields = ['entity__display_name', 'source', 'notes']
    autocomplete_fields = ['entity']
    readonly_fields = ['created_at', 'updated_at', 'get_object_display', 'get_validation_status']

    fieldsets = (
        ('Scope', {
            'fields': ('scope', 'object_id', 'get_object_display')
        }),
        ('Split Information', {
            'fields': ('entity', 'right_type', 'share')
        }),
        ('Source', {
            'fields': ('source', 'is_locked')
        }),
        ('Validation', {
            'fields': ('get_validation_status',),
            'classes': ('collapse',)
        }),
        ('Additional', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_object_display(self, obj):
        if obj.scope == 'work':
            work = obj.get_work
            if work:
                return format_html('<a href="/admin/catalog/work/{}/change/">Work: {}</a>',
                                   work.id, work.title)
        elif obj.scope == 'recording':
            recording = obj.get_recording
            if recording:
                return format_html('<a href="/admin/catalog/recording/{}/change/">Recording: {}</a>',
                                   recording.id, recording.title)
        return f"{obj.scope} #{obj.object_id}"
    get_object_display.short_description = 'Object'

    def get_validation_status(self, obj):
        """Show validation status for the splits."""
        validation = Split.validate_splits_total(obj.scope, obj.object_id, obj.right_type)

        status_html = f"""
        <div style="margin: 10px 0;">
            <strong>Total: {validation['total']:.2f}%</strong><br>
            Status: {'✅ Complete' if validation['is_complete'] else f"❌ Missing {validation['missing']:.2f}%"}<br>
            <br>
            <strong>All Splits for this {obj.get_right_type_display()}:</strong><br>
        """

        for split in validation['splits']:
            status_html += f"• {split['entity__display_name']}: {split['share']:.2f}%"
            if split['source']:
                status_html += f" (from {split['source']})"
            status_html += "<br>"

        status_html += "</div>"
        return format_html(status_html)

    get_validation_status.short_description = 'Validation Status'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('entity')


# Admin actions for bulk operations
@admin.action(description='Validate splits for selected items')
def validate_splits(modeladmin, request, queryset):
    """Admin action to validate splits."""
    from django.contrib import messages

    # Group by scope and object
    validations = {}
    for split in queryset:
        key = (split.scope, split.object_id)
        if key not in validations:
            if split.scope == 'work':
                validations[key] = SplitValidation.validate_work_splits(split.object_id)
            else:
                validations[key] = SplitValidation.validate_recording_splits(split.object_id)

    # Report results
    valid_count = sum(1 for v in validations.values() if v['valid'])
    invalid_count = len(validations) - valid_count

    if invalid_count > 0:
        error_messages = []
        for (scope, obj_id), validation in validations.items():
            if not validation['valid']:
                errors = '; '.join(validation['errors'])
                error_messages.append(f"{scope.title()} #{obj_id}: {errors}")

        messages.error(request, f"Found {invalid_count} invalid split groups:\n" + '\n'.join(error_messages))

    if valid_count > 0:
        messages.success(request, f"{valid_count} split groups are valid (100% complete)")


@admin.action(description='Auto-calculate splits from credits')
def auto_calculate_splits(modeladmin, request, queryset):
    """Admin action to auto-calculate splits from credits."""
    from django.contrib import messages

    processed = set()
    for item in queryset:
        key = (item.scope, item.object_id)
        if key not in processed:
            Split.auto_calculate_from_credits(item.scope, item.object_id)
            processed.add(key)

    messages.success(request, f"Auto-calculated splits for {len(processed)} objects")


# Add actions to the admin
SplitAdmin.actions = [validate_splits, auto_calculate_splits]