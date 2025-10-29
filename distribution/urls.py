from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PublicationViewSet

router = DefaultRouter()
router.register(r'publications', PublicationViewSet)

app_name = 'distribution'
urlpatterns = [
    path('', include(router.urls)),
]