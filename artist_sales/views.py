"""
ViewSets for Artist Sales - Unified Opportunities API

Production-ready with:
- Proper filtering and pagination for scale
- Optimized queries (select_related, prefetch_related)
- Bulk operations
- Custom actions for stage transitions
"""

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend, FilterSet, CharFilter, DateFilter, NumberFilter
from django.db.models import Count, Q, Prefetch
from django.utils import timezone
from .models import (
    Opportunity, OpportunityArtist, OpportunityTask, OpportunityActivity,
    OpportunityComment, OpportunityDeliverable, Approval, Invoice,
    DeliverablePack, UsageTerms
)
from .serializers import (
    OpportunityListSerializer, OpportunityDetailSerializer, OpportunityCreateSerializer,
    OpportunityArtistSerializer, OpportunityTaskSerializer, OpportunityActivitySerializer,
    OpportunityCommentSerializer, OpportunityDeliverableSerializer,
    ApprovalSerializer, InvoiceSerializer, DeliverablePackSerializer, UsageTermsSerializer
)


# === FILTERS ===

class OpportunityFilter(FilterSet):
    """Advanced filtering for opportunities"""
    expected_close_date_after = DateFilter(field_name='expected_close_date', lookup_expr='gte')
    expected_close_date_before = DateFilter(field_name='expected_close_date', lookup_expr='lte')
    estimated_value_min = NumberFilter(field_name='estimated_value', lookup_expr='gte')
    estimated_value_max = NumberFilter(field_name='estimated_value', lookup_expr='lte')
    search = CharFilter(method='filter_search')

    class Meta:
        model = Opportunity
        fields = {
            'stage': ['exact', 'in'],
            'priority': ['exact', 'in'],
            'owner': ['exact'],
            'team': ['exact'],
            'account': ['exact'],
            'currency': ['exact'],
        }

    def filter_search(self, queryset, name, value):
        """Search across title and account name"""
        return queryset.filter(
            Q(title__icontains=value) |
            Q(account__display_name__icontains=value) |
            Q(opportunity_number__icontains=value)
        )


# === VIEWSETS ===

class OpportunityViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Opportunity with optimized queries for scale.

    List view uses lightweight serializer with annotations.
    Detail view includes all related objects.
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = OpportunityFilter
    ordering_fields = ['created_at', 'updated_at', 'expected_close_date', 'estimated_value', 'priority', 'stage']
    ordering = ['-created_at']

    def get_queryset(self):
        """Optimized queryset with select_related and annotations"""
        queryset = Opportunity.objects.select_related(
            'account', 'contact_person', 'owner', 'team', 'created_by'
        )

        # For list view, add counts
        if self.action == 'list':
            queryset = queryset.annotate(
                artists_count=Count('artists', distinct=True),
                tasks_count=Count('tasks', distinct=True),
                active_tasks_count=Count(
                    'tasks',
                    filter=Q(tasks__status__in=['pending', 'in_progress']),
                    distinct=True
                )
            )

        # For detail view, prefetch related objects
        elif self.action == 'retrieve':
            queryset = queryset.prefetch_related(
                Prefetch('artists', queryset=OpportunityArtist.objects.select_related('artist')),
                Prefetch('tasks', queryset=OpportunityTask.objects.select_related('assigned_to', 'assigned_by')),
                'deliverables'
            )

        return queryset

    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action == 'list':
            return OpportunityListSerializer
        elif self.action == 'create':
            return OpportunityCreateSerializer
        return OpportunityDetailSerializer

    @action(detail=True, methods=['post'])
    def advance_stage(self, request, pk=None):
        """Advance opportunity to next stage"""
        opportunity = self.get_object()
        new_stage = request.data.get('stage')

        if not new_stage:
            return Response({'error': 'stage is required'}, status=status.HTTP_400_BAD_REQUEST)

        old_stage = opportunity.stage
        opportunity.stage = new_stage
        opportunity.save()

        # Log activity
        OpportunityActivity.objects.create(
            opportunity=opportunity,
            user=request.user,
            activity_type='stage_changed',
            title=f'Stage changed to {dict(Opportunity.STAGE_CHOICES).get(new_stage)}',
            metadata={'old_stage': old_stage, 'new_stage': new_stage}
        )

        serializer = self.get_serializer(opportunity)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def mark_won(self, request, pk=None):
        """Mark opportunity as won"""
        opportunity = self.get_object()
        opportunity.stage = 'won'
        opportunity.actual_close_date = timezone.now().date()
        opportunity.save()

        # Log activity
        OpportunityActivity.objects.create(
            opportunity=opportunity,
            user=request.user,
            activity_type='won',
            title='Opportunity marked as Won',
            metadata={'won_date': str(opportunity.actual_close_date)}
        )

        serializer = self.get_serializer(opportunity)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def mark_lost(self, request, pk=None):
        """Mark opportunity as lost"""
        opportunity = self.get_object()
        opportunity.stage = 'closed_lost'
        opportunity.actual_close_date = timezone.now().date()
        opportunity.lost_date = timezone.now().date()
        opportunity.lost_reason = request.data.get('lost_reason', '')
        opportunity.competitor = request.data.get('competitor', '')
        opportunity.save()

        # Log activity
        OpportunityActivity.objects.create(
            opportunity=opportunity,
            user=request.user,
            activity_type='lost',
            title='Opportunity marked as Lost',
            metadata={
                'lost_date': str(opportunity.lost_date),
                'lost_reason': opportunity.lost_reason,
                'competitor': opportunity.competitor
            }
        )

        serializer = self.get_serializer(opportunity)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def bulk_update(self, request):
        """Bulk update opportunities (e.g., bulk stage change, bulk assign)"""
        ids = request.data.get('ids', [])
        updates = request.data.get('updates', {})

        if not ids:
            return Response({'error': 'ids is required'}, status=status.HTTP_400_BAD_REQUEST)

        opportunities = Opportunity.objects.filter(id__in=ids)
        count = opportunities.update(**updates)

        return Response({
            'updated': count,
            'message': f'{count} opportunities updated'
        })

    @action(detail=True, methods=['get'])
    def activities(self, request, pk=None):
        """Get activity feed for opportunity"""
        opportunity = self.get_object()
        activities = opportunity.activities.select_related('user').all()
        serializer = OpportunityActivitySerializer(activities, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get', 'post'])
    def comments(self, request, pk=None):
        """Get or create comments for opportunity"""
        opportunity = self.get_object()

        if request.method == 'GET':
            comments = opportunity.comments.select_related('user').all()
            serializer = OpportunityCommentSerializer(comments, many=True)
            return Response(serializer.data)

        elif request.method == 'POST':
            serializer = OpportunityCommentSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                serializer.save(opportunity=opportunity, user=request.user)

                # Log activity
                OpportunityActivity.objects.create(
                    opportunity=opportunity,
                    user=request.user,
                    activity_type='comment_added',
                    title='New comment added',
                    description=serializer.data['comment'][:100]
                )

                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OpportunityArtistViewSet(viewsets.ModelViewSet):
    """ViewSet for OpportunityArtist"""
    queryset = OpportunityArtist.objects.select_related('opportunity', 'artist').all()
    serializer_class = OpportunityArtistSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['opportunity', 'artist', 'role', 'contract_status']


class OpportunityTaskViewSet(viewsets.ModelViewSet):
    """ViewSet for OpportunityTask"""
    queryset = OpportunityTask.objects.select_related('opportunity', 'assigned_to', 'assigned_by').all()
    serializer_class = OpportunityTaskSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['opportunity', 'assigned_to', 'status', 'priority', 'task_type']
    ordering_fields = ['due_date', 'priority', 'created_at']
    ordering = ['due_date']

    def perform_create(self, serializer):
        """Set assigned_by to current user"""
        serializer.save(assigned_by=self.request.user)

        # Log activity
        OpportunityActivity.objects.create(
            opportunity=serializer.instance.opportunity,
            user=self.request.user,
            activity_type='task_created',
            title=f'Task created: {serializer.instance.title}',
            metadata={'task_id': serializer.instance.id}
        )

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark task as completed"""
        task = self.get_object()
        task.status = 'completed'
        task.completed_at = timezone.now()
        task.save()

        # Log activity
        OpportunityActivity.objects.create(
            opportunity=task.opportunity,
            user=request.user,
            activity_type='task_completed',
            title=f'Task completed: {task.title}',
            metadata={'task_id': task.id}
        )

        serializer = self.get_serializer(task)
        return Response(serializer.data)


class OpportunityActivityViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for OpportunityActivity (read-only feed)"""
    queryset = OpportunityActivity.objects.select_related('opportunity', 'user').all()
    serializer_class = OpportunityActivitySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['opportunity', 'activity_type', 'user']
    ordering = ['-created_at']


class OpportunityCommentViewSet(viewsets.ModelViewSet):
    """ViewSet for OpportunityComment"""
    queryset = OpportunityComment.objects.select_related('opportunity', 'user').all()
    serializer_class = OpportunityCommentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['opportunity', 'is_internal']
    ordering = ['-created_at']

    def perform_create(self, serializer):
        """Set user to current user"""
        serializer.save(user=self.request.user)


class OpportunityDeliverableViewSet(viewsets.ModelViewSet):
    """ViewSet for OpportunityDeliverable"""
    queryset = OpportunityDeliverable.objects.select_related('opportunity').all()
    serializer_class = OpportunityDeliverableSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['opportunity', 'deliverable_type', 'status']
    ordering_fields = ['due_date', 'created_at']
    ordering = ['due_date']


class ApprovalViewSet(viewsets.ModelViewSet):
    """ViewSet for Approval"""
    queryset = Approval.objects.select_related('opportunity', 'deliverable', 'approver_contact', 'approver_user').all()
    serializer_class = ApprovalSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['opportunity', 'deliverable', 'stage', 'status']
    ordering = ['-submitted_at']

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve an approval request"""
        approval = self.get_object()
        approval.status = 'approved'
        approval.approved_at = timezone.now()
        approval.approver_user = request.user

        # Add notes if provided
        notes = request.data.get('notes', '')
        if notes:
            if approval.notes:
                approval.notes += f"\n\n[Approved by {request.user.full_name}]: {notes}"
            else:
                approval.notes = f"[Approved by {request.user.full_name}]: {notes}"

        approval.save()

        # Log activity
        OpportunityActivity.objects.create(
            opportunity=approval.opportunity,
            user=request.user,
            activity_type='approval_approved',
            title=f'Approval approved: {approval.get_stage_display()} v{approval.version}',
            metadata={'approval_id': approval.id, 'notes': notes}
        )

        serializer = self.get_serializer(approval)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject an approval request"""
        approval = self.get_object()
        notes = request.data.get('notes', '')

        if not notes:
            return Response(
                {'error': 'Rejection reason is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        approval.status = 'rejected'
        approval.approved_at = timezone.now()
        approval.approver_user = request.user

        if approval.notes:
            approval.notes += f"\n\n[Rejected by {request.user.full_name}]: {notes}"
        else:
            approval.notes = f"[Rejected by {request.user.full_name}]: {notes}"

        approval.save()

        # Log activity
        OpportunityActivity.objects.create(
            opportunity=approval.opportunity,
            user=request.user,
            activity_type='approval_rejected',
            title=f'Approval rejected: {approval.get_stage_display()} v{approval.version}',
            metadata={'approval_id': approval.id, 'notes': notes}
        )

        serializer = self.get_serializer(approval)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def request_changes(self, request, pk=None):
        """Request changes to an approval"""
        approval = self.get_object()
        notes = request.data.get('notes', '')

        if not notes:
            return Response(
                {'error': 'Change notes are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        approval.status = 'changes_requested'
        approval.approved_at = timezone.now()
        approval.approver_user = request.user

        if approval.notes:
            approval.notes += f"\n\n[Changes requested by {request.user.full_name}]: {notes}"
        else:
            approval.notes = f"[Changes requested by {request.user.full_name}]: {notes}"

        approval.save()

        # Log activity
        OpportunityActivity.objects.create(
            opportunity=approval.opportunity,
            user=request.user,
            activity_type='approval_changes_requested',
            title=f'Changes requested: {approval.get_stage_display()} v{approval.version}',
            metadata={'approval_id': approval.id, 'notes': notes}
        )

        serializer = self.get_serializer(approval)
        return Response(serializer.data)


class InvoiceViewSet(viewsets.ModelViewSet):
    """ViewSet for Invoice"""
    queryset = Invoice.objects.select_related('opportunity').all()
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['opportunity', 'invoice_type', 'status']
    ordering_fields = ['issue_date', 'due_date', 'created_at']
    ordering = ['-issue_date']


class DeliverablePackViewSet(viewsets.ModelViewSet):
    """ViewSet for DeliverablePack"""
    queryset = DeliverablePack.objects.prefetch_related('items').all()
    serializer_class = DeliverablePackSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'description']


class UsageTermsViewSet(viewsets.ModelViewSet):
    """ViewSet for UsageTerms"""
    queryset = UsageTerms.objects.all()
    serializer_class = UsageTermsSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['is_template', 'buyout']
    search_fields = ['name', 'exclusivity_category']
