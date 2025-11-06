from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    BriefViewSet,
    OpportunityViewSet,
    ProposalViewSet,
    ProposalArtistViewSet,
    DeliverablePackViewSet,
    UsageTermsViewSet,
    DealViewSet,
    DealArtistViewSet,
    DealDeliverableViewSet,
    ApprovalViewSet,
    InvoiceViewSet,
)

router = DefaultRouter()
router.register(r'briefs', BriefViewSet, basename='brief')
router.register(r'opportunities', OpportunityViewSet, basename='opportunity')
router.register(r'proposals', ProposalViewSet, basename='proposal')
router.register(r'proposal-artists', ProposalArtistViewSet, basename='proposal-artist')
router.register(r'deliverable-packs', DeliverablePackViewSet, basename='deliverable-pack')
router.register(r'usage-terms', UsageTermsViewSet, basename='usage-terms')
router.register(r'deals', DealViewSet, basename='deal')
router.register(r'deal-artists', DealArtistViewSet, basename='deal-artist')
router.register(r'deliverables', DealDeliverableViewSet, basename='deal-deliverable')
router.register(r'approvals', ApprovalViewSet, basename='approval')
router.register(r'invoices', InvoiceViewSet, basename='invoice')

urlpatterns = [
    path('', include(router.urls)),
]
