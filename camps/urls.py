from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CampViewSet

router = DefaultRouter()
router.register(r'', CampViewSet, basename='camp')

urlpatterns = [
    path('', include(router.urls)),
]
