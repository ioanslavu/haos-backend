from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.contrib.contenttypes.models import ContentType
from .models import Notification
from .serializers import NotificationSerializer


class NotificationService:
    """
    Service for creating and sending notifications to users.
    Handles both database persistence and real-time WebSocket delivery.
    """

    @staticmethod
    def create_notification(
        user,
        message,
        notification_type='system',
        related_object=None,
        action_url='',
        metadata=None
    ):
        """
        Create a notification and send it via WebSocket.

        Args:
            user: User instance who receives the notification
            message: Notification message text
            notification_type: Type of notification (default: 'system')
            related_object: Optional Django model instance to link
            action_url: Optional URL for frontend navigation
            metadata: Optional dict of additional data

        Returns:
            Notification instance
        """
        # Prepare notification data
        notification_data = {
            'user': user,
            'message': message,
            'notification_type': notification_type,
            'action_url': action_url,
            'metadata': metadata or {}
        }

        # Add generic relation if related object provided
        if related_object:
            notification_data['content_type'] = ContentType.objects.get_for_model(related_object)
            notification_data['object_id'] = related_object.pk

        # Create notification in database
        notification = Notification.objects.create(**notification_data)

        # Send to WebSocket
        NotificationService.send_to_user(user.id, notification)

        return notification

    @staticmethod
    def send_to_user(user_id, notification):
        """
        Send notification to user via WebSocket channel layer.

        Args:
            user_id: ID of the user to send to
            notification: Notification instance
        """
        channel_layer = get_channel_layer()
        group_name = f'notifications_{user_id}'

        # Serialize notification
        serialized_notification = NotificationSerializer(notification).data

        # Send to user's WebSocket group
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': 'notification_message',
                'notification': serialized_notification
            }
        )

    @staticmethod
    def notify_assignment(user, assigned_by, object_name, object_type, action_url=''):
        """
        Helper: Create assignment notification.

        Args:
            user: User who was assigned
            assigned_by: User who made the assignment
            object_name: Name of the object assigned
            object_type: Type of object (e.g., "contract", "task")
            action_url: URL to the object
        """
        message = f"{assigned_by.get_full_name() or assigned_by.email} assigned you to {object_type}: {object_name}"

        return NotificationService.create_notification(
            user=user,
            message=message,
            notification_type='assignment',
            action_url=action_url,
            metadata={
                'assigned_by_id': assigned_by.id,
                'assigned_by_name': assigned_by.get_full_name() or assigned_by.email,
                'object_name': object_name,
                'object_type': object_type
            }
        )

    @staticmethod
    def notify_mention(user, mentioned_by, context, action_url=''):
        """
        Helper: Create mention notification.

        Args:
            user: User who was mentioned
            mentioned_by: User who created the mention
            context: Context of the mention (e.g., "in a comment on Contract #123")
            action_url: URL to the mention location
        """
        message = f"{mentioned_by.get_full_name() or mentioned_by.email} mentioned you {context}"

        return NotificationService.create_notification(
            user=user,
            message=message,
            notification_type='mention',
            action_url=action_url,
            metadata={
                'mentioned_by_id': mentioned_by.id,
                'mentioned_by_name': mentioned_by.get_full_name() or mentioned_by.email,
                'context': context
            }
        )

    @staticmethod
    def notify_status_change(user, object_name, old_status, new_status, action_url=''):
        """
        Helper: Create status change notification.

        Args:
            user: User to notify
            object_name: Name of the object
            old_status: Previous status
            new_status: New status
            action_url: URL to the object
        """
        message = f"{object_name} status changed from '{old_status}' to '{new_status}'"

        return NotificationService.create_notification(
            user=user,
            message=message,
            notification_type='status_change',
            action_url=action_url,
            metadata={
                'object_name': object_name,
                'old_status': old_status,
                'new_status': new_status
            }
        )


def notify_entity_change_request(request_obj):
    """
    Notify all admins when a non-admin requests entity edit/delete.

    Args:
        request_obj: EntityChangeRequest instance
    """
    from api.models import UserProfile

    # Get all admin users (role level >= 1000)
    admins = UserProfile.objects.filter(role__level__gte=1000).select_related('user', 'role')

    # Determine action word
    action = 'edit' if request_obj.request_type == 'edit' else 'delete'

    # Get requester name
    requester_name = (
        f"{request_obj.requested_by.first_name} {request_obj.requested_by.last_name}".strip()
        or request_obj.requested_by.email
    )

    # Create notification for each admin
    for admin_profile in admins:
        NotificationService.create_notification(
            user=admin_profile.user,
            message=f"{requester_name} requested to {action} entity '{request_obj.entity.display_name}'",
            notification_type='entity_request',
            related_object=request_obj,
            action_url=f"/admin/entity-requests",
            metadata={
                'request_type': request_obj.request_type,
                'entity_id': request_obj.entity.id,
                'entity_name': request_obj.entity.display_name,
                'requester_id': request_obj.requested_by.id,
                'requester_name': requester_name,
            }
        )
