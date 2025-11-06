from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters import rest_framework as django_filters
from django.db.models import Q, Count, Sum, Prefetch, Exists, OuterRef, Value, Subquery
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.db import transaction
from .models import (
    Work, Recording, Release, Track, Asset,
    Song, SongChecklistItem, SongStageTransition, SongAsset, SongNote, SongAlert
)
from .serializers import (
    WorkListSerializer, WorkDetailSerializer,
    RecordingListSerializer, RecordingDetailSerializer,
    ReleaseListSerializer, ReleaseDetailSerializer, ReleaseCreateUpdateSerializer,
    TrackSerializer, AssetSerializer, AssetUploadSerializer,
    SongListSerializer, SongDetailSerializer, SongCreateUpdateSerializer,
    SongChecklistItemSerializer, SongStageTransitionSerializer,
    SongAssetSerializer, SongNoteSerializer, SongAlertSerializer
)
from . import permissions as song_permissions
from . import validators
from . import checklist_templates
from .alert_service import SongAlertService
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
                assignments__user=request.user
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


# ============================================================================
# SONG WORKFLOW VIEWSETS
# ============================================================================


class SongFilter(django_filters.FilterSet):
    """Filter for Song model."""

    stage = django_filters.MultipleChoiceFilter(
        choices=[
            ('draft', 'Draft'),
            ('publishing', 'Publishing'),
            ('label_recording', 'Label - Recording'),
            ('marketing_assets', 'Marketing - Assets'),
            ('label_review', 'Label - Review'),
            ('ready_for_digital', 'Ready for Digital'),
            ('digital_distribution', 'Digital Distribution'),
            ('released', 'Released'),
            ('archived', 'Archived'),
        ]
    )
    priority = django_filters.ChoiceFilter(
        choices=Song.PRIORITY_CHOICES
    )
    assigned_department = django_filters.ModelChoiceFilter(
        queryset=None  # Set in __init__
    )
    assigned_user = django_filters.ModelChoiceFilter(
        queryset=None  # Set in __init__
    )
    is_overdue = django_filters.BooleanFilter()
    is_archived = django_filters.BooleanFilter()
    is_blocked = django_filters.BooleanFilter()
    target_release_date_after = django_filters.DateFilter(
        field_name='target_release_date',
        lookup_expr='gte'
    )
    target_release_date_before = django_filters.DateFilter(
        field_name='target_release_date',
        lookup_expr='lte'
    )
    search = django_filters.CharFilter(method='filter_search')

    class Meta:
        model = Song
        fields = ['stage', 'priority', 'assigned_department', 'assigned_user',
                  'is_overdue', 'is_archived', 'is_blocked']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from api.models import Department
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.filters['assigned_department'].queryset = Department.objects.all()
        self.filters['assigned_user'].queryset = User.objects.all()

    def filter_search(self, queryset, name, value):
        """Search songs by title or artist name."""
        return queryset.filter(
            Q(title__icontains=value) |
            Q(artist__name__icontains=value) |
            Q(internal_notes__icontains=value)
        ).distinct()


class SongViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Song workflow.

    Permissions are filtered by department and user role.
    Users only see songs they have permission to view.
    """

    queryset = Song.objects.all()
    permission_classes = [IsAuthenticated, IsNotGuest]
    filterset_class = SongFilter
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    search_fields = ['title', 'internal_notes', 'external_notes']
    ordering_fields = ['title', 'created_at', 'target_release_date', 'priority', 'checklist_progress']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return SongListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return SongCreateUpdateSerializer
        return SongDetailSerializer

    def get_queryset(self):
        """Filter songs based on user permissions."""
        queryset = super().get_queryset()
        user = self.request.user

        # Filter by permission (only show songs user can view)
        if hasattr(user, 'profile'):
            # Admin sees all
            if user.profile.role.level >= 1000:
                pass  # No filtering
            else:
                # Filter by visible stages
                visible_stages = song_permissions.get_visible_stages_for_user(user)
                queryset = queryset.filter(stage__in=visible_stages)

        # Optimize with select_related
        queryset = queryset.select_related(
            'artist', 'assigned_department', 'assigned_user',
            'created_by', 'work', 'stage_updated_by'
        )

        return queryset

    def perform_create(self, serializer):
        """Set created_by when creating song."""
        serializer.save(created_by=self.request.user)

    def create(self, request, *args, **kwargs):
        """Create song and return full detail response."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        # Return detailed response
        instance = serializer.instance
        detail_serializer = SongDetailSerializer(instance, context={'request': request})
        headers = self.get_success_headers(detail_serializer.data)
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=['post'])
    def transition(self, request, pk=None):
        """
        Transition song to new stage.

        POST /songs/{id}/transition/
        {
            "target_stage": "publishing",
            "notes": "Ready for publishing department",
            "transition_type": "forward"  # optional
        }
        """
        song = self.get_object()
        target_stage = request.data.get('target_stage')
        notes = request.data.get('notes', '')
        transition_type = request.data.get('transition_type', 'forward')

        if not target_stage:
            return Response(
                {'error': 'target_stage is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check permission
        can_transition, error_msg = song_permissions.user_can_transition_stage(
            request.user, song, target_stage
        )

        if not can_transition:
            return Response(
                {'error': error_msg},
                status=status.HTTP_403_FORBIDDEN
            )

        # Perform transition
        with transaction.atomic():
            # Record current state
            from_stage = song.stage
            checklist_completion = song.calculate_checklist_progress()

            # Create transition record
            SongStageTransition.objects.create(
                song=song,
                from_stage=from_stage,
                to_stage=target_stage,
                transitioned_by=request.user,
                transition_type=transition_type,
                notes=notes,
                checklist_completion_at_transition=checklist_completion
            )

            # Update song
            song.stage = target_stage
            song.stage_entered_at = timezone.now()
            song.stage_updated_by = request.user

            # Assign to department for new stage
            target_dept_code = song_permissions.get_department_for_stage(target_stage)
            if target_dept_code:
                from api.models import Department
                try:
                    target_dept = Department.objects.get(code=target_dept_code)
                    song.assigned_department = target_dept
                except Department.DoesNotExist:
                    pass

            song.save()

            # Generate new checklist for target stage
            checklist_items_data = checklist_templates.generate_checklist_for_stage(song, target_stage)
            for item_data in checklist_items_data:
                SongChecklistItem.objects.create(**item_data)

            # Update computed fields
            song.update_computed_fields()

            # Create alert for target department
            SongAlertService.create_stage_transition_alert(song, from_stage, target_stage, request.user)

        # Return updated song
        serializer = SongDetailSerializer(song, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def send_to_marketing(self, request, pk=None):
        """
        Special action: Send from LABEL_RECORDING to MARKETING_ASSETS.

        POST /songs/{id}/send_to_marketing/
        """
        song = self.get_object()

        if song.stage != 'label_recording':
            return Response(
                {'error': 'Song must be in label_recording stage'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Use transition action
        return self.transition(request, pk)

    @action(detail=True, methods=['post'])
    def send_to_digital(self, request, pk=None):
        """
        Special action: Send from READY_FOR_DIGITAL to DIGITAL_DISTRIBUTION.

        Creates urgent alert for Digital department.

        POST /songs/{id}/send_to_digital/
        """
        song = self.get_object()

        if song.stage != 'ready_for_digital':
            return Response(
                {'error': 'Song must be in ready_for_digital stage'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create special alert
        SongAlertService.create_send_to_digital_alert(song, request.user)

        # Use transition action
        return self.transition(request, pk)

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """
        Archive a song.

        POST /songs/{id}/archive/
        """
        song = self.get_object()

        # Check permission
        if not song_permissions.user_can_edit_song(request.user, song):
            return Response(
                {'error': 'You do not have permission to archive this song'},
                status=status.HTTP_403_FORBIDDEN
            )

        song.is_archived = True
        song.stage = 'archived'
        song.save()

        return Response({'success': True, 'message': 'Song archived'})

    @action(detail=True, methods=['post'])
    def unarchive(self, request, pk=None):
        """
        Unarchive a song (admin only).

        POST /songs/{id}/unarchive/
        {
            "restore_to_stage": "draft"
        }
        """
        song = self.get_object()

        # Admin only
        if not hasattr(request.user, 'profile') or request.user.profile.role.level < 1000:
            return Response(
                {'error': 'Only admins can unarchive songs'},
                status=status.HTTP_403_FORBIDDEN
            )

        restore_to_stage = request.data.get('restore_to_stage', 'draft')

        song.is_archived = False
        song.stage = restore_to_stage
        song.stage_entered_at = timezone.now()
        song.save()

        return Response({'success': True, 'message': 'Song unarchived'})

    @action(detail=False, methods=['get'])
    def my_queue(self, request):
        """
        Get songs in user's department queue.

        GET /songs/my_queue/
        """
        user = request.user

        if not hasattr(user, 'profile') or not user.profile.department:
            return Response([])

        # Get stages this department is responsible for
        dept_code = user.profile.department.code.lower()
        dept_stages = []

        # Map departments to their stages
        stage_map = {
            'publishing': ['draft', 'publishing'],
            'label': ['label_recording', 'label_review', 'ready_for_digital'],
            'marketing': ['marketing_assets'],
            'digital': ['digital_distribution', 'released']
        }

        dept_stages = stage_map.get(dept_code, [])

        # Filter songs
        songs = self.get_queryset().filter(
            stage__in=dept_stages,
            is_archived=False
        ).order_by('priority', 'target_release_date')

        # Paginate
        page = self.paginate_queryset(songs)
        if page is not None:
            serializer = SongListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = SongListSerializer(songs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """
        Get overdue songs (manager only).

        GET /songs/overdue/
        """
        user = request.user

        # Manager or admin only
        if not hasattr(user, 'profile') or user.profile.role.level < 300:
            return Response(
                {'error': 'Only managers and admins can view overdue songs'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Filter overdue songs
        songs = self.get_queryset().filter(
            is_overdue=True,
            is_archived=False
        ).order_by('stage_deadline')

        # Paginate
        page = self.paginate_queryset(songs)
        if page is not None:
            serializer = SongListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = SongListSerializer(songs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get department statistics.

        GET /songs/stats/
        """
        user = request.user

        if not hasattr(user, 'profile') or not user.profile.department:
            return Response({'error': 'No department assigned'}, status=status.HTTP_400_BAD_REQUEST)

        dept_code = user.profile.department.code.lower()

        # Map departments to their stages
        stage_map = {
            'publishing': ['draft', 'publishing'],
            'label': ['label_recording', 'label_review', 'ready_for_digital'],
            'marketing': ['marketing_assets'],
            'digital': ['digital_distribution']
        }

        dept_stages = stage_map.get(dept_code, [])

        # Calculate stats
        songs_in_dept = Song.objects.filter(stage__in=dept_stages, is_archived=False)

        stats = {
            'total_songs': songs_in_dept.count(),
            'overdue_songs': songs_in_dept.filter(is_overdue=True).count(),
            'blocked_songs': songs_in_dept.filter(is_blocked=True).count(),
            'by_stage': {},
            'by_priority': {}
        }

        # Count by stage
        for stage_code, stage_display in Song._meta.get_field('stage').choices:
            if stage_code in dept_stages:
                count = songs_in_dept.filter(stage=stage_code).count()
                stats['by_stage'][stage_code] = {
                    'count': count,
                    'display': stage_display
                }

        # Count by priority
        for priority_code, priority_display in Song.PRIORITY_CHOICES:
            count = songs_in_dept.filter(priority=priority_code).count()
            stats['by_priority'][priority_code] = {
                'count': count,
                'display': priority_display
            }

        return Response(stats)

    @action(detail=True, methods=['get'])
    def recordings(self, request, pk=None):
        """
        Get all recordings linked to this song.

        GET /songs/{id}/recordings/

        Returns:
        - Full recording details with credits and splits (filtered by department)
        - Assets (master audio, instrumental)
        """
        song = self.get_object()
        user = request.user

        # Get all recordings linked to this song (M2M relationship)
        recordings = song.recordings.all().select_related('work').prefetch_related('assets')

        # Serialize recordings
        serialized_recordings = []

        for recording in recordings:
            # Base recording data
            recording_data = RecordingDetailSerializer(recording).data

            # Add credits (filtered by department)
            credits = Credit.objects.filter(
                scope='recording',
                object_id=recording.id
            ).select_related('entity')

            from rights.serializers import CreditSerializer

            # Department-based filtering
            if hasattr(user, 'profile') and user.profile.department:
                dept_code = user.profile.department.code.lower()

                # Marketing sees limited info (no financial details)
                if dept_code == 'marketing':
                    recording_data['credits'] = [
                        {'entity_name': c.entity.name if c.entity else 'Unknown', 'role': c.role}
                        for c in credits
                    ]
                    recording_data['splits'] = None  # Marketing doesn't see splits

                # Digital sees names only (no splits)
                elif dept_code == 'digital':
                    recording_data['credits'] = CreditSerializer(credits, many=True).data
                    recording_data['splits'] = None  # Digital doesn't see splits

                # Label sees everything
                elif dept_code == 'label':
                    recording_data['credits'] = CreditSerializer(credits, many=True).data

                    # Add master splits
                    splits = Split.objects.filter(
                        scope='recording',
                        object_id=recording.id,
                        right_type='master'
                    ).select_related('entity')

                    from rights.serializers import SplitSerializer
                    recording_data['splits'] = SplitSerializer(splits, many=True).data

                # Sales, Publishing see basic info
                else:
                    recording_data['credits'] = [
                        {'entity_name': c.entity.name if c.entity else 'Unknown', 'role': c.role}
                        for c in credits
                    ]
                    recording_data['splits'] = None
            else:
                # No department - show basic info
                recording_data['credits'] = [
                    {'entity_name': c.entity.name if c.entity else 'Unknown', 'role': c.role}
                    for c in credits
                ]
                recording_data['splits'] = None

            serialized_recordings.append(recording_data)

        return Response(serialized_recordings)

    @action(detail=True, methods=['post'], url_path='link_recording')
    def link_recording(self, request, pk=None):
        """
        Link an existing recording to this song.

        POST /songs/{id}/link_recording/
        Body: {"recording_id": 123}

        Permissions:
        - Label department users when song is in 'label_recording' stage
        - Administrators
        """
        song = self.get_object()
        user = request.user

        # Check permissions
        is_admin = user.is_superuser or (
            hasattr(user, 'profile') and
            user.profile.role and
            user.profile.role.name == 'Administrator'
        )
        is_label_in_stage = (
            hasattr(user, 'profile') and
            user.profile.department and
            user.profile.department.code == 'Label' and
            song.stage == 'label_recording'
        )

        if not (is_admin or is_label_in_stage):
            return Response(
                {'error': 'You do not have permission to link recordings to this song'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get recording_id from request
        recording_id = request.data.get('recording_id')
        if not recording_id:
            return Response(
                {'error': 'recording_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            recording = Recording.objects.get(id=recording_id)
        except Recording.DoesNotExist:
            return Response(
                {'error': f'Recording with id {recording_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Link recording to song (M2M relationship)
        if recording in song.recordings.all():
            return Response(
                {'message': 'Recording is already linked to this song'},
                status=status.HTTP_200_OK
            )

        song.recordings.add(recording)

        # If this is the first recording and work exists, auto-link work to recording
        if recording.work is None and song.work:
            recording.work = song.work
            recording.save()

        return Response(
            {
                'message': 'Recording linked successfully',
                'recording_id': recording.id,
                'recording_title': recording.title
            },
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['get'])
    def work(self, request, pk=None):
        """
        Get work details for this song.

        GET /songs/{id}/work/

        Returns:
        - Work details with splits (filtered by department permissions)
        - Writer splits (if user has permission)
        - Publisher splits (if user has permission)
        """
        song = self.get_object()
        user = request.user

        # Check if work exists
        if not song.work:
            return Response(
                {'error': 'No work linked to this song'},
                status=status.HTTP_404_NOT_FOUND
            )

        work = song.work

        # Base work data
        work_data = WorkDetailSerializer(work).data

        # Get department code
        dept_code = None
        if hasattr(user, 'profile') and user.profile.department:
            dept_code = user.profile.department.code.lower()

        # Department-based filtering for splits
        # Sales: Can see splits (need to know value for pitching)
        # Publishing: Can see everything
        # Label: Can see splits
        # Marketing: CANNOT see splits
        # Digital: Can see names only, no split percentages

        from rights.serializers import SplitSerializer

        # Marketing department CANNOT see splits
        if dept_code == 'marketing':
            work_data['writer_splits'] = None
            work_data['publisher_splits'] = None
            work_data['can_view_splits'] = False

        # Digital can see names but not percentages
        elif dept_code == 'digital':
            writer_splits = Split.objects.filter(
                scope='work',
                object_id=work.id,
                right_type='writer'
            ).select_related('entity')

            publisher_splits = Split.objects.filter(
                scope='work',
                object_id=work.id,
                right_type='publisher'
            ).select_related('entity')

            # Return names only
            work_data['writer_splits'] = [
                {'entity_name': s.entity.display_name if s.entity else 'Unknown', 'role': 'Writer'}
                for s in writer_splits
            ]
            work_data['publisher_splits'] = [
                {'entity_name': s.entity.display_name if s.entity else 'Unknown', 'role': 'Publisher'}
                for s in publisher_splits
            ]
            work_data['can_view_splits'] = False

        # Publishing, Label, Sales can see full splits
        else:
            writer_splits = Split.objects.filter(
                scope='work',
                object_id=work.id,
                right_type='writer'
            ).select_related('entity')

            publisher_splits = Split.objects.filter(
                scope='work',
                object_id=work.id,
                right_type='publisher'
            ).select_related('entity')

            work_data['writer_splits'] = SplitSerializer(writer_splits, many=True).data
            work_data['publisher_splits'] = SplitSerializer(publisher_splits, many=True).data
            work_data['can_view_splits'] = True

        # Add permission flags
        work_data['can_edit'] = (
            dept_code == 'publishing' and
            song.stage in ['draft', 'publishing']
        )

        return Response(work_data)

    @action(detail=True, methods=['get'])
    def contracts(self, request, pk=None):
        """
        Get all contracts related to this song.
        
        Returns contracts linked via ContractScope to:
        - The song's work
        - The song's recordings
        - The song's release
        
        GET /songs/{id}/contracts/
        """
        from contracts.models import Contract, ContractScope
        from contracts.serializers import ContractSerializer
        
        song = self.get_object()
        
        # Build query for contracts related to this song
        contract_ids = set()
        
        # Contracts linked to the song's work
        if song.work:
            work_scopes = ContractScope.objects.filter(work=song.work).values_list('contract_id', flat=True)
            contract_ids.update(work_scopes)
        
        # Contracts linked to the song's recordings
        recording_scopes = ContractScope.objects.filter(
            recording__song=song
        ).values_list('contract_id', flat=True)
        contract_ids.update(recording_scopes)
        
        # Contracts linked to the song's release
        if hasattr(song, 'release') and song.release:
            release_scopes = ContractScope.objects.filter(release=song.release).values_list('contract_id', flat=True)
            contract_ids.update(release_scopes)
        
        # Fetch all contracts with related data
        contracts = Contract.objects.filter(
            id__in=contract_ids
        ).select_related(
            'template',
            'counterparty_entity',
            'label_entity',
            'department',
            'created_by'
        ).prefetch_related(
            'signatures',
            'scopes',
            'scopes__work',
            'scopes__recording',
            'scopes__release'
        ).order_by('-created_at')
        
        # Serialize contracts
        serializer = ContractSerializer(contracts, many=True, context={'request': request})

        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def transitions(self, request, pk=None):
        """
        Get all stage transitions for this song.

        GET /songs/{id}/transitions/

        Returns:
        - List of all stage transitions with user info and timestamps
        """
        song = self.get_object()

        # Get all transitions for this song
        transitions = SongStageTransition.objects.filter(
            song=song
        ).select_related('transitioned_by').order_by('-transitioned_at')

        # Serialize transitions
        serializer = SongStageTransitionSerializer(transitions, many=True)

        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def link_release(self, request, pk=None):
        """
        Link a release to this song.

        POST /songs/{id}/link-release/
        {
            "release_id": 123
        }
        """
        song = self.get_object()
        release_id = request.data.get('release_id')

        if not release_id:
            return Response(
                {'error': 'release_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if release exists
        try:
            release = Release.objects.get(id=release_id)
        except Release.DoesNotExist:
            return Response(
                {'error': 'Release not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Link release to song (M2M)
        song.releases.add(release)

        return Response({
            'success': True,
            'message': f'Release "{release.title}" linked to song "{song.title}"',
            'release_id': release.id
        })


class SongChecklistViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Song Checklist Items (nested under Song).

    GET /songs/{song_id}/checklist/
    """

    queryset = SongChecklistItem.objects.all()
    serializer_class = SongChecklistItemSerializer
    permission_classes = [IsAuthenticated, IsNotGuest]

    def get_queryset(self):
        """Filter by song from URL."""
        song_id = self.kwargs.get('song_pk')
        if song_id:
            return self.queryset.filter(song_id=song_id).order_by('order', 'id')
        return self.queryset.none()

    @action(detail=True, methods=['post'])
    def toggle(self, request, song_pk=None, pk=None):
        """
        Toggle manual checklist item completion.

        POST /songs/{song_id}/checklist/{item_id}/toggle/
        """
        item = self.get_object()

        # Only manual items can be toggled
        if item.validation_type != 'manual':
            return Response(
                {'error': 'Only manual checklist items can be toggled'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check permission
        if not song_permissions.user_can_edit_song(request.user, item.song):
            return Response(
                {'error': 'You do not have permission to edit this checklist'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Toggle completion
        item.is_complete = not item.is_complete

        if item.is_complete:
            item.completed_by = request.user
            item.completed_at = timezone.now()
        else:
            item.completed_by = None
            item.completed_at = None

        item.save()

        # Update song's computed fields
        item.song.update_computed_fields()

        serializer = SongChecklistItemSerializer(item)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def validate_all(self, request, song_pk=None):
        """
        Run all auto-validators for current stage.

        POST /songs/{song_id}/checklist/validate_all/
        """
        song = Song.objects.get(pk=song_pk)

        # Run validation
        result = validators.revalidate_song_checklist(song)

        return Response(result)

    @action(detail=True, methods=['post'])
    def assign(self, request, song_pk=None, pk=None):
        """
        Assign checklist item to user.

        POST /songs/{song_id}/checklist/{item_id}/assign/
        {
            "user_id": 123
        }
        """
        item = self.get_object()

        # Check permission (manager or admin only)
        if not hasattr(request.user, 'profile') or request.user.profile.role.level < 300:
            return Response(
                {'error': 'Only managers can assign checklist items'},
                status=status.HTTP_403_FORBIDDEN
            )

        user_id = request.data.get('user_id')
        if not user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from django.contrib.auth import get_user_model
        User = get_user_model()

        try:
            user = User.objects.get(pk=user_id)
            item.assigned_to = user
            item.save()

            serializer = SongChecklistItemSerializer(item)
            return Response(serializer.data)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class SongAssetViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Song Assets (nested under Song).

    Marketing assets submitted by Marketing dept, reviewed by Label dept.
    """

    queryset = SongAsset.objects.all()
    serializer_class = SongAssetSerializer
    permission_classes = [IsAuthenticated, IsNotGuest]

    def get_queryset(self):
        """Filter by song from URL."""
        song_id = self.kwargs.get('song_pk')
        if song_id:
            return self.queryset.filter(song_id=song_id).order_by('-uploaded_at')
        return self.queryset.none()

    def perform_create(self, serializer):
        """Set uploaded_by when creating asset."""
        song_id = self.kwargs.get('song_pk')
        song = Song.objects.get(pk=song_id)

        serializer.save(
            uploaded_by=self.request.user,
            song=song
        )

        # Create alert for Label department
        SongAlertService.create_asset_submitted_alert(song, self.request.user)

    @action(detail=True, methods=['post'])
    def review(self, request, song_pk=None, pk=None):
        """
        Review asset (Label department only).

        POST /songs/{song_id}/assets/{asset_id}/review/
        {
            "action": "approved" | "rejected" | "revision_requested",
            "notes": "Feedback text"
        }
        """
        asset = self.get_object()

        # Label department only
        if not hasattr(request.user, 'profile') or not request.user.profile.department:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        if request.user.profile.department.code.lower() != 'label':
            return Response(
                {'error': 'Only Label department can review assets'},
                status=status.HTTP_403_FORBIDDEN
            )

        action = request.data.get('action')
        notes = request.data.get('notes', '')

        if action not in ['approved', 'rejected', 'revision_requested']:
            return Response(
                {'error': 'Invalid action. Must be: approved, rejected, or revision_requested'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update asset
        asset.review_status = action
        asset.reviewed_by = request.user
        asset.reviewed_at = timezone.now()
        asset.review_notes = notes
        asset.save()

        # Create alert for Marketing department
        SongAlertService.create_asset_reviewed_alert(
            asset.song, asset, action, request.user
        )

        serializer = SongAssetSerializer(asset)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def set_primary(self, request, song_pk=None, pk=None):
        """
        Set asset as primary for its type.

        POST /songs/{song_id}/assets/{asset_id}/set_primary/
        """
        asset = self.get_object()

        # Check permission
        if not song_permissions.user_can_edit_song(request.user, asset.song):
            return Response(
                {'error': 'You do not have permission to edit this song'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Unset other primary assets of same type
        SongAsset.objects.filter(
            song=asset.song,
            asset_type=asset.asset_type,
            is_primary=True
        ).update(is_primary=False)

        # Set this as primary
        asset.is_primary = True
        asset.save()

        serializer = SongAssetSerializer(asset)
        return Response(serializer.data)


class SongNoteViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Song Notes (nested under Song).

    Activity log and sales pitch tracking.
    """

    queryset = SongNote.objects.all()
    serializer_class = SongNoteSerializer
    permission_classes = [IsAuthenticated, IsNotGuest]

    def get_queryset(self):
        """Filter by song and department visibility."""
        song_id = self.kwargs.get('song_pk')
        if not song_id:
            return self.queryset.none()

        queryset = self.queryset.filter(song_id=song_id).order_by('-created_at')

        # Filter by department visibility
        user = self.request.user
        if hasattr(user, 'profile') and user.profile.department:
            # Show notes visible to user's department or notes with no department restriction
            queryset = queryset.filter(
                Q(visible_to_departments=user.profile.department) |
                Q(visible_to_departments__isnull=True)
            ).distinct()

        return queryset

    def perform_create(self, serializer):
        """Set author when creating note."""
        song_id = self.kwargs.get('song_pk')
        song = Song.objects.get(pk=song_id)

        note = serializer.save(
            author=self.request.user,
            song=song
        )

        # If this is a sales pitch, create alert
        if note.note_type == 'sales_pitch' and note.pitched_to_artist:
            SongAlertService.create_sales_pitch_alert(
                song, self.request.user, note.pitched_to_artist
            )


class SongAlertViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Song Alerts.

    In-app notifications for song workflow events.
    """

    queryset = SongAlert.objects.all()
    serializer_class = SongAlertSerializer
    permission_classes = [IsAuthenticated, IsNotGuest]

    def get_queryset(self):
        """Filter alerts for current user."""
        user = self.request.user
        queryset = self.queryset

        # Filter by target user or target department
        if hasattr(user, 'profile') and user.profile.department:
            queryset = queryset.filter(
                Q(target_user=user) |
                Q(target_department=user.profile.department)
            ).order_by('-created_at')
        else:
            queryset = queryset.filter(target_user=user).order_by('-created_at')

        return queryset

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """
        Mark alert as read.

        POST /alerts/{id}/mark_read/
        """
        alert = self.get_object()

        if not alert.is_read:
            alert.is_read = True
            alert.read_at = timezone.now()
            alert.save()

        serializer = SongAlertSerializer(alert)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """
        Mark all user's alerts as read.

        POST /alerts/mark_all_read/
        """
        updated = self.get_queryset().filter(is_read=False).update(
            is_read=True,
            read_at=timezone.now()
        )

        return Response({'success': True, 'updated': updated})

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """
        Get count of unread alerts.

        GET /alerts/unread_count/
        """
        count = self.get_queryset().filter(is_read=False).count()

        return Response({'unread_count': count})
