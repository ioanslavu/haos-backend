from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters import rest_framework as django_filters
from django.db.models import Q, Count, Sum
from django.db import transaction
from django.utils import timezone
from .models import Publication, PublicationReport
from .serializers import (
    PublicationListSerializer, PublicationDetailSerializer,
    PublicationCreateUpdateSerializer, PublicationBulkCreateSerializer,
    CoverageReportSerializer, TerritoryStatsSerializer,
    PlatformStatsSerializer, UpdateMetricsSerializer,
    PublicationActionSerializer
)
from catalog.models import Recording, Release


class PublicationFilter(django_filters.FilterSet):
    """Filter for Publication model."""

    object_type = django_filters.ChoiceFilter(choices=Publication.OBJECT_TYPE_CHOICES)
    platform = django_filters.ChoiceFilter(choices=Publication.PLATFORM_CHOICES)
    territory = django_filters.CharFilter(lookup_expr='iexact')
    status = django_filters.ChoiceFilter(choices=Publication.STATUS_CHOICES)
    channel = django_filters.ChoiceFilter(choices=Publication.CHANNEL_CHOICES)
    is_monetized = django_filters.BooleanFilter()
    is_active = django_filters.BooleanFilter()
    published_after = django_filters.DateTimeFilter(field_name='published_at', lookup_expr='gte')
    published_before = django_filters.DateTimeFilter(field_name='published_at', lookup_expr='lte')
    search = django_filters.CharFilter(method='filter_search')

    class Meta:
        model = Publication
        fields = ['object_type', 'platform', 'territory', 'status', 'channel',
                  'is_monetized', 'is_active']

    def filter_search(self, queryset, name, value):
        """Search publications by URL, external ID, or owner account."""
        return queryset.filter(
            Q(url__icontains=value) |
            Q(external_id__icontains=value) |
            Q(owner_account__icontains=value) |
            Q(distributor__icontains=value) |
            Q(notes__icontains=value)
        )


