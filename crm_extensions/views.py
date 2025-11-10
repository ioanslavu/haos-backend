from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from api.viewsets import OwnedResourceViewSet, DepartmentScopedViewSet
from api.scoping import QuerysetScoping

from .models import Task, Activity, CampaignMetrics, EntityChangeRequest, FlowTrigger, ManualTrigger
from .serializers import (
    TaskSerializer,
    TaskCreateUpdateSerializer,
    ActivitySerializer,
    ActivityCreateUpdateSerializer,
    CampaignMetricsSerializer,
    EntityChangeRequestSerializer,
    FlowTriggerSerializer,
    ManualTriggerSerializer,
)
from .permissions import TaskPermission, ActivityPermission, EntityChangeRequestPermission


class TaskViewSet(OwnedResourceViewSet):
    """
    ViewSet for managing tasks with RBAC.

    Inherits from OwnedResourceViewSet which provides automatic RBAC filtering:
    - Admins: See all tasks
    - Department Managers: See all tasks in their department
    - Department Employees: See tasks they created OR are assigned to
    - Guests/No Department: See nothing

    Note: Tasks use direct M2M for assignment (assigned_to_users), not through model.
    The BaseViewSet handles this automatically with assigned_through_field=None.
    """
    queryset = Task.objects.all()
    permission_classes = [IsAuthenticated, TaskPermission]
    serializer_class = TaskSerializer  # Default serializer
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
        # Universal task system entity filters
        'song': ['exact'],
        'work': ['exact'],
        'recording': ['exact'],
        'opportunity': ['exact'],
        'deliverable': ['exact'],
        'song_checklist_item': ['exact'],
        'source_stage': ['exact', 'in'],
        'due_date': ['exact', 'gte', 'lte'],
        'created_at': ['gte', 'lte'],
    }

    # BaseViewSet configuration (replaces hardcoded role checks)
    queryset_scoping = QuerysetScoping.DEPARTMENT_WITH_OWNERSHIP
    ownership_field = 'created_by'
    assigned_field = 'assignments'
    assigned_through_field = 'user'  # TaskAssignment.user (standard pattern)
    select_related_fields = [
        'campaign', 'entity', 'contract', 'assigned_to', 'created_by', 'department', 'parent_task',
        # Universal task system entities
        'song', 'song__artist', 'work', 'recording', 'opportunity', 'deliverable', 'song_checklist_item'
    ]
    prefetch_related_fields = ['blocks_tasks', 'subtasks', 'assignments__user']

    def get_queryset(self):
        """
        Extend parent queryset with additional query param filtering.

        Parent handles RBAC filtering (admin/manager/employee logic).
        This adds custom query params for task-specific filtering.
        """
        # Get RBAC-filtered queryset from parent
        queryset = super().get_queryset()

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
            queryset = queryset.filter(assigned_users=self.request.user)

        # Support filtering by multiple assignees
        assigned_to_in = self.request.query_params.get('assigned_to__in')
        if assigned_to_in:
            user_ids = [int(uid) for uid in assigned_to_in.split(',')]
            queryset = queryset.filter(assigned_users__id__in=user_ids).distinct()

        # Filter by entity type (which type of entity the task is linked to)
        entity_type = self.request.query_params.get('entity_type')
        if entity_type:
            if entity_type == 'song':
                queryset = queryset.filter(song__isnull=False)
            elif entity_type == 'work':
                queryset = queryset.filter(work__isnull=False)
            elif entity_type == 'recording':
                queryset = queryset.filter(recording__isnull=False)
            elif entity_type == 'opportunity':
                queryset = queryset.filter(opportunity__isnull=False)
            elif entity_type == 'deliverable':
                queryset = queryset.filter(deliverable__isnull=False)
            elif entity_type == 'contract':
                queryset = queryset.filter(contract__isnull=False)
            elif entity_type == 'campaign':
                queryset = queryset.filter(campaign__isnull=False)

        return queryset

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return TaskCreateUpdateSerializer
        return TaskSerializer

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

        # Extract assigned_user_ids before saving
        assigned_user_ids = serializer.validated_data.pop('assigned_user_ids', None)

        # Save task with creator
        task = serializer.save(created_by=user, department=department)

        # Handle task assignments
        from .models import TaskAssignment
        from django.contrib.auth import get_user_model
        User = get_user_model()

        if assigned_user_ids:
            # Create assignments for specified users
            for user_id in assigned_user_ids:
                try:
                    assignee = User.objects.get(id=user_id)
                    TaskAssignment.objects.create(
                        task=task,
                        user=assignee,
                        role='assignee',
                        assigned_by=user
                    )
                except User.DoesNotExist:
                    pass  # Skip invalid user IDs
        else:
            # Auto-assign creator if no assignees specified
            TaskAssignment.objects.create(
                task=task,
                user=user,
                role='assignee',
                assigned_by=user
            )

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


