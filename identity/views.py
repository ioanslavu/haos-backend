from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from api.permissions import CanRevealSensitiveIdentity
from django_filters import rest_framework as django_filters
from django.utils import timezone
from django.db.models import Q, Count
from .models import (
    Entity, EntityRole, SensitiveIdentity, Identifier, AuditLogSensitive,
    SocialMediaAccount, ContactPerson, ContactEmail, ContactPhone
)
from .serializers import (
    EntityListSerializer, EntityDetailSerializer, EntityCreateUpdateSerializer,
    EntityRoleSerializer, IdentifierSerializer, SensitiveIdentitySerializer,
    SensitiveIdentityRevealSerializer, AuditLogSensitiveSerializer,
    ClientCompatibilitySerializer, SocialMediaAccountSerializer,
    ContactPersonSerializer
)


class EntityFilter(django_filters.FilterSet):
    """Filter for Entity model."""

    kind = django_filters.ChoiceFilter(choices=Entity.KIND_CHOICES)
    has_role = django_filters.CharFilter(method='filter_has_role')
    search = django_filters.CharFilter(method='filter_search')
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        model = Entity
        fields = ['kind']

    def filter_has_role(self, queryset, name, value):
        """Filter entities by role."""
        return queryset.filter(entity_roles__role=value).distinct()

    def filter_search(self, queryset, name, value):
        """Search entities by name, email, or phone."""
        return queryset.filter(
            Q(display_name__icontains=value) |
            Q(email__icontains=value) |
            Q(phone__icontains=value)
        )


