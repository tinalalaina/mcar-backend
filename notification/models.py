from django.db import models
import uuid
from users.models import User


class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class NotificationType(models.TextChoices):
        RESERVATION = "RESERVATION", "Réservation"
        PAYMENT = "PAYMENT", "Paiement"
        MESSAGE = "MESSAGE", "Message"
        SYSTEM = "SYSTEM", "Système"
        VEHICLE = "VEHICLE", "Véhicule"
        VEHICLE_DOCUMENT = "VEHICLE_DOCUMENT", "Document véhicule"

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    reservation = models.ForeignKey(
        "reservations.Reservation",
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )

    vehicle = models.ForeignKey(
        "vehicule.Vehicule",
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )

    vehicle_document = models.ForeignKey(
        "vehicule.VehicleDocuments",
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )

    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices,
    )
    title = models.CharField(max_length=255)
    body = models.TextField()
    action_url = models.CharField(max_length=500, blank=True)
    extra_data = models.JSONField(default=dict, blank=True)

    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notif {self.notification_type} → {self.user.email}"


class TicketNotification(models.Model):
    class NotificationType(models.TextChoices):
        NEW_MESSAGE = "NEW_MESSAGE", "Nouveau message"
        STATUS_CHANGED = "STATUS_CHANGED", "Statut modifié"
        NEW_TICKET = "NEW_TICKET", "Nouveau ticket"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="ticket_notifications",
    )
    ticket = models.ForeignKey(
        "support.SupportTicket",
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    type = models.CharField(max_length=30, choices=NotificationType.choices)
    title = models.CharField(max_length=255)
    message = models.TextField(blank=True)
    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notif {self.type} -> {self.user.email}"