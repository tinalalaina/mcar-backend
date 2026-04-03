# support/routing.py
from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/support/tickets/(?P<ticket_id>[0-9a-f-]+)/$", consumers.TicketConsumer.as_asgi()),
]
