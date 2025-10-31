import django_filters
from django.db import models
from .models import Campaign


class CampaignFilter(django_filters.FilterSet):
    """
    Filter for campaigns with support for:
    - Status filtering
    - Entity filtering (client, artist, brand)
    - Date range filtering
    - Search by campaign name
    """

    # Status filter
    status = django_filters.MultipleChoiceFilter(
        choices=Campaign.STATUS_CHOICES,
        help_text="Filter by status (can specify multiple)"
    )

    # Entity filters
    client = django_filters.NumberFilter(
        field_name='client__id',
        help_text="Filter by client entity ID"
    )

    artist = django_filters.NumberFilter(
        field_name='artist__id',
        help_text="Filter by artist entity ID"
    )

    brand = django_filters.NumberFilter(
        field_name='brand__id',
        help_text="Filter by brand entity ID"
    )

    # Date range filters
    created_after = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='gte',
        help_text="Filter campaigns created after this date"
    )

    created_before = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='lte',
        help_text="Filter campaigns created before this date"
    )

    confirmed_after = django_filters.DateTimeFilter(
        field_name='confirmed_at',
        lookup_expr='gte',
        help_text="Filter campaigns confirmed after this date"
    )

    confirmed_before = django_filters.DateTimeFilter(
        field_name='confirmed_at',
        lookup_expr='lte',
        help_text="Filter campaigns confirmed before this date"
    )

    # Search filter (applied via SearchFilter in view)
    search = django_filters.CharFilter(
        method='filter_search',
        help_text="Search by campaign name, notes, or entity names"
    )

    # Service type filter (for digital campaigns)
    service_type = django_filters.CharFilter(
        method='filter_service_type',
        help_text="Filter by service type"
    )

    class Meta:
        model = Campaign
        fields = [
            'status',
            'client',
            'artist',
            'brand',
            'created_after',
            'created_before',
            'confirmed_after',
            'confirmed_before',
            'service_type',
        ]

    def filter_search(self, queryset, name, value):
        """Custom search across multiple fields"""
        if not value:
            return queryset

        return queryset.filter(
            models.Q(campaign_name__icontains=value) |
            models.Q(notes__icontains=value) |
            models.Q(client__display_name__icontains=value) |
            models.Q(artist__display_name__icontains=value) |
            models.Q(brand__display_name__icontains=value)
        )

    def filter_service_type(self, queryset, name, value):
        """Filter campaigns by service type (ArrayField contains lookup)"""
        if not value:
            return queryset

        # Use contains lookup for ArrayField
        return queryset.filter(service_types__contains=[value])