class PublicationViewSet(viewsets.ModelViewSet):
    """ViewSet for Publication model."""

    queryset = Publication.objects.all()
    permission_classes = [IsAuthenticated]
    filterset_class = PublicationFilter
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    search_fields = ['url', 'external_id', 'owner_account', 'distributor', 'notes']
    ordering_fields = ['published_at', 'platform', 'territory', 'created_at']
    ordering = ['-published_at', '-created_at']

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return PublicationListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return PublicationCreateUpdateSerializer
        elif self.action == 'bulk_create':
            return PublicationBulkCreateSerializer
        elif self.action == 'update_metrics':
            return UpdateMetricsSerializer
        elif self.action in ['go_live', 'schedule', 'take_down']:
            return PublicationActionSerializer
        return PublicationDetailSerializer

    def get_queryset(self):
        """Optimize queryset."""
        return super().get_queryset()

    @action(detail=False, methods=['get'])
    def by_object(self, request):
        """Get publications for a specific object."""
        object_type = request.query_params.get('object_type')
        object_id = request.query_params.get('object_id')

        if not object_type or not object_id:
            return Response(
                {'error': 'object_type and object_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        publications = self.get_queryset().filter(
            object_type=object_type,
            object_id=object_id
        )

        page = self.paginate_queryset(publications)
        if page is not None:
            serializer = PublicationListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = PublicationListSerializer(publications, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """Bulk create publications for an object."""
        serializer = PublicationBulkCreateSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        object_type = serializer.validated_data['object_type']
        object_id = serializer.validated_data['object_id']
        platforms_data = serializer.validated_data['platforms']

        created_publications = []
        with transaction.atomic():
            for platform_data in platforms_data:
                # Check for existing publication
                existing = Publication.objects.filter(
                    object_type=object_type,
                    object_id=object_id,
                    platform=platform_data['platform'],
                    territory=platform_data['territory']
                ).first()

                if not existing:
                    publication = Publication.objects.create(
                        object_type=object_type,
                        object_id=object_id,
                        **platform_data
                    )
                    created_publications.append(publication)

        result_serializer = PublicationDetailSerializer(created_publications, many=True)
        return Response(result_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def coverage_report(self, request):
        """Get coverage report for an object."""
        object_type = request.query_params.get('object_type')
        object_id = request.query_params.get('object_id')

        if not object_type or not object_id:
            return Response(
                {'error': 'object_type and object_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get coverage report
        report_data = PublicationReport.get_coverage_report(object_type, object_id)

        # Get object title
        if object_type == 'recording':
            recording = Recording.objects.filter(id=object_id).first()
            object_title = recording.title if recording else f"Recording #{object_id}"
        elif object_type == 'release':
            release = Release.objects.filter(id=object_id).first()
            object_title = release.title if release else f"Release #{object_id}"
        else:
            object_title = f"{object_type} #{object_id}"

        # Get publications
        publications = Publication.objects.filter(
            object_type=object_type,
            object_id=object_id
        )

        response_data = {
            'object_type': object_type,
            'object_id': object_id,
            'object_title': object_title,
            'total_platforms': report_data['total_platforms'],
            'covered_count': report_data['covered_count'],
            'coverage_percentage': report_data['coverage_percentage'],
            'covered_platforms': report_data['covered_platforms'],
            'missing_platforms': report_data['missing_platforms'],
            'publications': PublicationListSerializer(publications, many=True).data,
            'by_territory': report_data.get('by_territory', {}),
            'by_status': report_data.get('by_status', {})
        }

        serializer = CoverageReportSerializer(data=response_data)
        if serializer.is_valid():
            return Response(serializer.data)
        return Response(response_data)

    @action(detail=False, methods=['get'])
    def territory_stats(self, request):
        """Get statistics by territory."""
        territories = Publication.objects.values('territory').annotate(
            publication_count=Count('id'),
            live_count=Count('id', filter=Q(status='live')),
            scheduled_count=Count('id', filter=Q(status='scheduled')),
            taken_down_count=Count('id', filter=Q(status='taken_down')),
            monetized_count=Count('id', filter=Q(is_monetized=True))
        ).order_by('-publication_count')

        stats = []
        for territory_data in territories[:20]:  # Top 20 territories
            territory = territory_data['territory']
            territory_display = territory  # ISO country code or 'GLOBAL'

            # Get platforms for this territory
            platforms = Publication.objects.filter(
                territory=territory
            ).values_list('platform', flat=True).distinct()

            stats.append({
                'territory': territory,
                'territory_display': territory_display,
                'publication_count': territory_data['publication_count'],
                'platforms': list(platforms),
                'live_count': territory_data['live_count'],
                'scheduled_count': territory_data['scheduled_count'],
                'taken_down_count': territory_data['taken_down_count'],
                'monetized_count': territory_data['monetized_count']
            })

        return Response(stats)

    @action(detail=False, methods=['get'])
    def platform_stats(self, request):
        """Get statistics by platform."""
        platforms = Publication.objects.values('platform').annotate(
            publication_count=Count('id'),
            live_count=Count('id', filter=Q(status='live')),
            scheduled_count=Count('id', filter=Q(status='scheduled')),
            taken_down_count=Count('id', filter=Q(status='taken_down')),
            monetized_count=Count('id', filter=Q(is_monetized=True))
        ).order_by('-publication_count')

        stats = []
        for platform_data in platforms:
            platform = platform_data['platform']
            platform_display = dict(Publication.PLATFORM_CHOICES).get(platform, platform)
            platform_icon = Publication._meta.get_field('platform').default  # Get icon

            # Get territories for this platform
            territories = Publication.objects.filter(
                platform=platform
            ).values_list('territory', flat=True).distinct()

            # Calculate total metrics if available
            metrics_agg = Publication.objects.filter(
                platform=platform,
                metrics__isnull=False
            ).aggregate(
                total_views=Sum('metrics__views'),
                total_revenue=Sum('metrics__revenue')
            )

            stat_item = {
                'platform': platform,
                'platform_display': platform_display,
                'platform_icon': '🎵',  # Default icon
                'publication_count': platform_data['publication_count'],
                'territories': list(territories)[:10],  # Top 10 territories
                'live_count': platform_data['live_count'],
                'scheduled_count': platform_data['scheduled_count'],
                'taken_down_count': platform_data['taken_down_count'],
                'monetized_count': platform_data['monetized_count']
            }

            if metrics_agg['total_views']:
                stat_item['total_views'] = metrics_agg['total_views']
            if metrics_agg['total_revenue']:
                stat_item['total_revenue'] = float(metrics_agg['total_revenue'])

            stats.append(stat_item)

        return Response(stats)

    @action(detail=True, methods=['post'])
    def update_metrics(self, request, pk=None):
        """Update metrics for a publication."""
        publication = self.get_object()
        serializer = UpdateMetricsSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Update metrics
        publication.metrics = serializer.validated_data['metrics']
        publication.last_metrics_update = timezone.now()
        publication.save()

        result_serializer = PublicationDetailSerializer(publication)
        return Response(result_serializer.data)

    @action(detail=True, methods=['post'])
    def go_live(self, request, pk=None):
        """Mark publication as live."""
        publication = self.get_object()

        # Parse optional reason
        serializer = PublicationActionSerializer(data={'action': 'go_live', **request.data})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Update status
        publication.status = 'live'
        publication.published_at = timezone.now()
        publication.scheduled_for = None

        # Add note if reason provided
        if serializer.validated_data.get('reason'):
            if publication.notes:
                publication.notes += f"\n\nWent live: {serializer.validated_data['reason']}"
            else:
                publication.notes = f"Went live: {serializer.validated_data['reason']}"

        publication.save()

        result_serializer = PublicationDetailSerializer(publication)
        return Response(result_serializer.data)

    @action(detail=True, methods=['post'])
    def schedule(self, request, pk=None):
        """Schedule publication for future date."""
        publication = self.get_object()
        serializer = PublicationActionSerializer(data={'action': 'schedule', **request.data})

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Update status
        publication.status = 'scheduled'
        publication.scheduled_for = serializer.validated_data['scheduled_for']

        # Add note if reason provided
        if serializer.validated_data.get('reason'):
            if publication.notes:
                publication.notes += f"\n\nScheduled: {serializer.validated_data['reason']}"
            else:
                publication.notes = f"Scheduled: {serializer.validated_data['reason']}"

        publication.save()

        result_serializer = PublicationDetailSerializer(publication)
        return Response(result_serializer.data)

    @action(detail=True, methods=['post'])
    def take_down(self, request, pk=None):
        """Take down publication."""
        publication = self.get_object()

        # Parse optional reason
        serializer = PublicationActionSerializer(data={'action': 'take_down', **request.data})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Update status
        publication.status = 'taken_down'
        publication.taken_down_at = timezone.now()

        # Add note if reason provided
        if serializer.validated_data.get('reason'):
            if publication.notes:
                publication.notes += f"\n\nTaken down: {serializer.validated_data['reason']}"
            else:
                publication.notes = f"Taken down: {serializer.validated_data['reason']}"

        publication.save()

        result_serializer = PublicationDetailSerializer(publication)
        return Response(result_serializer.data)

    @action(detail=False, methods=['get'])
    def live(self, request):
        """Get all live publications."""
        live = self.get_queryset().filter(status='live')

        page = self.paginate_queryset(live)
        if page is not None:
            serializer = PublicationListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = PublicationListSerializer(live, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def scheduled(self, request):
        """Get all scheduled publications."""
        scheduled = self.get_queryset().filter(status='scheduled').order_by('scheduled_for')

        page = self.paginate_queryset(scheduled)
        if page is not None:
            serializer = PublicationListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = PublicationListSerializer(scheduled, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def monetized(self, request):
        """Get all monetized publications."""
        monetized = self.get_queryset().filter(is_monetized=True, status='live')

        page = self.paginate_queryset(monetized)
        if page is not None:
            serializer = PublicationListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = PublicationListSerializer(monetized, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_platform(self, request):
        """Get publications grouped by platform."""
        platform = request.query_params.get('platform')

        if not platform:
            return Response(
                {'error': 'platform is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        publications = self.get_queryset().filter(platform=platform)

        page = self.paginate_queryset(publications)
        if page is not None:
            serializer = PublicationListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = PublicationListSerializer(publications, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_territory(self, request):
        """Get publications grouped by territory."""
        territory = request.query_params.get('territory')

        if not territory:
            return Response(
                {'error': 'territory is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        publications = self.get_queryset().filter(territory=territory)

        page = self.paginate_queryset(publications)
        if page is not None:
            serializer = PublicationListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = PublicationListSerializer(publications, many=True)
        return Response(serializer.data)