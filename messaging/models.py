# # messaging/models.py
# from django.db import models
# from django.conf import settings
# from core.models import TimeStampedModel
# from vehicles.models import Vehicle


# class Conversation(TimeStampedModel):
#     client = models.ForeignKey(
#         settings.AUTH_USER_MODEL,
#         on_delete=models.CASCADE,
#         related_name="client_conversations",
#     )
#     owner = models.ForeignKey(
#         settings.AUTH_USER_MODEL,
#         on_delete=models.CASCADE,
#         related_name="owner_conversations",
#     )
#     vehicle = models.ForeignKey(
#         Vehicle,
#         on_delete=models.SET_NULL,
#         null=True,
#         blank=True,
#         related_name="conversations",
#     )
#     last_message_at = models.DateTimeField(null=True, blank=True)

#     def __str__(self):
#         return f"Conversation {self.client} ↔ {self.owner}"


# class Message(TimeStampedModel):
#     conversation = models.ForeignKey(
#         Conversation, on_delete=models.CASCADE, related_name="messages"
#     )
#     sender = models.ForeignKey(
#         settings.AUTH_USER_MODEL,
#         on_delete=models.CASCADE,
#         related_name="sent_messages",
#     )
#     content = models.TextField()
#     is_read = models.BooleanField(default=False)

#     def __str__(self):
#         return f"Message de {self.sender.email}"
