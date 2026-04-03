from django.apps import AppConfig


class ModepaymentConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modepayment'

    def ready(self):
        from . import signals  # noqa: F401
