from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    EntityViewSet, SensitiveIdentityViewSet, IdentifierViewSet,
    AuditLogSensitiveViewSet, ClientCompatibilityViewSet, SocialMediaAccountViewSet,
    ContactPersonViewSet
)

router = DefaultRouter()
router.register(r'entities', EntityViewSet)
router.register(r'sensitive-identities', SensitiveIdentityViewSet)
router.register(r'identifiers', IdentifierViewSet)
router.register(r'audit-logs', AuditLogSensitiveViewSet)
router.register(r'social-media-accounts', SocialMediaAccountViewSet)
router.register(r'contact-persons', ContactPersonViewSet)
router.register(r'clients', ClientCompatibilityViewSet, basename='client')  # Backward compatibility

app_name = 'identity'
urlpatterns = [
    path('', include(router.urls)),
]