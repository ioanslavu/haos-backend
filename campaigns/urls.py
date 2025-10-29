from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CampaignViewSet

router = DefaultRouter()
router.register(r'campaigns', CampaignViewSet, basename='campaign')

urlpatterns = [
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
