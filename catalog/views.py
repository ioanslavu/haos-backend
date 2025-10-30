from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters import rest_framework as django_filters
from django.db.models import Q, Count, Sum, Prefetch, Exists, OuterRef, Value, Subquery
from django.db.models.functions import Coalesce
from django.utils import timezone
from .models import Work, Recording, Release, Track, Asset
from .serializers import (
    WorkListSerializer, WorkDetailSerializer,
    RecordingListSerializer, RecordingDetailSerializer,
    ReleaseListSerializer, ReleaseDetailSerializer, ReleaseCreateUpdateSerializer,
    TrackSerializer, AssetSerializer, AssetUploadSerializer
)
from identity.models import Identifier
from rights.models import Credit, Split
from distribution.models import Publication
from api.permissions import IsNotGuest


class WorkFilter(django_filters.FilterSet):
    """Filter for Work model."""

    language = django_filters.CharFilter(lookup_expr='iexact')
    genre = django_filters.CharFilter(lookup_expr='icontains')
    year_composed = django_filters.NumberFilter()
    year_composed_min = django_filters.NumberFilter(field_name='year_composed', lookup_expr='gte')
    year_composed_max = django_filters.NumberFilter(field_name='year_composed', lookup_expr='lte')
    has_recordings = django_filters.BooleanFilter(method='filter_has_recordings')
    has_complete_splits = django_filters.BooleanFilter(method='filter_has_complete_splits')
    search = django_filters.CharFilter(method='filter_search')

    class Meta:
        model = Work
        fields = ['language', 'genre']

    def filter_has_recordings(self, queryset, name, value):
        """Filter works with/without recordings."""
        if value:
            return queryset.annotate(rec_count=Count('recordings')).filter(rec_count__gt=0)
        else:
            return queryset.annotate(rec_count=Count('recordings')).filter(rec_count=0)

    def filter_has_complete_splits(self, queryset, name, value):
        """Filter works with/without complete splits using DB annotations."""
        from rights.models import Split

        writer_sum_sq = Split.objects.filter(
            scope='work',
            object_id=OuterRef('id'),
            right_type='writer',
        ).values('object_id').annotate(total=Sum('share')).values('total')[:1]

        publisher_sum_sq = Split.objects.filter(
            scope='work',
            object_id=OuterRef('id'),
            right_type='publisher',
        ).values('object_id').annotate(total=Sum('share')).values('total')[:1]

        publisher_exists = Exists(
            Split.objects.filter(scope='work', object_id=OuterRef('id'), right_type='publisher')
        )

        annotated = queryset.annotate(
            writer_total=Coalesce(Subquery(writer_sum_sq), Value(0)),
            publisher_total=Coalesce(Subquery(publisher_sum_sq), Value(0)),
            publisher_exists=publisher_exists,
        )

        # Works are complete when writers sum to 100 and publishers either don't exist or sum to 100
        complete_q = Q(writer_total=100) & (Q(publisher_exists=False) | Q(publisher_total=100))

        if value:
            return annotated.filter(complete_q)
        else:
            return annotated.exclude(complete_q)

    def filter_search(self, queryset, name, value):
        """Search works by title, lyrics, alternate titles, or identifiers (ISWC)."""
        from identity.models import Identifier

        identifier_exists = Exists(
            Identifier.objects.filter(
                owner_type='work',
                owner_id=OuterRef('id'),
                value__icontains=value,
            )
        )

        return queryset.annotate(has_identifier=identifier_exists).filter(
            Q(title__icontains=value)
            | Q(alternate_titles__icontains=value)
            | Q(lyrics__icontains=value)
            | Q(has_identifier=True)
        ).distinct()


class WorkViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Work model.
    Access: All authenticated users except guests can view works.
    """

    queryset = Work.objects.all()
    permission_classes = [IsAuthenticated, IsNotGuest]
    filterset_class = WorkFilter
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    search_fields = ['title', 'alternate_titles', 'lyrics', 'notes']
    ordering_fields = ['title', 'year_composed', 'created_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return WorkListSerializer
        return WorkDetailSerializer

    def get_queryset(self):
        """Optimize queryset with annotations."""
        queryset = super().get_queryset()
        # Annotate recordings count for list and retrieve actions
        if self.action in ['list', 'retrieve']:
            queryset = queryset.annotate(
                recordings_count=Count('recordings', distinct=True)
            )
        return queryset

    @action(detail=True, methods=['post'])
    def add_iswc(self, request, pk=None):
        """Add ISWC identifier to work."""
        work = self.get_object()
        iswc = request.data.get('iswc')

        if not iswc:
            return Response(
                {'error': 'ISWC code is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if ISWC already exists
        if Identifier.objects.filter(
            owner_type='work',
            owner_id=work.id,
            scheme='ISWC'
        ).exists():
            return Response(
                {'error': 'Work already has an ISWC code'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create ISWC identifier
        identifier = Identifier.objects.create(
            scheme='ISWC',
            value=iswc,
            owner_type='work',
            owner_id=work.id
        )

        return Response({
            'success': True,
            'identifier': {
                'scheme': identifier.scheme,
                'value': identifier.value
            }
        })

    @action(detail=True, methods=['get'])
    def credits(self, request, pk=None):
        """Get credits for this work."""
        work = self.get_object()
        credits = Credit.objects.filter(
            scope='work',
            object_id=work.id
        ).select_related('entity')

        from rights.serializers import CreditSerializer
        serializer = CreditSerializer(credits, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def splits(self, request, pk=None):
        """Get splits for this work."""
        work = self.get_object()
        splits = Split.objects.filter(
            scope='work',
            object_id=work.id
        ).select_related('entity')

        from rights.serializers import SplitSerializer
        serializer = SplitSerializer(splits, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def recordings(self, request, pk=None):
        """Get all recordings of this work."""
        work = self.get_object()
        recordings = work.recordings.all()
        serializer = RecordingListSerializer(recordings, many=True)
        return Response(serializer.data)


class RecordingFilter(django_filters.FilterSet):
    """Filter for Recording model."""

    type = django_filters.ChoiceFilter(choices=Recording.TYPE_CHOICES)
    status = django_filters.ChoiceFilter(choices=Recording.STATUS_CHOICES)
    work = django_filters.ModelChoiceFilter(queryset=Work.objects.all())
    has_assets = django_filters.BooleanFilter(method='filter_has_assets')
    has_complete_splits = django_filters.BooleanFilter(method='filter_has_complete_splits')
    recording_date_after = django_filters.DateFilter(field_name='recording_date', lookup_expr='gte')
    recording_date_before = django_filters.DateFilter(field_name='recording_date', lookup_expr='lte')
    search = django_filters.CharFilter(method='filter_search')

    class Meta:
        model = Recording
        fields = ['type', 'status', 'work']

    def filter_has_assets(self, queryset, name, value):
        """Filter recordings with/without assets."""
        if value:
            return queryset.annotate(asset_count=Count('assets')).filter(asset_count__gt=0)
        else:
            return queryset.annotate(asset_count=Count('assets')).filter(asset_count=0)

    def filter_has_complete_splits(self, queryset, name, value):
        """Filter recordings with/without complete splits."""
        if value:
            recording_ids = []
            for recording in queryset:
                if recording.has_complete_master_splits:
                    recording_ids.append(recording.id)
            return queryset.filter(id__in=recording_ids)
        else:
            recording_ids = []
            for recording in queryset:
                if not recording.has_complete_master_splits:
                    recording_ids.append(recording.id)
            return queryset.filter(id__in=recording_ids)

    def filter_search(self, queryset, name, value):
        """Search recordings by title, notes, or ISRC."""
        return queryset.filter(
            Q(title__icontains=value) |
            Q(notes__icontains=value) |
            Q(identifier_set__value__icontains=value)
        ).distinct()


class RecordingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Recording model.
    Access: All authenticated users except guests can view recordings.
    Data shown is filtered by department (campaigns, etc.).
    """

    queryset = Recording.objects.all()
    permission_classes = [IsAuthenticated, IsNotGuest]
    filterset_class = RecordingFilter
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    search_fields = ['title', 'notes', 'studio', 'version']
    ordering_fields = ['title', 'recording_date', 'created_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return RecordingListSerializer
        return RecordingDetailSerializer

    def get_queryset(self):
        """Optimize queryset with prefetch."""
        queryset = super().get_queryset()
        if self.action == 'list':
            queryset = queryset.select_related('work').annotate(
                release_count=Count('tracks__release', distinct=True)
            )
        elif self.action == 'retrieve':
            queryset = queryset.select_related('work', 'derived_from').prefetch_related('assets').annotate(
                release_count=Count('tracks__release', distinct=True)
            )
        else:
            queryset = queryset.select_related('work', 'derived_from').prefetch_related('assets')
        return queryset

    @action(detail=True, methods=['post'])
    def add_isrc(self, request, pk=None):
        """Add ISRC identifier to recording."""
        recording = self.get_object()
        isrc = request.data.get('isrc')

        if not isrc:
            return Response(
                {'error': 'ISRC code is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if ISRC already exists
        if Identifier.objects.filter(
            owner_type='recording',
            owner_id=recording.id,
            scheme='ISRC'
        ).exists():
            return Response(
                {'error': 'Recording already has an ISRC code'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create ISRC identifier
        identifier = Identifier.objects.create(
            scheme='ISRC',
            value=isrc,
            owner_type='recording',
            owner_id=recording.id
        )

        return Response({
            'success': True,
            'identifier': {
                'scheme': identifier.scheme,
                'value': identifier.value
            }
        })

    @action(detail=True, methods=['get'])
    def credits(self, request, pk=None):
        """Get credits for this recording."""
        recording = self.get_object()
        credits = Credit.objects.filter(
            scope='recording',
            object_id=recording.id
        ).select_related('entity')

        from rights.serializers import CreditSerializer
        serializer = CreditSerializer(credits, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def splits(self, request, pk=None):
        """Get splits for this recording."""
        recording = self.get_object()
        splits = Split.objects.filter(
            scope='recording',
            object_id=recording.id
        ).select_related('entity')

        from rights.serializers import SplitSerializer
        serializer = SplitSerializer(splits, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def releases(self, request, pk=None):
        """Get all releases containing this recording."""
        recording = self.get_object()
        releases = Release.objects.filter(
            tracks__recording=recording
        ).distinct()
        serializer = ReleaseListSerializer(releases, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def publications(self, request, pk=None):
        """Get all publications of this recording."""
        recording = self.get_object()
        publications = Publication.objects.filter(
            object_type='recording',
            object_id=recording.id
        )

        from distribution.serializers import PublicationListSerializer
        serializer = PublicationListSerializer(publications, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def relationships(self, request, pk=None):
        """
        Get department-filtered relationships for this recording.
        Shows campaigns filtered by user's department access.

        Access rules:
        - Admins: See all campaigns
        - Managers: See campaigns from their department
        - Employees: See campaigns where they are handlers
        """
        recording = self.get_object()
        profile = request.user.profile

        # Filter campaigns by department/role
        from campaigns.models import Campaign

        if profile.is_admin:
            # Admins see all campaigns
            campaigns = recording.campaigns.all()
        elif profile.is_manager:
            # Managers see campaigns from their department
            campaigns = recording.campaigns.filter(department=profile.department)
        else:
            # Employees see only campaigns they're assigned to
            campaigns = recording.campaigns.filter(
                handlers__user=request.user
            ).distinct()

        # Serialize
        from campaigns.serializers import CampaignListSerializer
        campaign_data = CampaignListSerializer(campaigns, many=True).data

        return Response({
            'recording': {
                'id': recording.id,
                'title': recording.title,
                'type': recording.type,
            },
            'campaigns': campaign_data,
            'campaigns_count': len(campaign_data),
        })


class ReleaseFilter(django_filters.FilterSet):
    """Filter for Release model."""

    type = django_filters.ChoiceFilter(choices=Release.TYPE_CHOICES)
    status = django_filters.ChoiceFilter(choices=Release.STATUS_CHOICES)
    release_date_after = django_filters.DateFilter(field_name='release_date', lookup_expr='gte')
    release_date_before = django_filters.DateFilter(field_name='release_date', lookup_expr='lte')
    label_name = django_filters.CharFilter(lookup_expr='icontains')
    search = django_filters.CharFilter(method='filter_search')

    class Meta:
        model = Release
        fields = ['type', 'status', 'label_name']

    def filter_search(self, queryset, name, value):
        """Search releases by title, catalog number, or UPC."""
        return queryset.filter(
            Q(title__icontains=value) |
            Q(catalog_number__icontains=value) |
            Q(identifier_set__value__icontains=value)
        ).distinct()


class ReleaseViewSet(viewsets.ModelViewSet):
    """ViewSet for Release model."""

    queryset = Release.objects.all()
    permission_classes = [IsAuthenticated]
    filterset_class = ReleaseFilter
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    search_fields = ['title', 'catalog_number', 'label_name', 'description']
    ordering_fields = ['title', 'release_date', 'created_at']
    ordering = ['-release_date', '-created_at']

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return ReleaseListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ReleaseCreateUpdateSerializer
        return ReleaseDetailSerializer

    def get_queryset(self):
        """Optimize queryset with annotations."""
        queryset = super().get_queryset()
        if self.action == 'list':
            queryset = queryset.annotate(
                track_count=Count('tracks', distinct=True)
            )
        elif self.action == 'retrieve':
            queryset = queryset.prefetch_related(
                Prefetch('tracks', queryset=Track.objects.select_related('recording'))
            ).annotate(
                track_count=Count('tracks', distinct=True)
            )
        else:
            queryset = queryset.prefetch_related(
                Prefetch('tracks', queryset=Track.objects.select_related('recording'))
            )
        return queryset

    @action(detail=True, methods=['post'])
    def add_upc(self, request, pk=None):
        """Add UPC identifier to release."""
        release = self.get_object()
        upc = request.data.get('upc')

        if not upc:
            return Response(
                {'error': 'UPC code is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if UPC already exists
        if Identifier.objects.filter(
            owner_type='release',
            owner_id=release.id,
            scheme='UPC'
        ).exists():
            return Response(
                {'error': 'Release already has a UPC code'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create UPC identifier
        identifier = Identifier.objects.create(
            scheme='UPC',
            value=upc,
            owner_type='release',
            owner_id=release.id
        )

        return Response({
            'success': True,
            'identifier': {
                'scheme': identifier.scheme,
                'value': identifier.value
            }
        })

    @action(detail=True, methods=['get'])
    def publications(self, request, pk=None):
        """Get all publications of this release."""
        release = self.get_object()
        publications = Publication.objects.filter(
            object_type='release',
            object_id=release.id
        )

        from distribution.serializers import PublicationListSerializer
        serializer = PublicationListSerializer(publications, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming releases."""
        today = timezone.now().date()
        upcoming = self.get_queryset().filter(
            release_date__gt=today,
            status='scheduled'
        ).order_by('release_date')

        page = self.paginate_queryset(upcoming)
        if page is not None:
            serializer = ReleaseListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = ReleaseListSerializer(upcoming, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent releases."""
        days = int(request.query_params.get('days', 30))
        since = timezone.now().date() - timezone.timedelta(days=days)

        recent = self.get_queryset().filter(
            release_date__gte=since,
            status='released'
        ).order_by('-release_date')

        page = self.paginate_queryset(recent)
        if page is not None:
            serializer = ReleaseListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = ReleaseListSerializer(recent, many=True)
        return Response(serializer.data)


class TrackViewSet(viewsets.ModelViewSet):
    """ViewSet for Track model."""

    queryset = Track.objects.all()
    serializer_class = TrackSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.OrderingFilter
    ]
    filterset_fields = ['release', 'recording', 'disc_number', 'is_bonus', 'is_hidden']
    ordering_fields = ['track_number', 'disc_number']
    ordering = ['disc_number', 'track_number']

    def get_queryset(self):
        """Optimize with select_related."""
        return super().get_queryset().select_related('release', 'recording')


class AssetViewSet(viewsets.ModelViewSet):
    """ViewSet for Asset model."""

    queryset = Asset.objects.all()
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    filterset_fields = ['recording', 'kind', 'is_master', 'is_public']
    search_fields = ['file_name', 'notes']
    ordering_fields = ['created_at', 'file_size']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return AssetUploadSerializer
        return AssetSerializer

    def get_queryset(self):
        """Optimize with select_related."""
        return super().get_queryset().select_related('recording', 'uploaded_by')

    @action(detail=False, methods=['get'])
    def masters(self, request):
        """Get all master assets."""
        masters = self.get_queryset().filter(is_master=True)
        page = self.paginate_queryset(masters)
        if page is not None:
            serializer = AssetSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = AssetSerializer(masters, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def public(self, request):
        """Get all public assets."""
        public = self.get_queryset().filter(is_public=True)
        page = self.paginate_queryset(public)
        if page is not None:
            serializer = AssetSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = AssetSerializer(public, many=True)
        return Response(serializer.data)
