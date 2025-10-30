from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator

from .models import Notification, NotificationPreferences
from .serializers import (
    NotificationSerializer,
    NotificationListSerializer,
    MarkReadSerializer,
    NotificationPreferencesSerializer
)


class NotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing notifications.

    Provides:
    - list: Get paginated list of user's notifications
    - retrieve: Get single notification detail
    - mark_read: Mark single notification as read
    - mark_all_read: Mark all user's notifications as read
    - unread_count: Get count of unread notifications
    - destroy: Delete notification
    """
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        """Filter notifications to current user only"""
        user = self.request.user
        queryset = Notification.objects.filter(user=user)

        # Filter by read/unread status
        is_read = self.request.query_params.get('is_read')
        if is_read is not None:
            is_read_bool = is_read.lower() in ['true', '1', 'yes']
            queryset = queryset.filter(is_read=is_read_bool)

        # Filter by notification type
        notification_type = self.request.query_params.get('notification_type')
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)

        return queryset.select_related('content_type', 'user')

    def get_serializer_class(self):
        """Use lighter serializer for list view"""
        if self.action == 'list':
            return NotificationListSerializer
        return NotificationSerializer

    @action(detail=True, methods=['patch'])
    def mark_read(self, request, pk=None):
        """Mark a single notification as read/unread"""
        notification = self.get_object()
        serializer = MarkReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        is_read = serializer.validated_data.get('is_read', True)
        if is_read:
            notification.mark_as_read()
        else:
            notification.mark_as_unread()

        return Response(
            NotificationSerializer(notification).data,
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all user's notifications as read"""
        updated_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).update(is_read=True)

        return Response(
            {'count': updated_count},
            status=status.HTTP_200_OK
        )

    @method_decorator(ratelimit(key='user', rate='100/m', method='GET'))
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get count of unread notifications (cached in Redis)"""
        count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()

        return Response(
            {'count': count},
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get', 'put', 'patch'])
    def preferences(self, request):
        """
        Get or update user's notification preferences.

        GET: Returns current preferences (creates defaults if none exist)
        PUT/PATCH: Updates preferences
        """
        preferences, created = NotificationPreferences.objects.get_or_create(
            user=request.user
        )

        if request.method == 'GET':
            serializer = NotificationPreferencesSerializer(preferences)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # Handle PUT/PATCH
        serializer = NotificationPreferencesSerializer(
            preferences,
            data=request.data,
            partial=(request.method == 'PATCH')
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)
