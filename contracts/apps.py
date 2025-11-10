from django.apps import AppConfig


class ContractsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'contracts'

    def ready(self):
        """Register models with django-auditlog for automatic audit trail."""
        from auditlog.registry import auditlog
        from .models import Contract, ContractSignature, WebhookEvent

        # Register Contract with specific fields to track
        auditlog.register(
            Contract,
            include_fields=['status', 'signed_at', 'dropbox_sign_request_id', 'is_public', 'public_share_url']
        )

        # Register ContractSignature with specific fields to track
        auditlog.register(
            ContractSignature,
            include_fields=['status', 'signed_at', 'viewed_at', 'declined_at', 'decline_reason']
        )

        # Register WebhookEvent for complete audit trail
        auditlog.register(
            WebhookEvent,
            include_fields=['processed', 'verified_with_api', 'error_message']
        )

        # Import signals to register handlers
        from . import signals
