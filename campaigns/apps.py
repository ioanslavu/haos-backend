from django.apps import AppConfig


class CampaignsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'campaigns'
    verbose_name = 'Campaign Management'

    def ready(self):
        """Register signal handlers for task automation."""
        from . import signals
