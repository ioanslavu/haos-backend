from rest_framework import serializers
from .models import Notification, NotificationPreferences


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model"""

    # Read-only computed fields
    content_type_name = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id',
            'user',
            'message',
            'notification_type',
            'is_read',
            'content_type',
            'content_type_name',
            'object_id',
            'action_url',
            'metadata',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at', 'content_type_name']

    def get_content_type_name(self, obj):
        """Get human-readable content type name"""
        if obj.content_type:
            return obj.content_type.model
        return None


class NotificationListSerializer(serializers.ModelSerializer):
    """Lighter serializer for notification list view"""

    class Meta:
        model = Notification
        fields = [
            'id',
            'message',
            'notification_type',
            'is_read',
            'action_url',
            'created_at',
        ]
        read_only_fields = fields


class MarkReadSerializer(serializers.Serializer):
    """Serializer for marking notifications as read"""
    is_read = serializers.BooleanField(required=False, default=True)


class NotificationPreferencesSerializer(serializers.ModelSerializer):
    """Serializer for NotificationPreferences model"""

    class Meta:
        model = NotificationPreferences
        exclude = ['user', 'id', 'created_at', 'updated_at']

    def validate_urgent_deadline_hours(self, value):
        """Ensure urgent deadline hours is between 1-24"""
        if not 1 <= value <= 24:
            raise serializers.ValidationError("Must be between 1 and 24 hours")
        return value

    def validate_inactivity_days(self, value):
        """Ensure inactivity days is between 1-30"""
        if not 1 <= value <= 30:
            raise serializers.ValidationError("Must be between 1 and 30 days")
        return value

    def validate_campaign_ending_days(self, value):
        """Ensure campaign ending days is between 1-30"""
        if not 1 <= value <= 30:
            raise serializers.ValidationError("Must be between 1 and 30 days")
        return value

    def validate(self, data):
        """Validate quiet hours custom times"""
        if data.get('quiet_hours') == 'custom':
            if not data.get('quiet_hours_start') or not data.get('quiet_hours_end'):
                raise serializers.ValidationError({
                    'quiet_hours': 'Custom quiet hours requires both start and end times'
                })
        return data
