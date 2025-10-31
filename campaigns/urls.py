from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CampaignViewSet
from .views_financial import (
    financial_metrics,
    revenue_by_month,
    revenue_by_service,
    revenue_by_client,
    campaign_financials,
    kpis_overview,
)

router = DefaultRouter()
router.register(r'campaigns', CampaignViewSet, basename='campaign')

urlpatterns = [
    # Digital Financial endpoints (protected by HasDigitalDepartmentAccess)
    path('digital/financial/metrics/',
         financial_metrics,
         name='digital-financial-metrics'),
    path('digital/financial/revenue-by-month/',
         revenue_by_month,
         name='digital-financial-revenue-by-month'),
    path('digital/financial/revenue-by-service/',
         revenue_by_service,
         name='digital-financial-revenue-by-service'),
    path('digital/financial/revenue-by-client/',
         revenue_by_client,
         name='digital-financial-revenue-by-client'),
    path('digital/financial/campaigns/',
         campaign_financials,
         name='digital-financial-campaigns'),
    path('digital/financial/kpis/',
         kpis_overview,
         name='digital-financial-kpis'),

    # Manual routes for analytics detail endpoints (must come before router.urls)
    path('campaigns/brand_analytics/<int:brand_id>/',
         CampaignViewSet.as_view({'get': 'brand_analytics_detail'}),
         name='campaign-brand-analytics-detail'),
    path('campaigns/artist_analytics/<int:artist_id>/',
         CampaignViewSet.as_view({'get': 'artist_analytics_detail'}),
         name='campaign-artist-analytics-detail'),
    path('campaigns/client_analytics/<int:client_id>/',
         CampaignViewSet.as_view({'get': 'client_analytics_detail'}),
         name='campaign-client-analytics-detail'),
    path('', include(router.urls)),
]
