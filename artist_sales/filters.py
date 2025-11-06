import django_filters
from django.db import models
from .models import Brief, Opportunity, Proposal, Deal


class BriefFilter(django_filters.FilterSet):
    """
    Filter for briefs with support for:
    - Status filtering
    - Account filtering
    - Date range filtering
    - SLA overdue filtering
    """

    brief_status = django_filters.MultipleChoiceFilter(
        choices=Brief.STATUS_CHOICES,
        help_text="Filter by status (can specify multiple)"
    )

    account = django_filters.NumberFilter(
        field_name='account__id',
        help_text="Filter by account entity ID"
    )

    created_after = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='gte',
        help_text="Filter briefs created after this date"
    )

    created_before = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='lte',
        help_text="Filter briefs created before this date"
    )

    sla_overdue = django_filters.BooleanFilter(
        method='filter_sla_overdue',
        help_text="Filter overdue briefs"
    )

    class Meta:
        model = Brief
        fields = [
            'brief_status',
            'account',
            'brand_category',
            'created_after',
            'created_before',
            'sla_overdue',
        ]

    def filter_sla_overdue(self, queryset, name, value):
        """Filter overdue briefs"""
        if value is None:
            return queryset

        from django.utils import timezone
        today = timezone.now().date()

        if value:
            # Show only overdue briefs
            return queryset.filter(
                sla_due_date__lt=today,
                brief_status__in=['new', 'qualified']
            )
        else:
            # Show only non-overdue briefs
            return queryset.exclude(
                sla_due_date__lt=today,
                brief_status__in=['new', 'qualified']
            )


class OpportunityFilter(django_filters.FilterSet):
    """
    Filter for opportunities with support for:
    - Stage filtering
    - Account filtering
    - Owner filtering
    - Date range filtering
    """

    stage = django_filters.MultipleChoiceFilter(
        choices=Opportunity.STAGE_CHOICES,
        help_text="Filter by stage (can specify multiple)"
    )

    account = django_filters.NumberFilter(
        field_name='account__id',
        help_text="Filter by account entity ID"
    )

    owner_user = django_filters.NumberFilter(
        field_name='owner_user__id',
        help_text="Filter by owner user ID"
    )

    brief = django_filters.NumberFilter(
        field_name='brief__id',
        help_text="Filter by brief ID"
    )

    created_after = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='gte',
        help_text="Filter opportunities created after this date"
    )

    created_before = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='lte',
        help_text="Filter opportunities created before this date"
    )

    expected_close_after = django_filters.DateFilter(
        field_name='expected_close_date',
        lookup_expr='gte',
        help_text="Filter opportunities with expected close date after this date"
    )

    expected_close_before = django_filters.DateFilter(
        field_name='expected_close_date',
        lookup_expr='lte',
        help_text="Filter opportunities with expected close date before this date"
    )

    min_amount = django_filters.NumberFilter(
        field_name='amount_expected',
        lookup_expr='gte',
        help_text="Minimum expected amount"
    )

    max_amount = django_filters.NumberFilter(
        field_name='amount_expected',
        lookup_expr='lte',
        help_text="Maximum expected amount"
    )

    class Meta:
        model = Opportunity
        fields = [
            'stage',
            'account',
            'owner_user',
            'brief',
            'created_after',
            'created_before',
            'expected_close_after',
            'expected_close_before',
            'min_amount',
            'max_amount',
        ]


class ProposalFilter(django_filters.FilterSet):
    """
    Filter for proposals with support for:
    - Status filtering
    - Opportunity filtering
    - Date range filtering
    """

    proposal_status = django_filters.MultipleChoiceFilter(
        choices=Proposal.STATUS_CHOICES,
        help_text="Filter by status (can specify multiple)"
    )

    opportunity = django_filters.NumberFilter(
        field_name='opportunity__id',
        help_text="Filter by opportunity ID"
    )

    created_after = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='gte',
        help_text="Filter proposals created after this date"
    )

    created_before = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='lte',
        help_text="Filter proposals created before this date"
    )

    sent_after = django_filters.DateTimeFilter(
        field_name='sent_date',
        lookup_expr='gte',
        help_text="Filter proposals sent after this date"
    )

    sent_before = django_filters.DateTimeFilter(
        field_name='sent_date',
        lookup_expr='lte',
        help_text="Filter proposals sent before this date"
    )

    class Meta:
        model = Proposal
        fields = [
            'proposal_status',
            'opportunity',
            'version',
            'created_after',
            'created_before',
            'sent_after',
            'sent_before',
        ]


class DealFilter(django_filters.FilterSet):
    """
    Filter for deals with support for:
    - Status filtering
    - Account filtering
    - Date range filtering
    - Artist filtering
    """

    deal_status = django_filters.MultipleChoiceFilter(
        choices=Deal.STATUS_CHOICES,
        help_text="Filter by status (can specify multiple)"
    )

    account = django_filters.NumberFilter(
        field_name='account__id',
        help_text="Filter by account entity ID"
    )

    opportunity = django_filters.NumberFilter(
        field_name='opportunity__id',
        help_text="Filter by opportunity ID"
    )

    artist = django_filters.NumberFilter(
        method='filter_artist',
        help_text="Filter by artist entity ID"
    )

    created_after = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='gte',
        help_text="Filter deals created after this date"
    )

    created_before = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='lte',
        help_text="Filter deals created before this date"
    )

    start_date_after = django_filters.DateFilter(
        field_name='start_date',
        lookup_expr='gte',
        help_text="Filter deals starting after this date"
    )

    start_date_before = django_filters.DateFilter(
        field_name='start_date',
        lookup_expr='lte',
        help_text="Filter deals starting before this date"
    )

    end_date_after = django_filters.DateFilter(
        field_name='end_date',
        lookup_expr='gte',
        help_text="Filter deals ending after this date"
    )

    end_date_before = django_filters.DateFilter(
        field_name='end_date',
        lookup_expr='lte',
        help_text="Filter deals ending before this date"
    )

    min_fee = django_filters.NumberFilter(
        field_name='fee_total',
        lookup_expr='gte',
        help_text="Minimum fee"
    )

    max_fee = django_filters.NumberFilter(
        field_name='fee_total',
        lookup_expr='lte',
        help_text="Maximum fee"
    )

    expiring_soon = django_filters.BooleanFilter(
        method='filter_expiring_soon',
        help_text="Filter deals expiring within 30 days"
    )

    class Meta:
        model = Deal
        fields = [
            'deal_status',
            'account',
            'opportunity',
            'artist',
            'created_after',
            'created_before',
            'start_date_after',
            'start_date_before',
            'end_date_after',
            'end_date_before',
            'min_fee',
            'max_fee',
            'expiring_soon',
        ]

    def filter_artist(self, queryset, name, value):
        """Filter deals by artist (via DealArtist M2M)"""
        if not value:
            return queryset
        return queryset.filter(deal_artists__artist__id=value).distinct()

    def filter_expiring_soon(self, queryset, name, value):
        """Filter deals expiring within 30 days"""
        if value is None:
            return queryset

        from django.utils import timezone
        today = timezone.now().date()
        in_30_days = today + timezone.timedelta(days=30)

        if value:
            # Show only expiring soon
            return queryset.filter(
                end_date__gte=today,
                end_date__lte=in_30_days,
                deal_status__in=['signed', 'active']
            )
        else:
            # Show only not expiring soon
            return queryset.exclude(
                end_date__gte=today,
                end_date__lte=in_30_days,
                deal_status__in=['signed', 'active']
            )
