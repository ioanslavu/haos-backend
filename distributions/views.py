from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Sum, Q, Value
from django.db.models.functions import Coalesce
from decimal import Decimal
from api.viewsets import OwnedResourceViewSet
from api.scoping import QuerysetScoping
from .models import Distribution, DistributionCatalogItem, DistributionRevenueReport
from .serializers import (
    DistributionListSerializer,
    DistributionDetailSerializer,
    DistributionCreateUpdateSerializer,
    DistributionCatalogItemListSerializer,
    DistributionCatalogItemDetailSerializer,
    DistributionCatalogItemCreateUpdateSerializer,
    DistributionRevenueReportSerializer,
)
from .filters import DistributionFilter, DistributionCatalogItemFilter, DistributionRevenueReportFilter
from .permissions import DistributionPermission


class DistributionViewSet(OwnedResourceViewSet):
    """
    ViewSet for Distribution CRUD operations with RBAC.

    Inherits from OwnedResourceViewSet which provides automatic RBAC filtering:
    - Admins: See all distributions
    - Department Managers: See all distributions in their department
    - Department Employees: See distributions they created
    - Guests/No Department: See nothing
    """
    queryset = Distribution.objects.all()
    permission_classes = [IsAuthenticated, DistributionPermission]
    serializer_class = DistributionListSerializer
    filterset_class = DistributionFilter
    search_fields = ['entity__display_name', 'notes', 'special_terms']
    ordering_fields = ['created_at', 'updated_at', 'signing_date', 'deal_type', 'deal_status']
    ordering = ['-created_at']

    # RBAC configuration
    queryset_scoping = QuerysetScoping.DEPARTMENT_WITH_OWNERSHIP
    ownership_field = 'created_by'
    select_related_fields = ['entity', 'contract', 'contact_person', 'created_by', 'department']
    prefetch_related_fields = ['catalog_items__recording', 'catalog_items__release']

    def get_queryset(self):
        """Override to add track_count and total_revenue annotations"""
        queryset = super().get_queryset()
        return queryset.annotate(
            track_count=Count('catalog_items'),
            total_revenue=Coalesce(
                Sum('catalog_items__revenue_reports__revenue_amount'),
                Value(Decimal('0.00'))
            )
        )

    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action == 'list':
            return DistributionListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return DistributionCreateUpdateSerializer
        return DistributionDetailSerializer

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get distribution statistics

        Returns:
        - total_distributions: Total number of distributions
        - by_status: Count of distributions by status
        - by_deal_type: Count of distributions by deal type
        - total_tracks: Total number of distributed tracks
        """
        queryset = self.filter_queryset(self.get_queryset())

        stats = {
            'total_distributions': queryset.count(),
            'by_status': {},
            'by_deal_type': {},
            'total_tracks': queryset.aggregate(total=Sum('track_count'))['total'] or 0,
        }

        # Count by status
        status_counts = queryset.values('deal_status').annotate(
            count=Count('id')
        ).order_by('deal_status')

        for item in status_counts:
            stats['by_status'][item['deal_status']] = item['count']

        # Count by deal type
        type_counts = queryset.values('deal_type').annotate(
            count=Count('id')
        ).order_by('deal_type')

        for item in type_counts:
            stats['by_deal_type'][item['deal_type']] = item['count']

        return Response(stats)


class DistributionCatalogItemViewSet(viewsets.ModelViewSet):
    """
    ViewSet for DistributionCatalogItem CRUD operations.
    Nested under Distribution: /distributions/{id}/catalog-items/
    """
    queryset = DistributionCatalogItem.objects.all()
    permission_classes = [IsAuthenticated, DistributionPermission]
    serializer_class = DistributionCatalogItemListSerializer
    filterset_class = DistributionCatalogItemFilter
    search_fields = ['recording__title', 'release__title', 'notes']
    ordering_fields = ['added_at', 'release_date', 'distribution_status']
    ordering = ['-added_at']

    select_related_fields = ['distribution', 'recording', 'release']
    prefetch_related_fields = ['revenue_reports']

    def get_queryset(self):
        """Filter by distribution_pk from URL"""
        queryset = super().get_queryset()
        distribution_pk = self.kwargs.get('distribution_pk')
        if distribution_pk:
            queryset = queryset.filter(distribution_id=distribution_pk)

        # Apply select_related and prefetch_related
        if hasattr(self, 'select_related_fields'):
            queryset = queryset.select_related(*self.select_related_fields)
        if hasattr(self, 'prefetch_related_fields'):
            queryset = queryset.prefetch_related(*self.prefetch_related_fields)

        return queryset

    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action == 'list':
            return DistributionCatalogItemListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return DistributionCatalogItemCreateUpdateSerializer
        return DistributionCatalogItemDetailSerializer

    def perform_create(self, serializer):
        """Set distribution from URL parameter"""
        distribution_pk = self.kwargs.get('distribution_pk')
        serializer.save(distribution_id=distribution_pk)


class DistributionRevenueReportViewSet(viewsets.ModelViewSet):
    """
    ViewSet for DistributionRevenueReport CRUD operations.
    Nested under DistributionCatalogItem: /distributions/{id}/catalog-items/{id}/revenue-reports/
    """
    queryset = DistributionRevenueReport.objects.all()
    permission_classes = [IsAuthenticated, DistributionPermission]
    serializer_class = DistributionRevenueReportSerializer
    filterset_class = DistributionRevenueReportFilter
    search_fields = ['notes']
    ordering_fields = ['reporting_period', 'revenue_amount', 'platform']
    ordering = ['-reporting_period']

    select_related_fields = ['catalog_item', 'created_by']

    def get_queryset(self):
        """Filter by catalog_item_pk from URL"""
        queryset = super().get_queryset()
        catalog_item_pk = self.kwargs.get('catalog_item_pk')
        if catalog_item_pk:
            queryset = queryset.filter(catalog_item_id=catalog_item_pk)

        # Apply select_related
        if hasattr(self, 'select_related_fields'):
            queryset = queryset.select_related(*self.select_related_fields)

        return queryset

    def perform_create(self, serializer):
        """Set catalog_item and created_by from context"""
        catalog_item_pk = self.kwargs.get('catalog_item_pk')
        serializer.save(
            catalog_item_id=catalog_item_pk,
            created_by=self.request.user
        )
