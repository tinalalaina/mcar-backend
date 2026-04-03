from django.apps import AppConfig


class SmsappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'smsapp'

    def ready(self):
        from . import signals  # noqa: F401
 
