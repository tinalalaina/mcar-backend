"""
ASGI config for gasycar project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

from notification.routing import websocket_urlpatterns as notifications_urlpatterns
from support.routing import websocket_urlpatterns as support_urlpatterns

# ✅ AJOUT : middleware JWT pour WebSocket
from support.middleware import JwtAuthMiddleware


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gasycar.settings")


django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            # ✅ AJOUT : envelopper le stack existant avec JwtAuthMiddleware
            JwtAuthMiddleware(
                AuthMiddlewareStack(
                    URLRouter(notifications_urlpatterns + support_urlpatterns)
                )
            )
        ),
    }
)
