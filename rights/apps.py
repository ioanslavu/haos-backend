from django.apps import AppConfig


class RightsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'rights'

    def ready(self):
        """Register signal handlers for checklist auto-validation."""
        from . import signals
