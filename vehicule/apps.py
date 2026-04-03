from django.apps import AppConfig


class VehiculeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'vehicule'

    def ready(self):
        from . import signals  # noqa: F401
