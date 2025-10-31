"""
Digital Financial Views

These views provide financial reporting endpoints for the Digital department.
All calculations, aggregations, and currency conversions are done on the backend
using database aggregations for optimal performance.

Endpoints:
1. /api/v1/digital/financial/metrics/ - Financial overview metrics
2. /api/v1/digital/financial/revenue-by-month/ - Monthly revenue breakdown
3. /api/v1/digital/financial/revenue-by-service/ - Revenue by service type
4. /api/v1/digital/financial/revenue-by-client/ - Top clients by revenue
5. /api/v1/digital/financial/campaigns/ - Campaign financial details
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal

from django.db.models import Sum, Count, Q, F, ExpressionWrapper, DecimalField
from django.db.models.functions import TruncMonth, Coalesce
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from .models import Campaign
from .permissions import HasDigitalDepartmentAccess
from .services import convert_to_eur


logger = logging.getLogger(__name__)


class FinancialPagination(PageNumberPagination):
    """Custom pagination for financial data."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


def get_date_range_from_period(period):
    """
    Convert period filter to start_date and end_date.

    Args:
        period: '7d', '30d', '90d', 'year', or 'custom'

    Returns:
        tuple: (start_date, end_date) or (None, None) for 'custom'
    """
    today = timezone.now().date()

    if period == '7d':
        return (today - timedelta(days=7), today)
    elif period == '30d':
        return (today - timedelta(days=30), today)
    elif period == '90d':
        return (today - timedelta(days=90), today)
    elif period == 'year':
        return (today.replace(month=1, day=1), today)
    else:
        # 'custom' - dates provided separately
        return (None, None)


def apply_financial_filters(queryset, filters):
    """
    Apply filters to campaign queryset.

    Args:
        queryset: Campaign queryset
        filters: dict with filter parameters

    Returns:
        Filtered queryset
    """
    # Date range filtering
    start_date = filters.get('start_date')
    end_date = filters.get('end_date')
    period = filters.get('period', '30d')

    # If period is provided but no dates, calculate dates from period
    if period and period != 'custom' and not (start_date and end_date):
        start_date, end_date = get_date_range_from_period(period)

    if start_date:
        queryset = queryset.filter(start_date__gte=start_date)
    if end_date:
        queryset = queryset.filter(start_date__lte=end_date)

    # Service type filtering (now supports array field)
    service_type = filters.get('service_type')
    if service_type and service_type != 'all':
        queryset = queryset.filter(service_types__contains=[service_type])

    # Campaign status filtering
    campaign_status = filters.get('status')
    if campaign_status and campaign_status != 'all':
        queryset = queryset.filter(status=campaign_status)

    # Invoice status filtering
    invoice_status = filters.get('invoice_status')
    if invoice_status and invoice_status != 'all':
        queryset = queryset.filter(invoice_status=invoice_status)

    return queryset


