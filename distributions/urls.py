from rest_framework_nested import routers
from .views import DistributionViewSet, DistributionCatalogItemViewSet, DistributionRevenueReportViewSet

# Main router for distributions
router = routers.DefaultRouter()
router.register(r'distributions', DistributionViewSet, basename='distribution')

# Nested router for catalog items under distributions
# /distributions/{distribution_pk}/catalog-items/
distributions_router = routers.NestedDefaultRouter(router, r'distributions', lookup='distribution')
distributions_router.register(r'catalog-items', DistributionCatalogItemViewSet, basename='distribution-catalog-items')

# Nested router for revenue reports under catalog items
# /distributions/{distribution_pk}/catalog-items/{catalog_item_pk}/revenue-reports/
catalog_items_router = routers.NestedDefaultRouter(distributions_router, r'catalog-items', lookup='catalog_item')
catalog_items_router.register(r'revenue-reports', DistributionRevenueReportViewSet, basename='catalog-item-revenue-reports')

# Combine all URL patterns
urlpatterns = router.urls + distributions_router.urls + catalog_items_router.urls
