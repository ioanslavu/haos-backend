from django.apps import AppConfig


class ArtistSalesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'artist_sales'

    def ready(self):
        """Register signal handlers for task automation."""
        from . import signals