class ActivityViewSet(DepartmentScopedViewSet):
    """
    ViewSet for managing activities and communication logs with RBAC.

    Inherits from DepartmentScopedViewSet which provides automatic RBAC filtering:
    - Admins: See all activities
    - Department users: See activities in their department

    ActivityPermission provides object-level checks:
    - All department users can view/create/edit activities in their department
    - No ownership restrictions - activities are shared within the department

    No hardcoded role checks needed!
    """
    queryset = Activity.objects.all()
    permission_classes = [IsAuthenticated, ActivityPermission]
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

    # BaseViewSet configuration
    select_related_fields = ['entity', 'contact_person', 'campaign', 'contract', 'created_by', 'department', 'follow_up_task']
    prefetch_related_fields = ['participants']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ActivityCreateUpdateSerializer
        return ActivitySerializer

    def get_queryset(self):
        """
        Extend parent queryset with query param filtering.

        Parent handles RBAC filtering (admin/department logic).
        This adds custom query params for activity-specific filtering.
        """
        # Get RBAC-filtered queryset from parent
        queryset = super().get_queryset()

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
                Q(created_by=self.request.user) | Q(participants=self.request.user)
            ).distinct()

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
    ViewSet for campaign metrics and KPI tracking with RBAC.

    Metrics inherit access from their related Campaign:
    - Admins: See all metrics
    - Department Managers: See metrics for campaigns in their department
    - Department Employees: See metrics for campaigns they created or are assigned to

    No hardcoded role checks - uses Campaign RBAC to determine accessible metrics!
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
        """
        Filter metrics based on Campaign RBAC.

        Instead of duplicating Campaign's RBAC logic, we get the accessible campaigns
        and filter metrics to only those campaigns.
        """
        from campaigns.models import Campaign

        queryset = super().get_queryset()
        user = self.request.user

        if not hasattr(user, 'profile'):
            return queryset.none()

        profile = user.profile

        # Admins see all metrics
        if profile.is_admin:
            pass  # No filtering needed
        elif profile.department:
            # Filter by campaigns accessible to the user
            # This follows the same logic as CampaignViewSet
            if profile.is_manager:
                # Managers see metrics for all campaigns in their department
                queryset = queryset.filter(campaign__department=profile.department)
            else:
                # Employees see metrics for campaigns they created or are assigned to
                queryset = queryset.filter(
                    campaign__department=profile.department
                ).filter(
                    Q(campaign__created_by=user) | Q(campaign__handlers__user=user)
                ).distinct()
        else:
            # No department = no access
            return queryset.none()

        # Query param filtering
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
    ViewSet for entity change requests with RBAC.

    Simple ownership-based access:
    - Admins: View all requests, can approve/reject
    - Regular users: Create requests, view their own requests

    EntityChangeRequestPermission provides object-level checks.
    No hardcoded role checks!
    """
    serializer_class = EntityChangeRequestSerializer
    permission_classes = [IsAuthenticated, EntityChangeRequestPermission]
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
        """
        Filter requests based on ownership.

        Admins see all requests, regular users see only their own.
        No hardcoded role checks!
        """
        user = self.request.user

        if not hasattr(user, 'profile'):
            return EntityChangeRequest.objects.none()

        # Admins see all requests
        if user.profile.is_admin:
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

        Object-level permission check via get_object() ensures only admins can approve.
        No hardcoded role checks!
        """
        change_request = self.get_object()
        user = request.user

        # Additional business logic check: only admins can approve
        if not user.profile.is_admin:
            return Response(
                {'error': 'Only admins can approve requests'},
                status=status.HTTP_403_FORBIDDEN
            )

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

        Object-level permission check via get_object() ensures only admins can reject.
        No hardcoded role checks!
        """
        change_request = self.get_object()
        user = request.user

        # Additional business logic check: only admins can reject
        if not user.profile.is_admin:
            return Response(
                {'error': 'Only admins can reject requests'},
                status=status.HTTP_403_FORBIDDEN
            )

        admin_notes = request.data.get('admin_notes', '')

        # Reject the request
        change_request.reject(user, admin_notes)

        # TODO: Send notification to requester

        serializer = self.get_serializer(change_request)
        return Response(serializer.data)

class FlowTriggerViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for FlowTrigger - read-only list of automatic triggers.
    Used by frontend to understand what automatic actions exist.
    """
    queryset = FlowTrigger.objects.filter(is_active=True)
    serializer_class = FlowTriggerSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['name', 'description', 'trigger_entity_type']
    filterset_fields = ['trigger_entity_type', 'trigger_event', 'creates_task']


class ManualTriggerViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for ManualTrigger - provides UI button definitions and execution endpoint.

    Endpoints:
    - GET /api/manual-triggers/ - List all active triggers
    - GET /api/manual-triggers/?entity_type=song&context=label_recording_stage - Filter by entity/context
    - POST /api/manual-triggers/{id}/execute/ - Execute trigger (create task)
    """
    serializer_class = ManualTriggerSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['name', 'button_label']
    filterset_fields = ['entity_type', 'context', 'action_type']

    def get_queryset(self):
        """Filter triggers based on user's department visibility and active status."""
        queryset = ManualTrigger.objects.filter(is_active=True)
        
        # Filter by user's department (if they have one)
        user = self.request.user
        if hasattr(user, 'profile') and user.profile.department:
            # Show triggers visible to user's department
            queryset = queryset.filter(
                Q(visible_to_departments=user.profile.department) |
                Q(visible_to_departments__isnull=True)  # No department restrictions
            ).distinct()
        
        return queryset

    @action(detail=True, methods=['post'], url_path='execute')
    def execute(self, request, pk=None):
        """
        Execute a manual trigger - creates a task for the specified entity.
        
        Request body:
        {
            "entity_id": 123,  // ID of the entity (song, deliverable, etc.)
            "context_data": {}  // Optional additional context data
        }
        
        Returns the created task.
        """
        trigger = self.get_object()
        entity_id = request.data.get('entity_id')
        context_data = request.data.get('context_data', {})

        if not entity_id:
            return Response(
                {'error': 'entity_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get the entity based on trigger entity_type
        entity = None
        try:
            if trigger.entity_type == 'song':
                from catalog.models import Song
                entity = Song.objects.get(pk=entity_id)
            elif trigger.entity_type == 'deliverable':
                from artist_sales.models import OpportunityDeliverable
                entity = OpportunityDeliverable.objects.get(pk=entity_id)
            elif trigger.entity_type == 'opportunity':
                from artist_sales.models import Opportunity
                entity = Opportunity.objects.get(pk=entity_id)
            elif trigger.entity_type == 'contract':
                from contracts.models import Contract
                entity = Contract.objects.get(pk=entity_id)
            else:
                return Response(
                    {'error': f'Unsupported entity_type: {trigger.entity_type}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            return Response(
                {'error': f'Entity not found: {str(e)}'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Create task using TaskGenerator
        from crm_extensions.services import TaskGenerator
        task = TaskGenerator.create_from_manual_trigger(
            trigger=trigger,
            entity=entity,
            user=request.user,
            context_data=context_data
        )

        if not task:
            return Response(
                {'error': 'Failed to create task'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Return the created task
        from .serializers import TaskSerializer
        serializer = TaskSerializer(task)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
