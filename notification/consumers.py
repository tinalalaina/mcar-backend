from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
import json


class NotificationConsumer(WebsocketConsumer):
    room_group_name = None

    def connect(self):
        user = self.scope["user"]

        if not user or not user.is_authenticated:
            self.close()
            return

        self.room_group_name = f"user_{user.id}"

        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name,
        )

        self.accept()

    def disconnect(self, close_code):
        if self.room_group_name:
            async_to_sync(self.channel_layer.group_discard)(
                self.room_group_name,
                self.channel_name,
            )

    def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message = text_data_json.get("message")
        except Exception:
            return

        if not message:
            return

        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                "type": "notification_message",
                "message": message,
            },
        )

    def notification_message(self, event):
        message = event["message"]
        self.send(text_data=json.dumps(message))

    def ticket_notification(self, event):
        self.send(
            text_data=json.dumps(
                {
                    "event": event.get("event"),
                    "data": event.get("data"),
                }
            )
        )