from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters import rest_framework as django_filters
from django.db.models import Q, Sum, Count
from django.db import transaction
from decimal import Decimal
from .models import Credit, Split, SplitValidation
from .serializers import (
    CreditSerializer, SplitSerializer, SplitValidationSerializer,
    SplitBulkCreateSerializer, AutoCalculateSplitsSerializer,
    CreditBulkCreateSerializer, RightsValidationReportSerializer
)
from identity.models import Entity
from catalog.models import Work, Recording


class CreditFilter(django_filters.FilterSet):
    """Filter for Credit model."""

    scope = django_filters.ChoiceFilter(choices=Credit.SCOPE_CHOICES)
    role = django_filters.ChoiceFilter(choices=Credit.ALL_ROLE_CHOICES)
    entity = django_filters.ModelChoiceFilter(queryset=Entity.objects.all())
    share_kind = django_filters.ChoiceFilter(choices=Credit.SHARE_KIND_CHOICES)
    search = django_filters.CharFilter(method='filter_search')

    class Meta:
        model = Credit
        fields = ['scope', 'role', 'entity', 'share_kind']

    def filter_search(self, queryset, name, value):
        """Search credits by entity name or credited_as."""
        return queryset.filter(
            Q(entity__display_name__icontains=value) |
            Q(credited_as__icontains=value) |
            Q(notes__icontains=value)
        )