class EntityViewSet(viewsets.ModelViewSet):
    """ViewSet for Entity model."""

    queryset = Entity.objects.all()
    permission_classes = [IsAuthenticated]
    filterset_class = EntityFilter
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    search_fields = ['display_name', 'email', 'phone', 'notes']
    ordering_fields = ['display_name', 'created_at', 'updated_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return EntityListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return EntityCreateUpdateSerializer
        elif self.action == 'placeholders':
            return ClientCompatibilitySerializer
        return EntityDetailSerializer

    def get_queryset(self):
        """Optimize queryset with prefetch_related."""
        queryset = super().get_queryset()
        if self.action == 'list':
            queryset = queryset.prefetch_related('entity_roles')
        else:
            queryset = queryset.prefetch_related(
                'entity_roles'
            )
        return queryset

    @action(detail=True, methods=['get'])
    def placeholders(self, request, pk=None):
        """Get contract placeholders for backward compatibility."""
        entity = self.get_object()
        serializer = ClientCompatibilitySerializer(entity)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def artists(self, request):
        """Get all entities with artist role."""
        queryset = self.get_queryset().filter(
            entity_roles__role='artist'
        ).distinct()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = EntityListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = EntityListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def writers(self, request):
        """Get all entities with writer role."""
        queryset = self.get_queryset().filter(
            entity_roles__role='writer'
        ).distinct()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = EntityListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = EntityListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def producers(self, request):
        """Get all entities with producer role."""
        queryset = self.get_queryset().filter(
            entity_roles__role='producer'
        ).distinct()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = EntityListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = EntityListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get entity statistics."""
        stats = {
            'total_entities': Entity.objects.count(),
            'physical_persons': Entity.objects.filter(kind='PF').count(),
            'legal_entities': Entity.objects.filter(kind='PJ').count(),
            'by_role': {},
            'recent_entities': []
        }

        # Count by role
        for role_code, role_name in EntityRole.ROLE_CHOICES:
            count = Entity.objects.filter(entity_roles__role=role_code).distinct().count()
            stats['by_role'][role_name] = count

        # Recent entities
        recent = Entity.objects.order_by('-created_at')[:5]
        stats['recent_entities'] = EntityListSerializer(recent, many=True).data

        return Response(stats)

    @action(detail=True, methods=['get'])
    def latest_contract_shares(self, request, pk=None):
        """
        Get the latest contract shares for this entity.
        Optionally filter by contract_type.
        Used for auto-populating contract generation forms.
        """
        from contracts.models import Contract, ContractShare
        from contracts.serializers import ContractShareSerializer

        entity = self.get_object()
        contract_type = request.query_params.get('contract_type')

        # Find latest contract for this entity
        query = Contract.objects.filter(
            counterparty_entity=entity,
            status__in=['signed', 'draft']
        )

        if contract_type:
            query = query.filter(contract_type=contract_type)

        latest_contract = query.order_by('-created_at').first()

        if not latest_contract:
            return Response({
                'contract_id': None,
                'contract_type': None,
                'shares': []
            })

        # Get all shares for this contract
        shares = ContractShare.objects.filter(
            contract=latest_contract
        ).select_related('share_type')

        serializer = ContractShareSerializer(shares, many=True)

        return Response({
            'contract_id': latest_contract.id,
            'contract_number': latest_contract.contract_number,
            'contract_type': latest_contract.contract_type,
            'contract_title': latest_contract.title,
            'shares': serializer.data
        })


class SensitiveIdentityViewSet(viewsets.ModelViewSet):
    """ViewSet for SensitiveIdentity model."""

    queryset = SensitiveIdentity.objects.all()
    serializer_class = SensitiveIdentitySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.OrderingFilter
    ]
    filterset_fields = ['entity']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    def get_queryset(self):
        """Filter to only PF entities."""
        return super().get_queryset().select_related('entity')

    # Admin/superuser or users with 'identity.reveal_sensitive_identity'
    # may reveal sensitive fields. Serializer remains masked by default.
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, CanRevealSensitiveIdentity])
    def reveal_cnp(self, request, pk=None):
        """
        Reveal the full CNP with audit logging.

        Authorization strategy (scalable):
        - Superusers, platform administrators, and users granted the
          Django permission 'identity.reveal_sensitive_identity' are allowed.
        - This supports future departments (e.g., Legal/Finance) by
          assigning that permission to their groups — no code changes needed.
        """
        sensitive_identity = self.get_object()
        serializer = SensitiveIdentityRevealSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get IP address
        ip_address = request.META.get('HTTP_X_FORWARDED_FOR')
        if ip_address:
            ip_address = ip_address.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')

        # Log the access
        AuditLogSensitive.objects.create(
            entity=sensitive_identity.entity,
            field='cnp',
            action='revealed',
            viewer_user=request.user,
            reason=serializer.validated_data['reason'],
            viewed_at=timezone.now(),
            ip_address=ip_address,
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            session_key=request.session.session_key if hasattr(request, 'session') else None
        )

        # Return the full CNP
        cnp = sensitive_identity.cnp  # This decrypts the CNP

        # Check if decryption failed
        if cnp is None and sensitive_identity._cnp_encrypted:
            return Response(
                {
                    'error': 'Unable to decrypt CNP. The data may have been encrypted with a different key.',
                    'detail': 'Please re-enter the CNP to update it with the current encryption key.',
                    'needs_reentry': True
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        return Response({
            'cnp': cnp,
            'masked_cnp': sensitive_identity.get_masked_cnp(),
            'audit_logged': True,
            'viewer': request.user.username,
            'timestamp': timezone.now().isoformat()
        })


class IdentifierViewSet(viewsets.ModelViewSet):
    """ViewSet for Identifier model."""

    queryset = Identifier.objects.all()
    serializer_class = IdentifierSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    filterset_fields = ['scheme', 'owner_type', 'pii_flag']
    search_fields = ['value', 'issued_by']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    @action(detail=False, methods=['get'])
    def by_owner(self, request):
        """Get identifiers for a specific owner."""
        owner_type = request.query_params.get('owner_type')
        owner_id = request.query_params.get('owner_id')

        if not owner_type or not owner_id:
            return Response(
                {'error': 'owner_type and owner_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        identifiers = self.get_queryset().filter(
            owner_type=owner_type,
            owner_id=owner_id
        )
        serializer = self.get_serializer(identifiers, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def lookup(self, request):
        """Lookup an identifier by scheme and value."""
        scheme = request.query_params.get('scheme')
        value = request.query_params.get('value')

        if not scheme or not value:
            return Response(
                {'error': 'scheme and value are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            identifier = self.get_queryset().get(
                scheme=scheme,
                value=value
            )
            serializer = self.get_serializer(identifier)
            return Response(serializer.data)
        except Identifier.DoesNotExist:
            return Response(
                {'error': 'Identifier not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class AuditLogSensitiveViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only ViewSet for audit logs."""

    queryset = AuditLogSensitive.objects.all()
    serializer_class = AuditLogSensitiveSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.OrderingFilter
    ]
    filterset_fields = ['entity', 'field', 'action', 'viewer_user']
    ordering_fields = ['viewed_at']
    ordering = ['-viewed_at']

    def get_queryset(self):
        """Optimize with select_related."""
        return super().get_queryset().select_related(
            'entity',
            'viewer_user'
        )

    @action(detail=False, methods=['get'])
    def by_entity(self, request):
        """Get audit logs for a specific entity."""
        entity_id = request.query_params.get('entity_id')
        if not entity_id:
            return Response(
                {'error': 'entity_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        logs = self.get_queryset().filter(entity_id=entity_id)
        page = self.paginate_queryset(logs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(logs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent audit log entries."""
        days = int(request.query_params.get('days', 7))
        since = timezone.now() - timezone.timedelta(days=days)

        logs = self.get_queryset().filter(viewed_at__gte=since)
        page = self.paginate_queryset(logs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(logs, many=True)
        return Response(serializer.data)


# Backward compatibility views
class ClientCompatibilityViewSet(EntityViewSet):
    """Provides backward compatibility with the old Client API."""

    def get_serializer_class(self):
        """Use compatibility serializer."""
        return ClientCompatibilitySerializer

    def get_queryset(self):
        """Filter to entities that could be clients."""
        return Entity.objects.filter(
            Q(entity_roles__role='client') |
            Q(entity_roles__role='artist')
        ).distinct()


class SocialMediaAccountViewSet(viewsets.ModelViewSet):
    """ViewSet for SocialMediaAccount model."""

    queryset = SocialMediaAccount.objects.all()
    serializer_class = SocialMediaAccountSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter by entity if provided."""
        queryset = super().get_queryset()
        entity_id = self.request.query_params.get('entity', None)
        if entity_id:
            queryset = queryset.filter(entity_id=entity_id)
        return queryset.order_by('platform', '-is_primary', '-follower_count')


class ContactPersonViewSet(viewsets.ModelViewSet):
    """ViewSet for ContactPerson model."""

    queryset = ContactPerson.objects.all()
    serializer_class = ContactPersonSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    filterset_fields = ['entity', 'role', 'engagement_stage', 'sentiment']
    search_fields = ['name', 'notes']
    ordering_fields = ['name', 'created_at', 'updated_at']
    ordering = ['name']

    def get_queryset(self):
        """Optimize with prefetch_related for emails and phones."""
        return super().get_queryset().prefetch_related('emails', 'phones').select_related('entity')
