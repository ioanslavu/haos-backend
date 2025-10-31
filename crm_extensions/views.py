from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from datetime import datetime, timedelta

from .models import Task, Activity, CampaignMetrics, EntityChangeRequest
from .serializers import (
    TaskSerializer,
    TaskCreateUpdateSerializer,
    ActivitySerializer,
    ActivityCreateUpdateSerializer,
    CampaignMetricsSerializer,
    EntityChangeRequestSerializer,
)
from api.permissions import HasDepartmentAccess


class TaskViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing tasks.
    Supports filtering by status, priority, assignment, and associations.
    """
    queryset = Task.objects.all()
    permission_classes = [IsAuthenticated, HasDepartmentAccess]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description', 'notes']
    ordering_fields = ['priority', 'due_date', 'created_at', 'status']
    ordering = ['-priority', 'due_date']

    filterset_fields = {
        'status': ['exact', 'in'],
        'priority': ['exact', 'gte', 'lte'],
        'task_type': ['exact', 'in'],
        'assigned_to': ['exact'],
        'created_by': ['exact'],
        'department': ['exact'],
        'campaign': ['exact'],
        'entity': ['exact'],
        'contract': ['exact'],
        'due_date': ['exact', 'gte', 'lte'],
        'created_at': ['gte', 'lte'],
    }

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return TaskCreateUpdateSerializer
        return TaskSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        # Role-based filtering (similar to campaigns)
        if hasattr(user, 'profile'):
            if user.profile.is_admin:
                # Admins see everything
                pass
            elif user.profile.is_manager:
                # Managers see all tasks in their department
                if user.profile.department:
                    queryset = queryset.filter(department=user.profile.department)
            elif user.profile.is_employee:
                # Employees see only tasks assigned to them
                queryset = queryset.filter(assigned_to_users=user)
            else:
                # Guests see nothing
                queryset = queryset.none()

        # Additional query params
        is_overdue = self.request.query_params.get('is_overdue')
        if is_overdue == 'true':
            queryset = queryset.filter(
                due_date__lt=timezone.now(),
                status__in=['todo', 'in_progress', 'blocked']
            )

        is_blocked = self.request.query_params.get('is_blocked')
        if is_blocked == 'true':
            queryset = queryset.filter(
                blocked_by__status__in=['todo', 'in_progress', 'blocked']
            ).distinct()

        my_tasks = self.request.query_params.get('my_tasks')
        if my_tasks == 'true':
            queryset = queryset.filter(assigned_to_users=user)

        # Support filtering by multiple assignees
        assigned_to_in = self.request.query_params.get('assigned_to__in')
        if assigned_to_in:
            user_ids = [int(uid) for uid in assigned_to_in.split(',')]
            queryset = queryset.filter(assigned_to_users__id__in=user_ids).distinct()

        # Optimize query with select_related and prefetch_related
        queryset = queryset.select_related(
            'campaign', 'entity', 'contract',
            'assigned_to', 'created_by', 'department', 'parent_task'
        ).prefetch_related('blocks_tasks', 'subtasks', 'assigned_to_users')

        return queryset

    def perform_create(self, serializer):
        # Auto-assign creator to task and set department to digital
        user = self.request.user
        department = None

        # Get digital department
        from api.models import Department
        try:
            department = Department.objects.get(code='digital')
        except Department.DoesNotExist:
            pass

        # Save task with creator
        task = serializer.save(created_by=user, department=department)

        # Auto-assign creator to task if no assignees specified
        if not task.assigned_to_users.exists():
            task.assigned_to_users.add(user)

    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """Get task statistics for dashboard."""
        queryset = self.get_queryset()

        stats = {
            'total': queryset.count(),
            'by_status': dict(queryset.values('status').annotate(count=Count('id')).values_list('status', 'count')),
            'by_priority': dict(queryset.values('priority').annotate(count=Count('id')).values_list('priority', 'count')),
            'overdue': queryset.filter(
                due_date__lt=timezone.now(),
                status__in=['todo', 'in_progress', 'blocked']
            ).count(),
            'due_today': queryset.filter(
                due_date__date=timezone.now().date(),
                status__in=['todo', 'in_progress']
            ).count(),
            'due_this_week': queryset.filter(
                due_date__gte=timezone.now(),
                due_date__lte=timezone.now() + timedelta(days=7),
                status__in=['todo', 'in_progress']
            ).count(),
        }

        return Response(stats)

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Quick status update for a task."""
        task = self.get_object()
        new_status = request.data.get('status')

        if new_status not in dict(Task.STATUS_CHOICES):
            return Response(
                {'error': 'Invalid status'},
                status=status.HTTP_400_BAD_REQUEST
            )

        task.status = new_status
        task.save()

        return Response(TaskSerializer(task).data)

    @action(detail=True, methods=['post'])
    def create_subtask(self, request, pk=None):
        """Create a subtask for the current task."""
        parent_task = self.get_object()
        serializer = TaskCreateUpdateSerializer(data=request.data)

        if serializer.is_valid():
            subtask = serializer.save(
                created_by=request.user,
                parent_task=parent_task,
                campaign=parent_task.campaign,
                entity=parent_task.entity,
                contract=parent_task.contract,
                department=parent_task.department
            )
            return Response(TaskSerializer(subtask).data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ActivityViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing activities and communication logs.
    """
    queryset = Activity.objects.all()
    permission_classes = [IsAuthenticated, HasDepartmentAccess]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['subject', 'content', 'location']
    ordering_fields = ['activity_date', 'created_at', 'sentiment']
    ordering = ['-activity_date']

    filterset_fields = {
        'type': ['exact', 'in'],
        'sentiment': ['exact', 'in'],
        'direction': ['exact'],
        'follow_up_required': ['exact'],
        'follow_up_completed': ['exact'],
        'created_by': ['exact'],
        'department': ['exact'],
        'entity': ['exact'],
        'campaign': ['exact'],
        'contact_person': ['exact'],
        'activity_date': ['gte', 'lte'],
    }

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ActivityCreateUpdateSerializer
        return ActivitySerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        # Filter by user's department if not admin
        if hasattr(user, 'userprofile') and not user.userprofile.is_admin:
            if user.userprofile.department:
                queryset = queryset.filter(
                    Q(department=user.userprofile.department) | Q(department__isnull=True)
                )

        # Filter for activities needing follow-up
        needs_follow_up = self.request.query_params.get('needs_follow_up')
        if needs_follow_up == 'true':
            queryset = queryset.filter(
                follow_up_required=True,
                follow_up_completed=False,
                follow_up_date__lte=timezone.now() + timedelta(days=7)
            )

        # Filter for my activities
        my_activities = self.request.query_params.get('my_activities')
        if my_activities == 'true':
            queryset = queryset.filter(
                Q(created_by=user) | Q(participants=user)
            ).distinct()

        # Optimize query
        queryset = queryset.select_related(
            'entity', 'contact_person', 'campaign',
            'contract', 'created_by', 'department', 'follow_up_task'
        ).prefetch_related('participants')

        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def create_follow_up_task(self, request, pk=None):
        """Create a follow-up task for this activity."""
        activity = self.get_object()

        if activity.follow_up_task:
            return Response(
                {'error': 'Follow-up task already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not activity.follow_up_required:
            return Response(
                {'error': 'Activity does not require follow-up'},
                status=status.HTTP_400_BAD_REQUEST
            )

        task = activity.create_follow_up_task()

        if task:
            return Response(TaskSerializer(task).data, status=status.HTTP_201_CREATED)

        return Response(
            {'error': 'Could not create follow-up task'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=False, methods=['get'])
    def timeline(self, request):
        """Get activity timeline for an entity or campaign."""
        entity_id = request.query_params.get('entity')
        campaign_id = request.query_params.get('campaign')

        if not entity_id and not campaign_id:
            return Response(
                {'error': 'Entity or campaign ID required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        queryset = self.get_queryset()

        if entity_id:
            queryset = queryset.filter(entity_id=entity_id)
        if campaign_id:
            queryset = queryset.filter(campaign_id=campaign_id)

        # Group by date
        activities = queryset.order_by('-activity_date')
        serializer = self.get_serializer(activities, many=True)

        return Response(serializer.data)


class CampaignMetricsViewSet(viewsets.ModelViewSet):
    """
    ViewSet for campaign metrics and KPI tracking.
    """
    queryset = CampaignMetrics.objects.all()
    serializer_class = CampaignMetricsSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    ordering_fields = ['recorded_date']
    ordering = ['-recorded_date']

    filterset_fields = {
        'campaign': ['exact'],
        'source': ['exact', 'in'],
        'recorded_date': ['exact', 'gte', 'lte'],
    }

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by campaign if provided
        campaign_id = self.request.query_params.get('campaign')
        if campaign_id:
            queryset = queryset.filter(campaign_id=campaign_id)

        # Date range filtering
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        if start_date:
            queryset = queryset.filter(recorded_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(recorded_date__lte=end_date)

        return queryset.select_related('campaign')

    @action(detail=False, methods=['get'])
    def campaign_summary(self, request):
        """Get metrics summary for a specific campaign."""
        campaign_id = request.query_params.get('campaign')

        if not campaign_id:
            return Response(
                {'error': 'Campaign ID required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        metrics = self.get_queryset().filter(campaign_id=campaign_id)

        if not metrics.exists():
            return Response({'message': 'No metrics found for this campaign'})

        # Calculate aggregates
        summary = {
            'total_impressions': metrics.aggregate(Sum('impressions'))['impressions__sum'] or 0,
            'total_clicks': metrics.aggregate(Sum('clicks'))['clicks__sum'] or 0,
            'total_conversions': metrics.aggregate(Sum('conversions'))['conversions__sum'] or 0,
            'total_cost': metrics.aggregate(Sum('cost'))['cost__sum'] or 0,
            'total_revenue': metrics.aggregate(Sum('revenue'))['revenue__sum'] or 0,
            'avg_ctr': metrics.aggregate(Avg('ctr'))['ctr__avg'] or 0,
            'avg_cpa': metrics.aggregate(Avg('cpa'))['cpa__avg'] or 0,
            'avg_roi': metrics.aggregate(Avg('roi'))['roi__avg'] or 0,
            'latest_metrics': CampaignMetricsSerializer(metrics.first()).data,
            'metrics_count': metrics.count(),
        }

        return Response(summary)

    @action(detail=False, methods=['post'])
    def bulk_import(self, request):
        """Import multiple metrics records at once."""
        campaign_id = request.data.get('campaign')
        metrics_data = request.data.get('metrics', [])

        if not campaign_id or not metrics_data:
            return Response(
                {'error': 'Campaign ID and metrics data required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        created_metrics = []
        errors = []

        for metric_data in metrics_data:
            metric_data['campaign'] = campaign_id
            serializer = CampaignMetricsSerializer(data=metric_data)

            if serializer.is_valid():
                created_metrics.append(serializer.save())
            else:
                errors.append({
                    'data': metric_data,
                    'errors': serializer.errors
                })

        response_data = {
            'created': len(created_metrics),
            'errors': errors
        }

        if errors:
            return Response(response_data, status=status.HTTP_207_MULTI_STATUS)

        return Response(response_data, status=status.HTTP_201_CREATED)


class EntityChangeRequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet for entity change requests.
    - Non-admins can: create requests, view their own requests
    - Admins can: view all requests, approve/reject
    """
    serializer_class = EntityChangeRequestSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['message', 'admin_notes', 'entity__display_name']
    ordering_fields = ['created_at', 'status']
    ordering = ['-created_at']

    filterset_fields = {
        'status': ['exact', 'in'],
        'request_type': ['exact'],
        'entity': ['exact'],
        'requested_by': ['exact'],
    }

    def get_queryset(self):
        user = self.request.user

        # Admins see all requests
        if hasattr(user, 'profile') and user.profile.is_admin:
            return EntityChangeRequest.objects.all()

        # Non-admins see only their own requests
        return EntityChangeRequest.objects.filter(requested_by=user)

    def perform_create(self, serializer):
        # Auto-assign the current user as requester
        serializer.save(requested_by=self.request.user)

        # Send notification to admins
        from notifications.services import notify_entity_change_request
        request_obj = serializer.instance
        notify_entity_change_request(request_obj)

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        """
        Admin approves the request.
        Requires admin permission.
        """
        user = request.user

        # Check if user is admin
        if not (hasattr(user, 'profile') and user.profile.is_admin):
            return Response(
                {'error': 'Only admins can approve requests'},
                status=status.HTTP_403_FORBIDDEN
            )

        change_request = self.get_object()
        admin_notes = request.data.get('admin_notes', '')

        # Approve the request
        change_request.approve(user, admin_notes)

        # TODO: Send notification to requester

        serializer = self.get_serializer(change_request)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        """
        Admin rejects the request.
        Requires admin permission.
        """
        user = request.user

        # Check if user is admin
        if not (hasattr(user, 'profile') and user.profile.is_admin):
            return Response(
                {'error': 'Only admins can reject requests'},
                status=status.HTTP_403_FORBIDDEN
            )

        change_request = self.get_object()
        admin_notes = request.data.get('admin_notes', '')

        # Reject the request
        change_request.reject(user, admin_notes)

        # TODO: Send notification to requester

        serializer = self.get_serializer(change_request)
        return Response(serializer.data)