class CreditViewSet(viewsets.ModelViewSet):
    """ViewSet for Credit model."""

    queryset = Credit.objects.all()
    serializer_class = CreditSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = CreditFilter
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    search_fields = ['entity__display_name', 'credited_as', 'notes']
    ordering_fields = ['created_at', 'entity__display_name']
    ordering = ['-created_at']

    def get_queryset(self):
        """Optimize with select_related."""
        return super().get_queryset().select_related('entity')

    @action(detail=False, methods=['get'])
    def by_object(self, request):
        """Get credits for a specific object."""
        scope = request.query_params.get('scope')
        object_id = request.query_params.get('object_id')

        if not scope or not object_id:
            return Response(
                {'error': 'scope and object_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        credits = self.get_queryset().filter(
            scope=scope,
            object_id=object_id
        )
        serializer = self.get_serializer(credits, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_entity(self, request):
        """Get all credits for a specific entity."""
        entity_id = request.query_params.get('entity_id')

        if not entity_id:
            return Response(
                {'error': 'entity_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        credits = self.get_queryset().filter(entity_id=entity_id)
        page = self.paginate_queryset(credits)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(credits, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """Bulk create credits for an object."""
        serializer = CreditBulkCreateSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        scope = serializer.validated_data['scope']
        object_id = serializer.validated_data['object_id']
        credits_data = serializer.validated_data['credits']

        created_credits = []
        with transaction.atomic():
            for credit_data in credits_data:
                entity_id = credit_data.pop('entity_id')
                credit = Credit.objects.create(
                    scope=scope,
                    object_id=object_id,
                    entity_id=entity_id,
                    **credit_data
                )
                created_credits.append(credit)

        result_serializer = CreditSerializer(created_credits, many=True)
        return Response(result_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def writers(self, request):
        """Get all writer credits."""
        writers = self.get_queryset().filter(
            Q(role='writer') | Q(role='composer') | Q(role='lyricist')
        ).distinct()
        page = self.paginate_queryset(writers)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(writers, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def performers(self, request):
        """Get all performer credits."""
        performers = self.get_queryset().filter(
            Q(role='artist') | Q(role='featured_artist') | Q(role='performer')
        ).distinct()
        page = self.paginate_queryset(performers)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(performers, many=True)
        return Response(serializer.data)


class SplitFilter(django_filters.FilterSet):
    """Filter for Split model."""

    scope = django_filters.ChoiceFilter(choices=Split.SCOPE_CHOICES)
    right_type = django_filters.ChoiceFilter(choices=Split.RIGHT_TYPE_CHOICES)
    entity = django_filters.ModelChoiceFilter(queryset=Entity.objects.all())
    is_locked = django_filters.BooleanFilter()
    search = django_filters.CharFilter(method='filter_search')

    class Meta:
        model = Split
        fields = ['scope', 'right_type', 'entity', 'is_locked']

    def filter_search(self, queryset, name, value):
        """Search splits by entity name or source."""
        return queryset.filter(
            Q(entity__display_name__icontains=value) |
            Q(source__icontains=value) |
            Q(notes__icontains=value)
        )


class SplitViewSet(viewsets.ModelViewSet):
    """ViewSet for Split model."""

    queryset = Split.objects.all()
    serializer_class = SplitSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = SplitFilter
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    search_fields = ['entity__display_name', 'source', 'notes']
    ordering_fields = ['share', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        """Optimize with select_related."""
        return super().get_queryset().select_related('entity')

    @action(detail=False, methods=['get'])
    def by_object(self, request):
        """Get splits for a specific object."""
        scope = request.query_params.get('scope')
        object_id = request.query_params.get('object_id')
        right_type = request.query_params.get('right_type')

        if not scope or not object_id:
            return Response(
                {'error': 'scope and object_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        queryset = self.get_queryset().filter(
            scope=scope,
            object_id=object_id
        )

        if right_type:
            queryset = queryset.filter(right_type=right_type)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def validate(self, request):
        """Validate splits for an object."""
        scope = request.query_params.get('scope')
        object_id = request.query_params.get('object_id')
        right_type = request.query_params.get('right_type')

        if not scope or not object_id or not right_type:
            return Response(
                {'error': 'scope, object_id, and right_type are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        validation = Split.validate_splits_total(scope, object_id, right_type)

        # Add object title
        if scope == 'work':
            work = Work.objects.filter(id=object_id).first()
            object_title = work.title if work else f"Work #{object_id}"
        elif scope == 'recording':
            recording = Recording.objects.filter(id=object_id).first()
            object_title = recording.title if recording else f"Recording #{object_id}"
        else:
            object_title = f"{scope} #{object_id}"

        response_data = {
            'scope': scope,
            'object_id': object_id,
            'object_title': object_title,
            'right_type': right_type,
            'right_type_display': dict(Split.RIGHT_TYPE_CHOICES).get(right_type, right_type),
            'total': float(validation['total']),
            'is_complete': validation['is_complete'],
            'missing': float(validation['missing']),
            'splits': validation['splits']
        }

        serializer = SplitValidationSerializer(data=response_data)
        if serializer.is_valid():
            return Response(serializer.data)
        return Response(response_data)  # Return raw data if serializer fails

    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """Bulk create splits for an object."""
        serializer = SplitBulkCreateSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        scope = serializer.validated_data['scope']
        object_id = serializer.validated_data['object_id']
        right_type = serializer.validated_data['right_type']
        splits_data = serializer.validated_data['splits']

        # Delete existing splits for this object and right type
        Split.objects.filter(
            scope=scope,
            object_id=object_id,
            right_type=right_type,
            is_locked=False  # Only delete unlocked splits
        ).delete()

        created_splits = []
        with transaction.atomic():
            for split_data in splits_data:
                entity_id = split_data.pop('entity_id')
                share = Decimal(str(split_data.pop('share')))
                source = split_data.pop('source', 'manual')

                split = Split.objects.create(
                    scope=scope,
                    object_id=object_id,
                    entity_id=entity_id,
                    right_type=right_type,
                    share=share,
                    source=source
                )
                created_splits.append(split)

        result_serializer = SplitSerializer(created_splits, many=True)
        return Response(result_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def auto_calculate(self, request):
        """Auto-calculate splits from credits."""
        serializer = AutoCalculateSplitsSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        scope = serializer.validated_data['scope']
        object_id = serializer.validated_data['object_id']

        # Perform auto-calculation
        Split.auto_calculate_from_credits(scope, object_id)

        # Return the new splits
        splits = Split.objects.filter(
            scope=scope,
            object_id=object_id
        ).select_related('entity')

        result_serializer = SplitSerializer(splits, many=True)
        return Response(result_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def lock(self, request, pk=None):
        """Lock a split to prevent modifications."""
        split = self.get_object()
        split.is_locked = True
        split.save()
        serializer = self.get_serializer(split)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def unlock(self, request, pk=None):
        """Unlock a split to allow modifications."""
        split = self.get_object()
        split.is_locked = False
        split.save()
        serializer = self.get_serializer(split)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def lock_all(self, request):
        """Lock all splits for an object."""
        scope = request.data.get('scope')
        object_id = request.data.get('object_id')
        right_type = request.data.get('right_type')

        if not scope or not object_id:
            return Response(
                {'error': 'scope and object_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        queryset = Split.objects.filter(
            scope=scope,
            object_id=object_id
        )

        if right_type:
            queryset = queryset.filter(right_type=right_type)

        count = queryset.update(is_locked=True)
        return Response({
            'success': True,
            'locked_count': count
        })

    @action(detail=False, methods=['get'])
    def report(self, request):
        """Generate comprehensive rights validation report."""
        scope = request.query_params.get('scope')
        object_id = request.query_params.get('object_id')

        if not scope or not object_id:
            return Response(
                {'error': 'scope and object_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        report = {
            'errors': [],
            'warnings': [],
            'is_valid': True
        }

        if scope == 'work':
            # Validate work splits
            validation = SplitValidation.validate_work_splits(object_id)
            report['work_validation'] = validation

            if not validation['valid']:
                report['errors'].extend(validation['errors'])
                report['is_valid'] = False
            if validation.get('warnings'):
                report['warnings'].extend(validation['warnings'])

        elif scope == 'recording':
            # Validate recording splits
            validation = SplitValidation.validate_recording_splits(object_id)
            report['recording_validation'] = validation

            if not validation['valid']:
                report['errors'].extend(validation['errors'])
                report['is_valid'] = False
            if validation.get('warnings'):
                report['warnings'].extend(validation['warnings'])

        serializer = RightsValidationReportSerializer(data=report)
        if serializer.is_valid():
            return Response(serializer.data)
        return Response(report)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get split statistics."""
        stats = {
            'total_splits': Split.objects.count(),
            'by_scope': {},
            'by_right_type': {},
            'locked_count': Split.objects.filter(is_locked=True).count(),
            'incomplete_works': [],
            'incomplete_recordings': []
        }

        # Count by scope
        for scope_code, scope_name in Split.SCOPE_CHOICES:
            count = Split.objects.filter(scope=scope_code).count()
            stats['by_scope'][scope_name] = count

        # Count by right type
        for type_code, type_name in Split.RIGHT_TYPE_CHOICES:
            count = Split.objects.filter(right_type=type_code).count()
            stats['by_right_type'][type_name] = count

        # Find incomplete works
        work_ids = Split.objects.filter(scope='work').values('object_id').distinct()
        for work_id in work_ids[:10]:  # Limit to 10 for performance
            obj_id = work_id['object_id']
            for right_type in ['writer', 'publisher']:
                validation = Split.validate_splits_total('work', obj_id, right_type)
                if not validation['is_complete']:
                    work = Work.objects.filter(id=obj_id).first()
                    stats['incomplete_works'].append({
                        'id': obj_id,
                        'title': work.title if work else f"Work #{obj_id}",
                        'right_type': right_type,
                        'total': float(validation['total']),
                        'missing': float(validation['missing'])
                    })

        # Find incomplete recordings
        recording_ids = Split.objects.filter(scope='recording').values('object_id').distinct()
        for recording_id in recording_ids[:10]:  # Limit to 10 for performance
            obj_id = recording_id['object_id']
            validation = Split.validate_splits_total('recording', obj_id, 'master')
            if not validation['is_complete']:
                recording = Recording.objects.filter(id=obj_id).first()
                stats['incomplete_recordings'].append({
                    'id': obj_id,
                    'title': recording.title if recording else f"Recording #{obj_id}",
                    'total': float(validation['total']),
                    'missing': float(validation['missing'])
                })

        return Response(stats)