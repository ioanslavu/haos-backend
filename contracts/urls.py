from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import ContractTemplateViewSet, ContractViewSet, dropbox_sign_webhook
from .api import ContractVerbsView, ContractPolicyView, UserContractsMatrixView

router = DefaultRouter()
router.register(r'templates', ContractTemplateViewSet, basename='contract-template')
router.register(r'contracts', ContractViewSet, basename='contract')

urlpatterns = [
    path('webhook/dropbox-sign/<str:secret_token>/', dropbox_sign_webhook, name='dropbox-sign-webhook'),
    path('rbac/contracts/verbs/', ContractVerbsView.as_view(), name='contracts-verbs'),
    path('rbac/contracts/policy/', ContractPolicyView.as_view(), name='contracts-policy'),
    path('rbac/contracts/users/<int:user_id>/matrix/', UserContractsMatrixView.as_view(), name='contracts-user-matrix'),
] + router.urls
