from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Sum, Q, F, DecimalField
from django.db.models.functions import Coalesce
from decimal import Decimal
from api.viewsets import OwnedResourceViewSet
from api.scoping import QuerysetScoping
from .models import Campaign
from .serializers import (
    CampaignListSerializer,
    CampaignDetailSerializer,
    CampaignCreateUpdateSerializer
)
from .filters import CampaignFilter
from .permissions import CampaignPermission


class CampaignViewSet(OwnedResourceViewSet):
    """
    ViewSet for Campaign CRUD operations and analytics with RBAC.

    Inherits from OwnedResourceViewSet which provides automatic RBAC filtering:
    - Admins: See all campaigns
    - Department Managers: See all campaigns in their department
    - Department Employees: See campaigns they created OR are assigned to (handlers)
    - Guests/No Department: See nothing

    All role/permission logic is handled by the parent class - no hardcoded checks!
    """
    queryset = Campaign.objects.all()
    permission_classes = [IsAuthenticated, CampaignPermission]
    serializer_class = CampaignListSerializer  # Default serializer
    filterset_class = CampaignFilter
    search_fields = ['campaign_name', 'notes', 'client__display_name', 'artist__display_name', 'brand__display_name', 'song__title']
    ordering_fields = ['created_at', 'updated_at', 'campaign_name', 'value', 'status', 'confirmed_at']
    ordering = ['-created_at']

    # BaseViewSet configuration (replaces get_queryset hardcoded logic)
    queryset_scoping = QuerysetScoping.DEPARTMENT_WITH_OWNERSHIP
    ownership_field = 'created_by'
    assigned_field = 'handlers'
    assigned_through_field = 'user'  # CampaignHandler.user
    select_related_fields = ['client', 'artist', 'brand', 'song', 'created_by', 'department']
    prefetch_related_fields = ['handlers__user']

    # NO get_queryset() override needed - parent handles all RBAC filtering!

    def get_serializer_class(self):
        """
        Use different serializers for different actions
        """
        if self.action == 'list':
            return CampaignListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return CampaignCreateUpdateSerializer
        return CampaignDetailSerializer

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get campaign statistics

        Returns:
        - total_campaigns: Total number of campaigns
        - total_value: Sum of all campaign values
        - by_status: Count of campaigns by status
        - recent_campaigns: 5 most recent campaigns
        """
        queryset = self.filter_queryset(self.get_queryset())

        stats = {
            'total_campaigns': queryset.count(),
            'total_value': str(queryset.aggregate(
                total=Coalesce(Sum('value'), Decimal('0'), output_field=DecimalField())
            )['total']),
            'by_status': {}
        }

        # Count by status
        status_counts = queryset.values('status').annotate(
            count=Count('id')
        ).order_by('status')

        for item in status_counts:
            stats['by_status'][item['status']] = item['count']

        # Recent campaigns
        recent = queryset.order_by('-created_at')[:5]
        stats['recent_campaigns'] = CampaignListSerializer(recent, many=True).data

        return Response(stats)

    @action(detail=False, methods=['get'], url_path='brand_analytics')
    def brand_analytics(self, request):
        """
        Get analytics for all brands

        Returns list of brands with:
        - total_campaigns: Number of campaigns for this brand
        - total_value: Sum of campaign values
        - unique_artists: Number of unique artists used
        - campaigns_by_status: Count by status
        """
        from identity.models import Entity

        # Get all entities with brand role
        brands = Entity.objects.filter(
            entity_roles__role='brand'
        ).distinct()

        analytics = []

        for brand in brands:
            brand_campaigns = Campaign.objects.filter(brand=brand).select_related(
            'client', 'artist', 'brand', 'song', 'created_by'
        )

            brand_stats = {
                'brand_id': brand.id,
                'brand_name': brand.display_name,
                'total_campaigns': brand_campaigns.count(),
                'total_value': str(brand_campaigns.aggregate(
                    total=Coalesce(Sum('value'), Decimal('0'), output_field=DecimalField())
                )['total']),
                'unique_artists': brand_campaigns.values('artist').distinct().count(),
                'campaigns_by_status': {}
            }

            # Count by status
            status_counts = brand_campaigns.values('status').annotate(
                count=Count('id')
            )

            for item in status_counts:
                brand_stats['campaigns_by_status'][item['status']] = item['count']

            # Get artist usage
            artist_usage = brand_campaigns.values(
                'artist__id',
                'artist__display_name'
            ).annotate(
                campaign_count=Count('id')
            ).order_by('-campaign_count')

            brand_stats['artists'] = [
                {
                    'id': item['artist__id'],
                    'name': item['artist__display_name'],
                    'campaign_count': item['campaign_count']
                }
                for item in artist_usage
            ]

            # Recent campaigns
            recent = brand_campaigns.order_by('-created_at')[:5]
            brand_stats['recent_campaigns'] = CampaignListSerializer(recent, many=True).data

            analytics.append(brand_stats)

        # Sort by total campaigns descending
        analytics.sort(key=lambda x: x['total_campaigns'], reverse=True)

        return Response(analytics)

    def brand_analytics_detail(self, request, brand_id=None):
        """
        Get analytics for a specific brand with RBAC filtering

        URL: /api/v1/campaigns/brand_analytics/{brand_id}/
        Note: This is manually routed in urls.py
        """
        from identity.models import Entity

        try:
            brand = Entity.objects.get(id=brand_id, entity_roles__role='brand')
        except Entity.DoesNotExist:
            return Response(
                {'error': 'Brand not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Use get_queryset() to respect RBAC filtering
        base_queryset = self.get_queryset()
        brand_campaigns = base_queryset.filter(brand=brand)

        analytics = {
            'brand_id': brand.id,
            'brand_name': brand.display_name,
            'total_campaigns': brand_campaigns.count(),
            'total_value': str(brand_campaigns.aggregate(
                total=Coalesce(Sum('value'), Decimal('0'), output_field=DecimalField())
            )['total']),
            'unique_artists': brand_campaigns.values('artist').distinct().count(),
            'campaigns_by_status': {}
        }

        # Count by status
        status_counts = brand_campaigns.values('status').annotate(
            count=Count('id')
        )

        for item in status_counts:
            analytics['campaigns_by_status'][item['status']] = item['count']

        # Get artist usage
        artist_usage = brand_campaigns.values(
            'artist__id',
            'artist__display_name'
        ).annotate(
            campaign_count=Count('id')
        ).order_by('-campaign_count')

        analytics['artists'] = [
            {
                'id': item['artist__id'],
                'name': item['artist__display_name'],
                'campaign_count': item['campaign_count']
            }
            for item in artist_usage
        ]

        # Recent campaigns
        recent = brand_campaigns.order_by('-created_at')[:10]
        analytics['recent_campaigns'] = CampaignListSerializer(recent, many=True).data

        # All campaigns for this brand
        all_campaigns = brand_campaigns.order_by('-created_at')
        analytics['campaigns'] = CampaignListSerializer(all_campaigns, many=True).data

        return Response(analytics)

    @action(detail=False, methods=['get'], url_path='artist_analytics')
    def artist_analytics(self, request):
        """
        Get analytics for all artists

        Returns list of artists with:
        - total_campaigns: Number of campaigns for this artist
        - total_value: Sum of campaign values
        - unique_clients: Number of unique clients
        - unique_brands: Number of unique brands
        - campaigns_by_status: Count by status
        """
        from identity.models import Entity

        # Get all entities with artist role
        artists = Entity.objects.filter(
            entity_roles__role='artist'
        ).distinct()

        analytics = []

        for artist in artists:
            artist_campaigns = Campaign.objects.filter(artist=artist).select_related(
                'client', 'artist', 'brand', 'song', 'created_by'
            )

            artist_stats = {
                'artist_id': artist.id,
                'artist_name': artist.display_name,
                'total_campaigns': artist_campaigns.count(),
                'total_value': str(artist_campaigns.aggregate(
                    total=Coalesce(Sum('value'), Decimal('0'), output_field=DecimalField())
                )['total']),
                'unique_clients': artist_campaigns.values('client').distinct().count(),
                'unique_brands': artist_campaigns.values('brand').distinct().count(),
                'campaigns_by_status': {}
            }

            # Count by status
            status_counts = artist_campaigns.values('status').annotate(
                count=Count('id')
            )

            for item in status_counts:
                artist_stats['campaigns_by_status'][item['status']] = item['count']

            # Get brand usage
            brand_usage = artist_campaigns.values(
                'brand__id',
                'brand__display_name'
            ).annotate(
                campaign_count=Count('id')
            ).order_by('-campaign_count')

            artist_stats['brands'] = [
                {
                    'id': item['brand__id'],
                    'name': item['brand__display_name'],
                    'campaign_count': item['campaign_count']
                }
                for item in brand_usage
            ]

            # Get client usage
            client_usage = artist_campaigns.values(
                'client__id',
                'client__display_name'
            ).annotate(
                campaign_count=Count('id')
            ).order_by('-campaign_count')

            artist_stats['clients'] = [
                {
                    'id': item['client__id'],
                    'name': item['client__display_name'],
                    'campaign_count': item['campaign_count']
                }
                for item in client_usage
            ]

            # Recent campaigns
            recent = artist_campaigns.order_by('-created_at')[:5]
            artist_stats['recent_campaigns'] = CampaignListSerializer(recent, many=True).data

            analytics.append(artist_stats)

        # Sort by total campaigns descending
        analytics.sort(key=lambda x: x['total_campaigns'], reverse=True)

        return Response(analytics)

    def artist_analytics_detail(self, request, artist_id=None):
        """
        Get analytics for a specific artist with RBAC filtering

        URL: /api/v1/campaigns/artist_analytics/{artist_id}/
        Note: This is manually routed in urls.py
        """
        from identity.models import Entity

        try:
            artist = Entity.objects.get(id=artist_id, entity_roles__role='artist')
        except Entity.DoesNotExist:
            return Response(
                {'error': 'Artist not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Use get_queryset() to respect RBAC filtering
        base_queryset = self.get_queryset()
        artist_campaigns = base_queryset.filter(artist=artist)

        analytics = {
            'artist_id': artist.id,
            'artist_name': artist.display_name,
            'total_campaigns': artist_campaigns.count(),
            'total_value': str(artist_campaigns.aggregate(
                total=Coalesce(Sum('value'), Decimal('0'), output_field=DecimalField())
            )['total']),
            'unique_clients': artist_campaigns.values('client').distinct().count(),
            'unique_brands': artist_campaigns.values('brand').distinct().count(),
            'campaigns_by_status': {}
        }

        # Count by status
        status_counts = artist_campaigns.values('status').annotate(
            count=Count('id')
        )

        for item in status_counts:
            analytics['campaigns_by_status'][item['status']] = item['count']

        # Get brand usage
        brand_usage = artist_campaigns.values(
            'brand__id',
            'brand__display_name'
        ).annotate(
            campaign_count=Count('id')
        ).order_by('-campaign_count')

        analytics['brands'] = [
            {
                'id': item['brand__id'],
                'name': item['brand__display_name'],
                'campaign_count': item['campaign_count']
            }
            for item in brand_usage
        ]

        # Get client usage
        client_usage = artist_campaigns.values(
            'client__id',
            'client__display_name'
        ).annotate(
            campaign_count=Count('id')
        ).order_by('-campaign_count')

        analytics['clients'] = [
            {
                'id': item['client__id'],
                'name': item['client__display_name'],
                'campaign_count': item['campaign_count']
            }
            for item in client_usage
        ]

        # Recent campaigns
        recent = artist_campaigns.order_by('-created_at')[:10]
        analytics['recent_campaigns'] = CampaignListSerializer(recent, many=True).data

        # All campaigns for this artist
        all_campaigns = artist_campaigns.order_by('-created_at')
        analytics['campaigns'] = CampaignListSerializer(all_campaigns, many=True).data

        return Response(analytics)

    @action(detail=False, methods=['get'], url_path='client_analytics')
    def client_analytics(self, request):
        """
        Get analytics for all clients

        Returns list of clients with:
        - total_campaigns: Number of campaigns for this client
        - total_value: Sum of campaign values
        - unique_artists: Number of unique artists
        - unique_brands: Number of unique brands
        - campaigns_by_status: Count by status
        """
        from identity.models import Entity

        # Get all entities with client role
        clients = Entity.objects.filter(
            entity_roles__role='client'
        ).distinct()

        analytics = []

        for client in clients:
            client_campaigns = Campaign.objects.filter(client=client).select_related(
                'client', 'artist', 'brand', 'song', 'created_by'
            )

            client_stats = {
                'client_id': client.id,
                'client_name': client.display_name,
                'total_campaigns': client_campaigns.count(),
                'total_value': str(client_campaigns.aggregate(
                    total=Coalesce(Sum('value'), Decimal('0'), output_field=DecimalField())
                )['total']),
                'unique_artists': client_campaigns.values('artist').distinct().count(),
                'unique_brands': client_campaigns.values('brand').distinct().count(),
                'campaigns_by_status': {}
            }

            # Count by status
            status_counts = client_campaigns.values('status').annotate(
                count=Count('id')
            )

            for item in status_counts:
                client_stats['campaigns_by_status'][item['status']] = item['count']

            # Get artist usage
            artist_usage = client_campaigns.values(
                'artist__id',
                'artist__display_name'
            ).annotate(
                campaign_count=Count('id')
            ).order_by('-campaign_count')

            client_stats['artists'] = [
                {
                    'id': item['artist__id'],
                    'name': item['artist__display_name'],
                    'campaign_count': item['campaign_count']
                }
                for item in artist_usage
            ]

            # Get brand usage
            brand_usage = client_campaigns.values(
                'brand__id',
                'brand__display_name'
            ).annotate(
                campaign_count=Count('id')
            ).order_by('-campaign_count')

            client_stats['brands'] = [
                {
                    'id': item['brand__id'],
                    'name': item['brand__display_name'],
                    'campaign_count': item['campaign_count']
                }
                for item in brand_usage
            ]

            # Recent campaigns
            recent = client_campaigns.order_by('-created_at')[:5]
            client_stats['recent_campaigns'] = CampaignListSerializer(recent, many=True).data

            analytics.append(client_stats)

        # Sort by total campaigns descending
        analytics.sort(key=lambda x: x['total_campaigns'], reverse=True)

        return Response(analytics)

    def client_analytics_detail(self, request, client_id=None):
        """
        Get analytics for a specific client with RBAC filtering

        URL: /api/v1/campaigns/client_analytics/{client_id}/
        Note: This is manually routed in urls.py
        """
        from identity.models import Entity

        try:
            client = Entity.objects.get(id=client_id, entity_roles__role='client')
        except Entity.DoesNotExist:
            return Response(
                {'error': 'Client not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Use get_queryset() to respect RBAC filtering
        base_queryset = self.get_queryset()
        client_campaigns = base_queryset.filter(client=client)

        analytics = {
            'client_id': client.id,
            'client_name': client.display_name,
            'total_campaigns': client_campaigns.count(),
            'total_value': str(client_campaigns.aggregate(
                total=Coalesce(Sum('value'), Decimal('0'), output_field=DecimalField())
            )['total']),
            'unique_artists': client_campaigns.values('artist').distinct().count(),
            'unique_brands': client_campaigns.values('brand').distinct().count(),
            'campaigns_by_status': {}
        }

        # Count by status
        status_counts = client_campaigns.values('status').annotate(
            count=Count('id')
        )

        for item in status_counts:
            analytics['campaigns_by_status'][item['status']] = item['count']

        # Get artist usage
        artist_usage = client_campaigns.values(
            'artist__id',
            'artist__display_name'
        ).annotate(
            campaign_count=Count('id')
        ).order_by('-campaign_count')

        analytics['artists'] = [
            {
                'id': item['artist__id'],
                'name': item['artist__display_name'],
                'campaign_count': item['campaign_count']
            }
            for item in artist_usage
        ]

        # Get brand usage
        brand_usage = client_campaigns.values(
            'brand__id',
            'brand__display_name'
        ).annotate(
            campaign_count=Count('id')
        ).order_by('-campaign_count')

        analytics['brands'] = [
            {
                'id': item['brand__id'],
                'name': item['brand__display_name'],
                'campaign_count': item['campaign_count']
            }
            for item in brand_usage
        ]

        # Recent campaigns
        recent = client_campaigns.order_by('-created_at')[:10]
        analytics['recent_campaigns'] = CampaignListSerializer(recent, many=True).data

        # All campaigns for this client
        all_campaigns = client_campaigns.order_by('-created_at')
        analytics['campaigns'] = CampaignListSerializer(all_campaigns, many=True).data

        return Response(analytics)