@api_view(['GET'])
@permission_classes([HasDigitalDepartmentAccess])
def financial_metrics(request):
    """
    Get financial metrics overview.

    Returns aggregated metrics:
    - total_revenue: Sum of all campaign values (converted to EUR)
    - total_profit: Sum of all profits (converted to EUR)
    - total_budget_spent: Sum of all budget spent (converted to EUR)
    - pending_collections: Sum of campaigns with invoice status 'issued' or 'delayed'
    - profit_margin: Percentage of profit relative to revenue

    Query Parameters:
    - start_date: ISO date (YYYY-MM-DD)
    - end_date: ISO date (YYYY-MM-DD)
    - period: '7d', '30d', '90d', 'year', 'custom'
    - service_type: Filter by service type
    - status: Filter by campaign status
    - invoice_status: Filter by invoice status
    """
    try:
        # Get all digital campaigns
        queryset = Campaign.objects.filter(
            department__name='Digital Department'
        ).select_related('client', 'brand')

        # Apply filters
        queryset = apply_financial_filters(queryset, request.query_params)

        # Calculate totals - we'll convert each campaign's values to EUR
        total_revenue = Decimal('0.00')
        total_profit = Decimal('0.00')
        total_budget_spent = Decimal('0.00')
        pending_collections = Decimal('0.00')

        for campaign in queryset:
            # Convert values to EUR
            value_eur = convert_to_eur(campaign.value, campaign.currency) or Decimal('0.00')
            profit_eur = convert_to_eur(campaign.profit, campaign.currency) or Decimal('0.00')
            budget_eur = convert_to_eur(campaign.budget_spent, campaign.currency) or Decimal('0.00')

            total_revenue += value_eur
            total_profit += profit_eur
            total_budget_spent += budget_eur

            # Pending collections (issued or delayed invoices)
            if campaign.invoice_status in ['issued', 'delayed']:
                pending_collections += value_eur

        # Calculate profit margin
        if total_revenue > 0:
            profit_margin = float((total_profit / total_revenue) * 100)
        else:
            profit_margin = 0.0

        return Response({
            'total_revenue': float(total_revenue),
            'total_profit': float(total_profit),
            'total_budget_spent': float(total_budget_spent),
            'pending_collections': float(pending_collections),
            'profit_margin': round(profit_margin, 2)
        })

    except Exception as e:
        logger.error(f"Error calculating financial metrics: {e}", exc_info=True)
        return Response(
            {'error': 'Failed to calculate financial metrics'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([HasDigitalDepartmentAccess])
def revenue_by_month(request):
    """
    Get monthly revenue breakdown.

    Returns list of monthly aggregations with:
    - month: Month label (e.g., "Jan 2024")
    - revenue: Total revenue for the month (EUR)
    - profit: Total profit for the month (EUR)
    - spent: Total budget spent for the month (EUR)

    Query Parameters: Same as financial_metrics
    """
    try:
        # Get filtered campaigns
        queryset = Campaign.objects.filter(
            department__name='Digital Department'
        ).select_related('client', 'brand')

        queryset = apply_financial_filters(queryset, request.query_params)

        # Group by month
        monthly_data = {}

        for campaign in queryset:
            if not campaign.start_date:
                continue

            # Get month key (YYYY-MM format)
            month_key = campaign.start_date.strftime('%Y-%m')
            month_label = campaign.start_date.strftime('%b %Y')

            if month_key not in monthly_data:
                monthly_data[month_key] = {
                    'month': month_label,
                    'revenue': Decimal('0.00'),
                    'profit': Decimal('0.00'),
                    'spent': Decimal('0.00')
                }

            # Convert and accumulate
            value_eur = convert_to_eur(campaign.value, campaign.currency) or Decimal('0.00')
            profit_eur = convert_to_eur(campaign.profit, campaign.currency) or Decimal('0.00')
            budget_eur = convert_to_eur(campaign.budget_spent, campaign.currency) or Decimal('0.00')

            monthly_data[month_key]['revenue'] += value_eur
            monthly_data[month_key]['profit'] += profit_eur
            monthly_data[month_key]['spent'] += budget_eur

        # Convert to list and sort by month
        results = sorted(monthly_data.values(), key=lambda x: x['month'])

        # Convert Decimals to floats for JSON
        for item in results:
            item['revenue'] = float(item['revenue'])
            item['profit'] = float(item['profit'])
            item['spent'] = float(item['spent'])

        return Response(results)

    except Exception as e:
        logger.error(f"Error calculating monthly revenue: {e}", exc_info=True)
        return Response(
            {'error': 'Failed to calculate monthly revenue'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([HasDigitalDepartmentAccess])
def revenue_by_service(request):
    """
    Get revenue by service type.

    Returns list of service types with:
    - service: Service type code
    - service_display: Human-readable service name
    - revenue: Total revenue for this service (EUR)
    - campaign_count: Number of campaigns

    Query Parameters: Same as financial_metrics
    """
    try:
        # Get filtered campaigns
        queryset = Campaign.objects.filter(
            department__name='Digital Department'
        ).select_related('client', 'brand')

        queryset = apply_financial_filters(queryset, request.query_params)

        # Group by service type (campaigns can have multiple service types)
        service_data = {}

        for campaign in queryset:
            # Get all service types for this campaign
            services = campaign.service_types if campaign.service_types else ['unknown']

            # Convert revenue once per campaign
            value_eur = convert_to_eur(campaign.value, campaign.currency) or Decimal('0.00')

            # Distribute to each service type (split revenue if multiple services)
            revenue_per_service = value_eur / len(services) if services else value_eur

            for service in services:
                if service not in service_data:
                    # Get display name from choices
                    service_display = dict(Campaign.SERVICE_TYPE_CHOICES).get(
                        service,
                        service.replace('_', ' ').title()
                    )

                    service_data[service] = {
                        'service': service,
                        'service_display': service_display,
                        'revenue': Decimal('0.00'),
                        'campaign_count': 0
                    }

                # Accumulate (revenue is split among service types)
                service_data[service]['revenue'] += revenue_per_service
                service_data[service]['campaign_count'] += 1

        # Convert to list and sort by revenue (descending)
        results = sorted(
            service_data.values(),
            key=lambda x: x['revenue'],
            reverse=True
        )

        # Convert Decimals to floats for JSON
        for item in results:
            item['revenue'] = float(item['revenue'])

        return Response(results)

    except Exception as e:
        logger.error(f"Error calculating revenue by service: {e}", exc_info=True)
        return Response(
            {'error': 'Failed to calculate revenue by service'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([HasDigitalDepartmentAccess])
def revenue_by_client(request):
    """
    Get top clients by revenue.

    Returns top 5 clients with:
    - client_id: Client entity ID
    - client_name: Client display name
    - revenue: Total revenue from this client (EUR)
    - campaign_count: Number of campaigns

    Query Parameters: Same as financial_metrics
    """
    try:
        # Get filtered campaigns
        queryset = Campaign.objects.filter(
            department__name='Digital Department'
        ).select_related('client', 'brand')

        queryset = apply_financial_filters(queryset, request.query_params)

        # Group by client
        client_data = {}

        for campaign in queryset:
            # Skip campaigns without a client
            if not campaign.client:
                continue

            client_id = campaign.client.id
            client_name = campaign.client.display_name

            if client_id not in client_data:
                client_data[client_id] = {
                    'client_id': client_id,
                    'client_name': client_name,
                    'revenue': Decimal('0.00'),
                    'campaign_count': 0
                }

            # Convert and accumulate
            value_eur = convert_to_eur(campaign.value, campaign.currency) or Decimal('0.00')
            client_data[client_id]['revenue'] += value_eur
            client_data[client_id]['campaign_count'] += 1

        # Convert to list and sort by revenue (descending)
        results = sorted(
            client_data.values(),
            key=lambda x: x['revenue'],
            reverse=True
        )[:5]  # Top 5 clients only

        # Convert Decimals to floats for JSON
        for item in results:
            item['revenue'] = float(item['revenue'])

        return Response(results)

    except Exception as e:
        logger.error(f"Error calculating revenue by client: {e}", exc_info=True)
        return Response(
            {'error': 'Failed to calculate revenue by client'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([HasDigitalDepartmentAccess])
def campaign_financials(request):
    """
    Get campaign financial details (paginated).

    Returns paginated list of campaigns with all financial data.
    All monetary values are converted to EUR on the backend.

    Response includes:
    - EUR converted values (value_eur, budget_spent_eur, profit_eur, etc.)
    - Original currency values for tooltips
    - Campaign details (name, client, service type, dates)
    - Invoice status

    Query Parameters: Same as financial_metrics + pagination
    """
    try:
        # Get filtered campaigns
        queryset = Campaign.objects.filter(
            department__name='Digital Department'
        ).select_related('client', 'brand')

        queryset = apply_financial_filters(queryset, request.query_params)

        # Order by most recent first
        queryset = queryset.order_by('-start_date', '-created_at')

        # Apply pagination
        paginator = FinancialPagination()
        paginated_queryset = paginator.paginate_queryset(queryset, request)

        # Build response data
        results = []
        for campaign in paginated_queryset:
            # Convert all values to EUR
            value_eur = convert_to_eur(campaign.value, campaign.currency)
            budget_spent_eur = convert_to_eur(campaign.budget_spent, campaign.currency)
            profit_eur = convert_to_eur(campaign.profit, campaign.currency)
            internal_cost_eur = convert_to_eur(
                campaign.internal_cost_estimate,
                campaign.currency
            )

            # Get service types display names
            service_types_display = []
            if campaign.service_types:
                service_type_dict = dict(Campaign.SERVICE_TYPE_CHOICES)
                service_types_display = [
                    service_type_dict.get(st, st) for st in campaign.service_types
                ]

            results.append({
                'id': campaign.id,
                'campaign_name': campaign.campaign_name,
                'client_id': campaign.client.id,
                'client_name': campaign.client.display_name,
                'service_types': campaign.service_types or [],
                'service_types_display': service_types_display,

                # EUR converted values
                'value_eur': float(value_eur) if value_eur else None,
                'budget_spent_eur': float(budget_spent_eur) if budget_spent_eur else None,
                'profit_eur': float(profit_eur) if profit_eur else None,
                'internal_cost_estimate_eur': float(internal_cost_eur) if internal_cost_eur else None,

                # Original values (for tooltips)
                'original_currency': campaign.currency,
                'original_value': float(campaign.value) if campaign.value else None,
                'original_budget_spent': float(campaign.budget_spent) if campaign.budget_spent else None,
                'original_profit': float(campaign.profit) if campaign.profit else None,
                'original_internal_cost': float(campaign.internal_cost_estimate) if campaign.internal_cost_estimate else None,

                # Status and dates
                'invoice_status': campaign.invoice_status,
                'campaign_status': campaign.status,
                'start_date': campaign.start_date.isoformat() if campaign.start_date else None,
                'end_date': campaign.end_date.isoformat() if campaign.end_date else None,
            })

        return paginator.get_paginated_response(results)

    except Exception as e:
        logger.error(f"Error fetching campaign financials: {e}", exc_info=True)
        return Response(
            {'error': 'Failed to fetch campaign financials'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([HasDigitalDepartmentAccess])
def kpis_overview(request):
    """
    Get comprehensive KPI overview for Digital department.

    Returns all KPIs in a single response to minimize API calls:
    1. Total active clients (unique clients with active/confirmed campaigns)
    2. Campaigns in progress (active status)
    3. Total revenue current month (EUR)
    4. Average delivery time per service (days)
    5. ROI per campaign type (percentage)
    6. Top 5 clients by revenue

    Query Parameters: Same as financial_metrics
    """
    try:
        # Get all digital campaigns
        queryset = Campaign.objects.filter(
            department__name='Digital Department'
        ).select_related('client', 'brand')

        # Apply filters
        queryset = apply_financial_filters(queryset, request.query_params)

        # ===== KPI 1: Total Active Clients =====
        # Count unique clients with active or confirmed campaigns
        active_client_ids = queryset.filter(
            status__in=['active', 'confirmed'],
            client__isnull=False
        ).values_list('client', flat=True).distinct()
        total_active_clients = len(set(active_client_ids))

        # ===== KPI 2: Campaigns in Progress =====
        campaigns_in_progress = queryset.filter(status='active').count()

        # ===== KPI 3: Total Revenue Current Month =====
        today = timezone.now().date()
        month_start = today.replace(day=1)
        # Get first day of next month
        if today.month == 12:
            next_month_start = today.replace(year=today.year + 1, month=1, day=1)
        else:
            next_month_start = today.replace(month=today.month + 1, day=1)

        current_month_campaigns = queryset.filter(
            start_date__gte=month_start,
            start_date__lt=next_month_start
        )

        total_revenue_current_month = Decimal('0.00')
        for campaign in current_month_campaigns:
            value_eur = convert_to_eur(campaign.value, campaign.currency) or Decimal('0.00')
            total_revenue_current_month += value_eur

        # ===== KPI 4: Average Delivery Time per Service =====
        service_delivery_data = {}

        for campaign in queryset:
            if not campaign.start_date or not campaign.end_date:
                continue

            services = campaign.service_types if campaign.service_types else ['unknown']

            # Calculate delivery time in days
            delivery_days = (campaign.end_date - campaign.start_date).days

            # Distribute to each service type
            for service in services:
                if service not in service_delivery_data:
                    service_display = dict(Campaign.SERVICE_TYPE_CHOICES).get(
                        service,
                        service.replace('_', ' ').title()
                    )
                    service_delivery_data[service] = {
                        'service_type': service,
                        'service_display': service_display,
                        'total_days': 0,
                        'campaign_count': 0
                    }

                service_delivery_data[service]['total_days'] += delivery_days
                service_delivery_data[service]['campaign_count'] += 1

        # Calculate averages
        avg_delivery_by_service = []
        for service_data in service_delivery_data.values():
            if service_data['campaign_count'] > 0:
                avg_days = service_data['total_days'] / service_data['campaign_count']
                avg_delivery_by_service.append({
                    'service_type': service_data['service_type'],
                    'service_display': service_data['service_display'],
                    'avg_delivery_days': round(avg_days, 1),
                    'campaign_count': service_data['campaign_count']
                })

        # Sort by avg delivery days descending
        avg_delivery_by_service.sort(key=lambda x: x['avg_delivery_days'], reverse=True)

        # ===== KPI 5: ROI per Campaign Type =====
        # ROI = (profit / budget_spent) * 100
        roi_data = {}

        for campaign in queryset:
            services = campaign.service_types if campaign.service_types else ['unknown']

            # Convert to EUR
            profit_eur = convert_to_eur(campaign.profit, campaign.currency) or Decimal('0.00')
            budget_eur = convert_to_eur(campaign.budget_spent, campaign.currency) or Decimal('0.00')

            # Split profit and budget among service types if multiple
            profit_per_service = profit_eur / len(services) if services else profit_eur
            budget_per_service = budget_eur / len(services) if services else budget_eur

            for service in services:
                if service not in roi_data:
                    service_display = dict(Campaign.SERVICE_TYPE_CHOICES).get(
                        service,
                        service.replace('_', ' ').title()
                    )
                    roi_data[service] = {
                        'service_type': service,
                        'service_display': service_display,
                        'total_profit': Decimal('0.00'),
                        'total_budget': Decimal('0.00'),
                        'campaign_count': 0
                    }

                roi_data[service]['total_profit'] += profit_per_service
                roi_data[service]['total_budget'] += budget_per_service
                roi_data[service]['campaign_count'] += 1

        # Calculate ROI percentages
        roi_by_campaign_type = []
        for service_data in roi_data.values():
            if service_data['total_budget'] > 0:
                roi_percentage = (service_data['total_profit'] / service_data['total_budget']) * 100
            else:
                roi_percentage = 0.0

            roi_by_campaign_type.append({
                'service_type': service_data['service_type'],
                'service_display': service_data['service_display'],
                'roi': round(float(roi_percentage), 2),
                'total_profit_eur': float(service_data['total_profit']),
                'total_budget_spent_eur': float(service_data['total_budget']),
                'campaign_count': service_data['campaign_count']
            })

        # Sort by ROI descending
        roi_by_campaign_type.sort(key=lambda x: x['roi'], reverse=True)

        # ===== KPI 6: Top 5 Clients =====
        client_data = {}

        for campaign in queryset:
            # Skip campaigns without a client
            if not campaign.client:
                continue

            client_id = campaign.client.id
            client_name = campaign.client.display_name

            if client_id not in client_data:
                client_data[client_id] = {
                    'client_id': client_id,
                    'client_name': client_name,
                    'revenue': Decimal('0.00'),
                    'campaign_count': 0
                }

            # Convert and accumulate
            value_eur = convert_to_eur(campaign.value, campaign.currency) or Decimal('0.00')
            client_data[client_id]['revenue'] += value_eur
            client_data[client_id]['campaign_count'] += 1

        # Convert to list and sort by revenue (descending)
        top_clients = sorted(
            client_data.values(),
            key=lambda x: x['revenue'],
            reverse=True
        )[:5]  # Top 5 clients only

        # Convert Decimals to floats for JSON
        for item in top_clients:
            item['revenue'] = float(item['revenue'])

        # ===== Build Response =====
        response_data = {
            'total_active_clients': total_active_clients,
            'campaigns_in_progress': campaigns_in_progress,
            'total_revenue_current_month': float(total_revenue_current_month),
            'avg_delivery_time_by_service': avg_delivery_by_service,
            'roi_by_campaign_type': roi_by_campaign_type,
            'top_clients': top_clients
        }

        return Response(response_data)

    except Exception as e:
        logger.error(f"Error calculating KPI overview: {e}", exc_info=True)
        return Response(
            {'error': 'Failed to calculate KPI overview'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
