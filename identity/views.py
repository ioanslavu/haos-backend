from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from api.permissions import CanRevealSensitiveIdentity, IsNotGuest
from django_filters import rest_framework as django_filters
from django.utils import timezone
from django.db.models import Q, Count
from .models import (
    Entity, EntityRole, SensitiveIdentity, Identifier, AuditLogSensitive,
    SocialMediaAccount, ContactPerson, ContactEmail, ContactPhone,
    ClientProfile, ClientProfileHistory
)
from .serializers import (
    EntityListSerializer, EntityDetailSerializer, EntityCreateUpdateSerializer,
    EntityRoleSerializer, IdentifierSerializer, SensitiveIdentitySerializer,
    SensitiveIdentityRevealSerializer, AuditLogSensitiveSerializer,
    ClientCompatibilitySerializer, SocialMediaAccountSerializer,
    ContactPersonSerializer, ClientProfileSerializer,
    ClientProfileCreateUpdateSerializer, ClientProfileHistorySerializer
)


class EntityFilter(django_filters.FilterSet):
    """Filter for Entity model."""

    kind = django_filters.ChoiceFilter(choices=Entity.KIND_CHOICES)
    has_role = django_filters.CharFilter(method='filter_has_role')
    is_internal = django_filters.BooleanFilter(method='filter_is_internal')
    search = django_filters.CharFilter(method='filter_search')
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        model = Entity
        fields = ['kind']

    def filter_has_role(self, queryset, name, value):
        """Filter entities by role."""
        return queryset.filter(entity_roles__role=value).distinct()

    def filter_is_internal(self, queryset, name, value):
        """Filter entities by internal/external status."""
        return queryset.filter(entity_roles__is_internal=value).distinct()

    def filter_search(self, queryset, name, value):
        """Search entities by name, email, or phone."""
        return queryset.filter(
            Q(display_name__icontains=value) |
            Q(email__icontains=value) |
            Q(phone__icontains=value)
        )


class EntityViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Entity model.

    Access: All authenticated users except guests can view entities.
    Data shown is filtered by department (campaigns, contact persons, etc.).
    """

    queryset = Entity.objects.all()
    permission_classes = [IsAuthenticated, IsNotGuest]
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
    def business(self, request):
        """
        Get all entities with any business role.
        Used for both client and brand searches in campaigns.

        Business roles include: client, brand, label, booking, endorsements,
        publishing, productie, new_business, digital.
        """
        business_roles = [
            'client', 'brand', 'label', 'booking', 'endorsements',
            'publishing', 'productie', 'new_business', 'digital'
        ]
        queryset = self.get_queryset().filter(
            entity_roles__role__in=business_roles
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
    def relationships(self, request, pk=None):
        """
        Get department-filtered campaigns and contracts for this entity.

        Access rules:
        - Admins: See all campaigns and contracts across all departments
        - Managers: See all campaigns and contracts for their department
        - Employees: See only campaigns and contracts they created or are assigned to
        - Guests: No access
        """
        entity = self.get_object()
        user = request.user
        profile = user.profile

        # Import here to avoid circular imports
        from campaigns.models import Campaign
        from contracts.models import Contract

        # Base querysets
        campaigns_queryset = Campaign.objects.filter(entity=entity)
        contracts_queryset = Contract.objects.filter(counterparty_entity=entity)

        # Apply department filtering based on role level
        if profile.is_admin:
            # Admins see everything
            pass
        elif profile.is_manager:
            # Managers see all data for their department
            if profile.department:
                campaigns_queryset = campaigns_queryset.filter(department=profile.department)
                contracts_queryset = contracts_queryset.filter(department=profile.department)
            else:
                # Manager without department sees nothing
                campaigns_queryset = campaigns_queryset.none()
                contracts_queryset = contracts_queryset.none()
        else:
            # Employees and guests see only their own data
            if profile.department:
                campaigns_queryset = campaigns_queryset.filter(
                    department=profile.department,
                    created_by=user
                )
                contracts_queryset = contracts_queryset.filter(
                    department=profile.department,
                    created_by=user
                )
            else:
                # No department = no access
                campaigns_queryset = campaigns_queryset.none()
                contracts_queryset = contracts_queryset.none()

        # Order and select related
        campaigns = campaigns_queryset.select_related('created_by', 'department').order_by('-created_at')
        contracts = contracts_queryset.select_related('created_by', 'department').order_by('-created_at')

        # Serialize data
        from campaigns.serializers import CampaignSerializer
        from contracts.serializers import ContractSerializer

        return Response({
            'entity_id': entity.id,
            'entity_name': entity.display_name,
            'user_department': profile.department.code if profile.department else None,
            'user_role': profile.role_code,
            'campaigns': CampaignSerializer(campaigns, many=True, context={'request': request}).data,
            'contracts': ContractSerializer(contracts, many=True, context={'request': request}).data,
        })

    @action(detail=True, methods=['get'])
    def latest_contract_shares(self, request, pk=None):
        """
        Get the latest contract shares for this entity.
        Optionally filter by contract_type.
        Used for auto-populating contract generation forms.
        Now respects department filtering.
        """
        from contracts.models import Contract, ContractShare
        from contracts.serializers import ContractShareSerializer

        entity = self.get_object()
        user = request.user
        profile = user.profile
        contract_type = request.query_params.get('contract_type')

        # Find latest contract for this entity with department filtering
        query = Contract.objects.filter(
            counterparty_entity=entity,
            status__in=['signed', 'draft']
        )

        # Apply department filtering
        if profile.is_admin:
            # Admins see all contracts
            pass
        elif profile.is_manager:
            # Managers see their department's contracts
            if profile.department:
                query = query.filter(department=profile.department)
            else:
                query = query.none()
        else:
            # Employees see only their own contracts
            if profile.department:
                query = query.filter(department=profile.department, created_by=user)
            else:
                query = query.none()

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
        """
        Filter to entities with any business role.
        Business roles include: client, brand, label, booking, endorsements,
        publishing, productie, new_business, digital.
        """
        business_roles = [
            'client', 'brand', 'label', 'booking', 'endorsements',
            'publishing', 'productie', 'new_business', 'digital'
        ]
        return Entity.objects.filter(
            entity_roles__role__in=business_roles
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


class ClientProfileFilter(django_filters.FilterSet):
    """Filter for ClientProfile model."""

    entity = django_filters.NumberFilter()
    department = django_filters.NumberFilter()
    min_health_score = django_filters.NumberFilter(field_name='health_score', lookup_expr='gte')
    max_health_score = django_filters.NumberFilter(field_name='health_score', lookup_expr='lte')

    class Meta:
        model = ClientProfile
        fields = ['entity', 'department']


class ClientProfileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for ClientProfile model.

    RBAC:
    - Users can only see and edit profiles for their department
    - Admins can see and edit profiles for all departments
    """

    queryset = ClientProfile.objects.all()
    permission_classes = [IsAuthenticated, IsNotGuest]
    filterset_class = ClientProfileFilter
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.OrderingFilter
    ]
    ordering_fields = ['health_score', 'updated_at', 'created_at']
    ordering = ['-updated_at']

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action in ['create', 'update', 'partial_update']:
            return ClientProfileCreateUpdateSerializer
        return ClientProfileSerializer

    def get_queryset(self):
        """
        Filter queryset based on user's department.
        - Admins see all profiles
        - Users see only their department's profiles
        """
        queryset = super().get_queryset().select_related(
            'entity', 'department', 'updated_by'
        ).prefetch_related('history')

        user = self.request.user
        profile = getattr(user, 'profile', None)

        if not profile:
            return queryset.none()

        # Admins see all profiles
        if profile.is_admin:
            return queryset

        # Users with department see only their department's profiles
        if profile.department:
            return queryset.filter(department=profile.department)

        # Users without department see nothing
        return queryset.none()

    @action(detail=False, methods=['get'])
    def by_entity(self, request):
        """
        Get client profile for a specific entity in user's department.
        For admins, returns all department profiles for that entity.
        """
        entity_id = request.query_params.get('entity_id')
        if not entity_id:
            return Response(
                {'error': 'entity_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        queryset = self.get_queryset().filter(entity_id=entity_id)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        """Get full history for a client profile."""
        profile = self.get_object()
        history = profile.history.order_by('-changed_at')

        page = self.paginate_queryset(history)
        if page is not None:
            serializer = ClientProfileHistorySerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ClientProfileHistorySerializer(history, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get client health statistics for user's department.
        Admins see stats for all departments or a specific department.
        """
        user = request.user
        profile = getattr(user, 'profile', None)

        if not profile:
            return Response({'error': 'User profile not found'}, status=status.HTTP_400_BAD_REQUEST)

        # Get queryset with department filtering
        queryset = self.get_queryset()

        # For admins, allow filtering by specific department
        if profile.is_admin:
            dept_id = request.query_params.get('department_id')
            if dept_id:
                queryset = queryset.filter(department_id=dept_id)

        # Calculate stats
        total_profiles = queryset.count()
        profiles_with_scores = queryset.exclude(health_score__isnull=True)

        stats = {
            'total_profiles': total_profiles,
            'profiles_with_scores': profiles_with_scores.count(),
            'average_health_score': None,
            'score_distribution': {},
            'trend_distribution': {}
        }

        if profiles_with_scores.exists():
            from django.db.models import Avg
            avg_score = profiles_with_scores.aggregate(Avg('health_score'))['health_score__avg']
            stats['average_health_score'] = round(avg_score, 2) if avg_score else None

            # Score distribution (1-3: Poor, 4-6: Fair, 7-10: Good)
            poor = profiles_with_scores.filter(health_score__lte=3).count()
            fair = profiles_with_scores.filter(health_score__gte=4, health_score__lte=6).count()
            good = profiles_with_scores.filter(health_score__gte=7).count()

            stats['score_distribution'] = {
                'poor': poor,
                'fair': fair,
                'good': good
            }

            # Trend distribution
            trends = {'up': 0, 'down': 0, 'stable': 0}
            for profile in profiles_with_scores:
                trend = profile.get_score_trend()
                trends[trend] += 1

            stats['trend_distribution'] = trends

        return Response(stats)


class ClientProfileHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only ViewSet for ClientProfileHistory.
    Users can only see history for profiles in their department.
    """

    queryset = ClientProfileHistory.objects.all()
    serializer_class = ClientProfileHistorySerializer
    permission_classes = [IsAuthenticated, IsNotGuest]
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.OrderingFilter
    ]
    filterset_fields = ['client_profile', 'changed_by']
    ordering_fields = ['changed_at']
    ordering = ['-changed_at']

    def get_queryset(self):
        """
        Filter history based on user's department access to the profile.
        """
        queryset = super().get_queryset().select_related(
            'client_profile__entity',
            'client_profile__department',
            'changed_by'
        )

        user = self.request.user
        profile = getattr(user, 'profile', None)

        if not profile:
            return queryset.none()

        # Admins see all history
        if profile.is_admin:
            return queryset

        # Users see history for their department's profiles only
        if profile.department:
            return queryset.filter(client_profile__department=profile.department)

        return queryset.none()
