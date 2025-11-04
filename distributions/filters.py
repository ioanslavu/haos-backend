from django_filters import rest_framework as filters
from .models import Distribution, DistributionCatalogItem, DistributionRevenueReport


class DistributionFilter(filters.FilterSet):
    """Filter set for Distribution model"""
    entity = filters.NumberFilter(field_name='entity__id')
    deal_type = filters.MultipleChoiceFilter(choices=Distribution.DEAL_TYPE_CHOICES)
    deal_status = filters.MultipleChoiceFilter(choices=Distribution.DEAL_STATUS_CHOICES)
    signing_date_after = filters.DateFilter(field_name='signing_date', lookup_expr='gte')
    signing_date_before = filters.DateFilter(field_name='signing_date', lookup_expr='lte')
    department = filters.NumberFilter(field_name='department__id')

    class Meta:
        model = Distribution
        fields = ['entity', 'deal_type', 'deal_status', 'department']


class DistributionCatalogItemFilter(filters.FilterSet):
    """Filter set for DistributionCatalogItem model"""
    distribution = filters.NumberFilter(field_name='distribution__id')
    distribution_status = filters.MultipleChoiceFilter(choices=DistributionCatalogItem.DISTRIBUTION_STATUS_CHOICES)
    platforms = filters.CharFilter(field_name='platforms', lookup_expr='contains')
    release_date_after = filters.DateFilter(field_name='release_date', lookup_expr='gte')
    release_date_before = filters.DateFilter(field_name='release_date', lookup_expr='lte')

    class Meta:
        model = DistributionCatalogItem
        fields = ['distribution', 'distribution_status', 'recording', 'release']


class DistributionRevenueReportFilter(filters.FilterSet):
    """Filter set for DistributionRevenueReport model"""
    catalog_item = filters.NumberFilter(field_name='catalog_item__id')
    platform = filters.CharFilter(field_name='platform')
    reporting_period_after = filters.DateFilter(field_name='reporting_period', lookup_expr='gte')
    reporting_period_before = filters.DateFilter(field_name='reporting_period', lookup_expr='lte')
    currency = filters.CharFilter(field_name='currency')

    class Meta:
        model = DistributionRevenueReport
        fields = ['catalog_item', 'platform', 'currency']
