import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time notifications.
    Each user has their own notification channel.
    """

    async def connect(self):
        """Handle WebSocket connection"""
        # Get user from scope (set by AuthMiddleware)
        self.user = self.scope.get('user')

        # Reject anonymous users
        if not self.user or isinstance(self.user, AnonymousUser):
            await self.close(code=4001)
            return

        # Create a unique group name for this user
        self.group_name = f'notifications_{self.user.id}'

        # Join user's notification group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        # Accept WebSocket connection
        await self.accept()

        # Send connection success message
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to notification stream'
        }))

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if hasattr(self, 'group_name'):
            # Leave user's notification group
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """
        Handle messages from WebSocket client.
        Currently supports: ping/pong for connection health.
        """
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'ping':
                # Respond to ping with pong
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': data.get('timestamp')
                }))
            elif message_type == 'mark_read':
                # Handle mark as read from WebSocket
                notification_id = data.get('notification_id')
                if notification_id:
                    await self.mark_notification_read(notification_id)

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))

    async def notification_message(self, event):
        """
        Handle notification.message events from channel layer.
        This is called when a notification is sent to the user's group.
        """
        # Send notification to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': event['notification']
        }))

    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """Mark notification as read (async wrapper)"""
        from .models import Notification
        try:
            notification = Notification.objects.get(
                id=notification_id,
                user=self.user
            )
            notification.mark_as_read()
            return True
        except Notification.DoesNotExist:
            return False
