from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CreditViewSet, SplitViewSet

router = DefaultRouter()
router.register(r'credits', CreditViewSet)
router.register(r'splits', SplitViewSet)

app_name = 'rights'
urlpatterns = [
    path('', include(router.urls)),
]