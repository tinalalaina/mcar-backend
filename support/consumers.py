# support/consumers.py
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async





from .models import SupportTicket, TicketMessage


class TicketConsumer(AsyncJsonWebsocketConsumer):
    @database_sync_to_async
    def create_message(self, message_text):
        # On suppose que le ticket exists car connect() l'a validé (ou try/except)
        return TicketMessage.objects.create(
            ticket_id=self.ticket_id,
            sender=self.scope["user"],
            message=message_text
        )

    async def receive_json(self, content, **kwargs):
        # Client envoie { "message": "hello" }
        message_text = content.get("message")
        if not message_text:
            return

        # Création en DB => déclenche le signal post_save => on_new_ticket_message
        # => envoie le message sur le group WS
        await self.create_message(message_text)

    async def connect(self):
        if self.scope["user"].is_anonymous:
            await self.close()
            return

        self.ticket_id = self.scope["url_route"]["kwargs"]["ticket_id"]
        self.group_name = f"ticket_{self.ticket_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def ticket_message(self, event):
        # push d’un nouveau message sur un ticket
        await self.send_json(event)
