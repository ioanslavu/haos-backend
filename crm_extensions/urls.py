from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TaskViewSet, ActivityViewSet, CampaignMetricsViewSet

router = DefaultRouter()
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'activities', ActivityViewSet, basename='activity')
router.register(r'metrics', CampaignMetricsViewSet, basename='campaignmetrics')

urlpatterns = [
    path('', include(router.urls)),
]