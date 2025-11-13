from django.apps import AppConfig


class IdentityConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'identity'

    def ready(self):
        """Register signal handlers for checklist auto-validation."""
        from . import signals
