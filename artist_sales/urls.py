"""
URL Configuration for Artist Sales - Unified Opportunities API
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    OpportunityViewSet, OpportunityArtistViewSet, OpportunityTaskViewSet,
    OpportunityActivityViewSet, OpportunityCommentViewSet, OpportunityDeliverableViewSet,
    ApprovalViewSet, InvoiceViewSet, DeliverablePackViewSet, UsageTermsViewSet
)

router = DefaultRouter()

# Main opportunities endpoint
router.register(r'opportunities', OpportunityViewSet, basename='opportunity')

# Related endpoints
router.register(r'opportunity-artists', OpportunityArtistViewSet, basename='opportunity-artist')
router.register(r'opportunity-tasks', OpportunityTaskViewSet, basename='opportunity-task')
router.register(r'opportunity-activities', OpportunityActivityViewSet, basename='opportunity-activity')
router.register(r'opportunity-comments', OpportunityCommentViewSet, basename='opportunity-comment')
router.register(r'opportunity-deliverables', OpportunityDeliverableViewSet, basename='opportunity-deliverable')

# Supporting endpoints
router.register(r'approvals', ApprovalViewSet, basename='approval')
router.register(r'invoices', InvoiceViewSet, basename='invoice')
router.register(r'deliverable-packs', DeliverablePackViewSet, basename='deliverable-pack')
router.register(r'usage-terms', UsageTermsViewSet, basename='usage-terms')

urlpatterns = [
    path('', include(router.urls)),
]
