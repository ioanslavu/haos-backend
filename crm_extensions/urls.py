from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TaskViewSet, ActivityViewSet, CampaignMetricsViewSet,
    EntityChangeRequestViewSet, FlowTriggerViewSet, ManualTriggerViewSet
)

router = DefaultRouter()
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'activities', ActivityViewSet, basename='activity')
router.register(r'metrics', CampaignMetricsViewSet, basename='campaignmetrics')
router.register(r'entity-change-requests', EntityChangeRequestViewSet, basename='entitychangerequest')
# Universal task system endpoints
router.register(r'flow-triggers', FlowTriggerViewSet, basename='flowtrigger')
router.register(r'manual-triggers', ManualTriggerViewSet, basename='manualtrigger')

urlpatterns = [
    path('', include(router.urls)),
]