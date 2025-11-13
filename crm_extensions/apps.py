from django.apps import AppConfig


class CrmExtensionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'crm_extensions'

    def ready(self):
        """Import signals when app is ready."""
        import crm_extensions.signals  # noqa: F401
