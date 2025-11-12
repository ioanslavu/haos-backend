"""
Views for Camps app
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Count, Q
from django_filters import rest_framework as filters

from api.permissions import IsAdministratorOrManager
from .models import Camp, CampStudio
from .serializers import (
    CampListSerializer,
    CampDetailSerializer,
    CampWriteSerializer,
    CampStudioSerializer
)


class CampFilter(filters.FilterSet):
    """Filter for camps"""
    search = filters.CharFilter(field_name='name', lookup_expr='icontains')
    status = filters.ChoiceFilter(choices=Camp.STATUS_CHOICES)
    time_filter = filters.CharFilter(method='filter_by_time')
    start_date_after = filters.DateFilter(field_name='start_date', lookup_expr='gte')
    start_date_before = filters.DateFilter(field_name='start_date', lookup_expr='lte')

    class Meta:
        model = Camp
        fields = ['search', 'status', 'time_filter', 'start_date_after', 'start_date_before']

    def filter_by_time(self, queryset, name, value):
        """Filter by time relative to today"""
        today = timezone.now().date()

        if value == 'upcoming':
            # Camps with start_date in future OR start_date is null
            return queryset.filter(
                Q(start_date__gte=today) | Q(start_date__isnull=True)
            )
        elif value == 'past':
            # Camps with start_date in past
            return queryset.filter(start_date__lt=today)
        elif value == 'all':
            return queryset

        return queryset


class CampViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Camp model with CRUD operations + duplicate + export_pdf.
    Only managers and admins (level >= 300) have access.
    """
    permission_classes = [IsAuthenticated, IsAdministratorOrManager]
    filterset_class = CampFilter
    ordering_fields = ['name', 'start_date', 'created_at', 'status']
    ordering = ['-start_date', '-created_at']

    def get_queryset(self):
        """
        Return camps excluding soft-deleted ones.
        Note: We don't annotate studios_count here since the model has a property for it.
        """
        queryset = Camp.objects.filter(deleted_at__isnull=True)

        # Prefetch related objects for detail view
        if self.action == 'retrieve':
            queryset = queryset.prefetch_related(
                'studios__studio_artists__artist',
                'created_by',
                'department'
            )

        return queryset.select_related('created_by', 'department')

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return CampListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return CampWriteSerializer
        else:
            return CampDetailSerializer

    def perform_create(self, serializer):
        """Set department and created_by from logged-in user"""
        # Set department if user has a profile with a department
        department = None
        if hasattr(self.request.user, 'profile') and self.request.user.profile.department:
            department = self.request.user.profile.department

        serializer.save(
            department=department,
            created_by=self.request.user
        )

    def perform_destroy(self, instance):
        """Soft delete instead of hard delete"""
        instance.soft_delete()

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """
        Duplicate a camp with all its studios and artists.
        Dates are cleared and status is set to draft.
        """
        original_camp = self.get_object()

        # Create new camp with modified name
        new_camp = Camp.objects.create(
            name=f"{original_camp.name} (Copy)",
            start_date=None,  # Clear dates
            end_date=None,
            status='draft',  # Reset to draft
            department=original_camp.department,
            created_by=request.user
        )

        # Duplicate all studios with their artists
        for studio in original_camp.studios.all():
            # Create new studio
            new_studio = CampStudio.objects.create(
                camp=new_camp,
                name=studio.name,
                location=studio.location,
                city=studio.city,
                country=studio.country,
                hours=studio.hours,
                sessions=studio.sessions,
                order=studio.order
            )

            # Copy all studio artists
            for studio_artist in studio.studio_artists.all():
                studio_artist.pk = None  # Create new instance
                studio_artist.studio = new_studio
                studio_artist.save()

        # Return the duplicated camp
        serializer = CampDetailSerializer(new_camp, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def export_pdf(self, request, pk=None):
        """
        Export camp report as PDF.
        This endpoint will be implemented with PDF generation service.
        """
        camp = self.get_object()

        # Import here to avoid circular import
        from .services.pdf_generator import CampPDFGenerator

        # Generate PDF
        generator = CampPDFGenerator(camp)
        pdf_content = generator.generate_pdf()

        # Return PDF as response
        from django.http import HttpResponse
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="camp_{camp.id}_{camp.name.lower().replace(" ", "_")}.pdf"'
        return response


class CampStudioViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing studios within a camp.
    Nested under /camps/{camp_id}/studios/
    """
    permission_classes = [IsAuthenticated, IsAdministratorOrManager]
    serializer_class = CampStudioSerializer
    ordering = ['order', 'id']

    def get_queryset(self):
        """Filter studios by camp_id from URL"""
        camp_id = self.kwargs.get('camp_pk')
        return CampStudio.objects.filter(
            camp_id=camp_id
        ).prefetch_related('studio_artists__artist')

    def perform_create(self, serializer):
        """Set camp from URL parameter"""
        camp_id = self.kwargs.get('camp_pk')
        serializer.save(camp_id=camp_id)
