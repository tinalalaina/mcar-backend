from django.apps import AppConfig


class PrestataireConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'prestataire'

    def ready(self):
        from . import signals # noqa: F401
