from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Sum, Q, Avg
from django.utils import timezone
from decimal import Decimal
from api.viewsets import OwnedResourceViewSet
from api.scoping import QuerysetScoping
from .models import (
    Brief, Opportunity, Proposal, ProposalArtist,
    DeliverablePack, DeliverablePackItem, UsageTerms,
    Deal, DealArtist, DealDeliverable, Approval, Invoice
)
from .serializers import (
    BriefListSerializer, BriefDetailSerializer,
    OpportunityListSerializer, OpportunityDetailSerializer,
    ProposalListSerializer, ProposalDetailSerializer, ProposalArtistSerializer,
    DeliverablePackListSerializer, DeliverablePackDetailSerializer, DeliverablePackItemSerializer,
    UsageTermsListSerializer, UsageTermsDetailSerializer,
    DealListSerializer, DealDetailSerializer, DealArtistSerializer,
    DealDeliverableSerializer, ApprovalSerializer, InvoiceSerializer
)
from .filters import BriefFilter, OpportunityFilter, ProposalFilter, DealFilter
from .permissions import ArtistSalesPermission


class BriefViewSet(OwnedResourceViewSet):
    """
    ViewSet for Brief CRUD operations with RBAC.
    """
    queryset = Brief.objects.all()
    permission_classes = [IsAuthenticated, ArtistSalesPermission]
    serializer_class = BriefListSerializer
    filterset_class = BriefFilter
    search_fields = ['campaign_title', 'brand_category', 'objectives', 'notes', 'account__display_name']
    ordering_fields = ['created_at', 'updated_at', 'received_date', 'sla_due_date', 'brief_status']
    ordering = ['-created_at']

    queryset_scoping = QuerysetScoping.DEPARTMENT_WITH_OWNERSHIP
    ownership_field = 'created_by'
    select_related_fields = ['account', 'contact_person', 'created_by', 'department']

    def get_serializer_class(self):
        if self.action == 'list':
            return BriefListSerializer
        return BriefDetailSerializer

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get brief statistics"""
        queryset = self.filter_queryset(self.get_queryset())

        stats = {
            'total_briefs': queryset.count(),
            'by_status': {},
            'overdue_count': queryset.filter(
                sla_due_date__lt=timezone.now().date(),
                brief_status__in=['new', 'qualified']
            ).count()
        }

        # Count by status
        status_counts = queryset.values('brief_status').annotate(count=Count('id'))
        for item in status_counts:
            stats['by_status'][item['brief_status']] = item['count']

        return Response(stats)


class OpportunityViewSet(OwnedResourceViewSet):
    """
    ViewSet for Opportunity CRUD operations with RBAC.
    """
    queryset = Opportunity.objects.all()
    permission_classes = [IsAuthenticated, ArtistSalesPermission]
    serializer_class = OpportunityListSerializer
    filterset_class = OpportunityFilter
    search_fields = ['opp_name', 'next_step', 'notes', 'account__display_name']
    ordering_fields = ['created_at', 'updated_at', 'expected_close_date', 'amount_expected', 'probability_percent', 'stage']
    ordering = ['-created_at']

    queryset_scoping = QuerysetScoping.DEPARTMENT_WITH_OWNERSHIP
    ownership_field = 'created_by'
    select_related_fields = ['brief', 'account', 'owner_user', 'created_by', 'department']

    def get_serializer_class(self):
        if self.action == 'list':
            return OpportunityListSerializer
        return OpportunityDetailSerializer

    @action(detail=False, methods=['get'])
    def pipeline(self, request):
        """Get sales pipeline statistics"""
        queryset = self.filter_queryset(self.get_queryset())

        pipeline = {
            'total_opportunities': queryset.count(),
            'total_value': str(queryset.aggregate(Sum('amount_expected'))['amount_expected__sum'] or 0),
            'weighted_value': 0,
            'by_stage': {}
        }

        # Calculate weighted value and count by stage
        for opp in queryset:
            if opp.amount_expected and opp.probability_percent:
                weighted = (opp.amount_expected * opp.probability_percent) / 100
                pipeline['weighted_value'] += float(weighted)

        pipeline['weighted_value'] = str(Decimal(str(pipeline['weighted_value'])))

        # Count by stage
        stage_counts = queryset.values('stage').annotate(
            count=Count('id'),
            total_value=Sum('amount_expected')
        )
        for item in stage_counts:
            pipeline['by_stage'][item['stage']] = {
                'count': item['count'],
                'total_value': str(item['total_value'] or 0)
            }

        return Response(pipeline)

    @action(detail=True, methods=['post'])
    def convert_to_deal(self, request, pk=None):
        """Convert opportunity to deal"""
        opportunity = self.get_object()

        if opportunity.stage == 'closed_lost':
            return Response(
                {'error': 'Cannot convert a lost opportunity to a deal'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create deal from opportunity
        deal = Deal.objects.create(
            opportunity=opportunity,
            account=opportunity.account,
            deal_title=opportunity.opp_name,
            fee_total=opportunity.amount_expected or Decimal('0.00'),
            currency=opportunity.currency,
            department=opportunity.department,
            created_by=request.user
        )

        # Update opportunity stage
        opportunity.stage = 'completed'
        opportunity.actual_close_date = timezone.now().date()
        opportunity.save()

        return Response(
            DealDetailSerializer(deal).data,
            status=status.HTTP_201_CREATED
        )


class ProposalViewSet(OwnedResourceViewSet):
    """
    ViewSet for Proposal CRUD operations with RBAC.
    """
    queryset = Proposal.objects.all()
    permission_classes = [IsAuthenticated, ArtistSalesPermission]
    serializer_class = ProposalListSerializer
    filterset_class = ProposalFilter
    search_fields = ['opportunity__opp_name', 'notes']
    ordering_fields = ['created_at', 'updated_at', 'version', 'sent_date', 'fee_net']
    ordering = ['-created_at']

    queryset_scoping = QuerysetScoping.DEPARTMENT
    department_field = 'opportunity__department'
    select_related_fields = ['opportunity', 'opportunity__account', 'created_by']
    prefetch_related_fields = ['proposal_artists__artist']

    def get_serializer_class(self):
        if self.action == 'list':
            return ProposalListSerializer
        return ProposalDetailSerializer

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get proposal statistics"""
        queryset = self.filter_queryset(self.get_queryset())

        stats = {
            'total_proposals': queryset.count(),
            'total_value': str(queryset.aggregate(Sum('fee_net'))['fee_net__sum'] or 0),
            'by_status': {},
            'avg_version': queryset.aggregate(Avg('version'))['version__avg'] or 0
        }

        # Count by status
        status_counts = queryset.values('proposal_status').annotate(
            count=Count('id'),
            total_value=Sum('fee_net')
        )
        for item in status_counts:
            stats['by_status'][item['proposal_status']] = {
                'count': item['count'],
                'total_value': str(item['total_value'] or 0)
            }

        return Response(stats)

    @action(detail=True, methods=['post'])
    def send_to_client(self, request, pk=None):
        """Send proposal to client via email"""
        from django.core.mail import send_mail
        from django.conf import settings

        proposal = self.get_object()
        recipient_email = request.data.get('recipient_email')
        cc_emails = request.data.get('cc_emails', [])
        message = request.data.get('message', '')

        if not recipient_email:
            return Response(
                {'error': 'recipient_email is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update proposal status to sent
        proposal.proposal_status = 'sent'
        if not proposal.sent_date:
            proposal.sent_date = timezone.now()
        proposal.save()

        # Email content
        subject = f"Proposal {proposal.opportunity.opp_name} - Version {proposal.version}"

        email_body = f"""
Dear Client,

{message if message else 'Please find attached our proposal for your review.'}

Proposal Details:
- Opportunity: {proposal.opportunity.opp_name}
- Version: {proposal.version}
- Total Value: {proposal.currency} {proposal.fee_net}
- Valid Until: {proposal.valid_until.strftime('%Y-%m-%d') if proposal.valid_until else 'N/A'}

Artists Included:
"""
        for pa in proposal.proposal_artists.all():
            email_body += f"- {pa.artist.name} ({pa.get_role_display()})\n"

        email_body += f"""

Please review and let us know if you have any questions.

Best regards,
{proposal.created_by.get_full_name() if proposal.created_by else 'The Team'}
"""

        try:
            send_mail(
                subject=subject,
                message=email_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient_email] + cc_emails,
                fail_silently=False,
            )
            return Response({
                'message': 'Proposal sent successfully',
                'proposal': ProposalDetailSerializer(proposal).data
            })
        except Exception as e:
            return Response(
                {'error': f'Failed to send email: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Create a new version of the proposal"""
        original = self.get_object()

        # Get the next version number
        max_version = Proposal.objects.filter(
            opportunity=original.opportunity
        ).aggregate(max_v=Count('version'))['max_v'] or 0

        # Create new proposal
        new_proposal = Proposal.objects.create(
            opportunity=original.opportunity,
            version=max_version + 1,
            fee_gross=original.fee_gross,
            discounts=original.discounts,
            agency_fee=original.agency_fee,
            currency=original.currency,
            notes=original.notes,
            created_by=request.user
        )

        # Copy artists
        for pa in original.proposal_artists.all():
            ProposalArtist.objects.create(
                proposal=new_proposal,
                artist=pa.artist,
                role=pa.role,
                proposed_fee=pa.proposed_fee
            )

        return Response(
            ProposalDetailSerializer(new_proposal).data,
            status=status.HTTP_201_CREATED
        )


class DeliverablePackViewSet(viewsets.ModelViewSet):
    """
    ViewSet for DeliverablePack CRUD operations.
    """
    queryset = DeliverablePack.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = DeliverablePackListSerializer
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'updated_at', 'name']
    ordering = ['name']

    def get_serializer_class(self):
        if self.action == 'list':
            return DeliverablePackListSerializer
        return DeliverablePackDetailSerializer


class UsageTermsViewSet(viewsets.ModelViewSet):
    """
    ViewSet for UsageTerms CRUD operations.
    """
    queryset = UsageTerms.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = UsageTermsListSerializer
    search_fields = ['name', 'notes']
    ordering_fields = ['created_at', 'updated_at', 'name']
    ordering = ['name']

    def get_queryset(self):
        """Filter templates vs custom terms"""
        queryset = super().get_queryset()
        is_template = self.request.query_params.get('is_template', None)
        if is_template is not None:
            queryset = queryset.filter(is_template=is_template.lower() == 'true')
        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return UsageTermsListSerializer
        return UsageTermsDetailSerializer


class DealViewSet(OwnedResourceViewSet):
    """
    ViewSet for Deal CRUD operations with RBAC.
    """
    queryset = Deal.objects.all()
    permission_classes = [IsAuthenticated, ArtistSalesPermission]
    serializer_class = DealListSerializer
    filterset_class = DealFilter
    search_fields = ['deal_title', 'contract_number', 'po_number', 'notes', 'account__display_name']
    ordering_fields = ['created_at', 'updated_at', 'start_date', 'end_date', 'fee_total', 'deal_status']
    ordering = ['-created_at']

    queryset_scoping = QuerysetScoping.DEPARTMENT_WITH_OWNERSHIP
    ownership_field = 'created_by'
    select_related_fields = ['opportunity', 'account', 'deliverable_pack', 'usage_terms', 'created_by', 'department']
    prefetch_related_fields = ['deal_artists__artist', 'deliverables', 'approvals', 'invoices']

    def get_serializer_class(self):
        if self.action == 'list':
            return DealListSerializer
        return DealDetailSerializer

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get deal statistics"""
        queryset = self.filter_queryset(self.get_queryset())

        stats = {
            'total_deals': queryset.count(),
            'total_value': str(queryset.aggregate(Sum('fee_total'))['fee_total__sum'] or 0),
            'by_status': {},
            'expiring_soon': queryset.filter(
                end_date__lte=timezone.now().date() + timezone.timedelta(days=30),
                deal_status__in=['signed', 'active']
            ).count()
        }

        # Count by status
        status_counts = queryset.values('deal_status').annotate(
            count=Count('id'),
            total_value=Sum('fee_total')
        )
        for item in status_counts:
            stats['by_status'][item['deal_status']] = {
                'count': item['count'],
                'total_value': str(item['total_value'] or 0)
            }

        return Response(stats)

    @action(detail=True, methods=['get'])
    def deliverables(self, request, pk=None):
        """Get all deliverables for this deal"""
        deal = self.get_object()
        deliverables = deal.deliverables.all()
        serializer = DealDeliverableSerializer(deliverables, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_deliverable(self, request, pk=None):
        """Add a deliverable to this deal"""
        deal = self.get_object()
        serializer = DealDeliverableSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(deal=deal)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def approvals(self, request, pk=None):
        """Get all approvals for this deal"""
        deal = self.get_object()
        approvals = deal.approvals.all()
        serializer = ApprovalSerializer(approvals, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_approval(self, request, pk=None):
        """Add an approval to this deal"""
        deal = self.get_object()
        serializer = ApprovalSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(deal=deal)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def invoices(self, request, pk=None):
        """Get all invoices for this deal"""
        deal = self.get_object()
        invoices = deal.invoices.all()
        serializer = InvoiceSerializer(invoices, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_invoice(self, request, pk=None):
        """Add an invoice to this deal"""
        deal = self.get_object()
        serializer = InvoiceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(deal=deal)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DealDeliverableViewSet(viewsets.ModelViewSet):
    """
    ViewSet for DealDeliverable CRUD operations.
    """
    queryset = DealDeliverable.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = DealDeliverableSerializer
    search_fields = ['description', 'notes']
    ordering_fields = ['created_at', 'updated_at', 'due_date', 'status']
    ordering = ['due_date']

    def get_queryset(self):
        """Filter by deal if provided"""
        queryset = super().get_queryset()
        deal_id = self.request.query_params.get('deal_id', None)
        if deal_id is not None:
            queryset = queryset.filter(deal_id=deal_id)
        return queryset


class ApprovalViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Approval CRUD operations.
    """
    queryset = Approval.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = ApprovalSerializer
    search_fields = ['notes']
    ordering_fields = ['submitted_at', 'approved_at', 'status', 'stage']
    ordering = ['-submitted_at']

    def get_queryset(self):
        """Filter by deal if provided"""
        queryset = super().get_queryset()
        deal_id = self.request.query_params.get('deal_id', None)
        if deal_id is not None:
            queryset = queryset.filter(deal_id=deal_id)
        return queryset


class DealArtistViewSet(viewsets.ModelViewSet):
    """
    ViewSet for DealArtist CRUD operations.
    """
    queryset = DealArtist.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = DealArtistSerializer
    ordering_fields = ['created_at', 'updated_at', 'artist_fee', 'contract_status']
    ordering = ['created_at']

    def get_queryset(self):
        """Filter by deal if provided"""
        queryset = super().get_queryset().select_related('artist', 'deal')
        deal_id = self.request.query_params.get('deal_id', None)
        if deal_id is not None:
            queryset = queryset.filter(deal_id=deal_id)
        return queryset


class ProposalArtistViewSet(viewsets.ModelViewSet):
    """
    ViewSet for ProposalArtist CRUD operations.
    """
    queryset = ProposalArtist.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = ProposalArtistSerializer
    ordering_fields = ['created_at', 'role', 'proposed_fee']
    ordering = ['created_at']

    def get_queryset(self):
        """Filter by proposal if provided"""
        queryset = super().get_queryset().select_related('artist', 'proposal')
        proposal_id = self.request.query_params.get('proposal_id', None)
        if proposal_id is not None:
            queryset = queryset.filter(proposal_id=proposal_id)
        return queryset


class InvoiceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Invoice CRUD operations.
    """
    queryset = Invoice.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = InvoiceSerializer
    search_fields = ['invoice_number', 'notes']
    ordering_fields = ['created_at', 'updated_at', 'issue_date', 'due_date', 'amount', 'status']
    ordering = ['-issue_date']

    def get_queryset(self):
        """Filter by deal if provided"""
        queryset = super().get_queryset()
        deal_id = self.request.query_params.get('deal_id', None)
        if deal_id is not None:
            queryset = queryset.filter(deal_id=deal_id)
        return queryset

    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """Get overdue invoices"""
        queryset = self.get_queryset().filter(
            status__in=['issued', 'sent'],
            due_date__lt=timezone.now().date()
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
