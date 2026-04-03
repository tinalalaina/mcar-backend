# support/models.py
import uuid
from django.db import models
from django.utils import timezone

from reservations.models import Reservation
from users.models import User
from vehicule.models import Vehicule


class SupportTicket(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class TicketType(models.TextChoices):
        TECHNICAL = "TECHNICAL", "Technique"
        CONFLICT = "CONFLICT", "Conflit / litige"
        PAYMENT = "PAYMENT", "Paiement"
        OTHER = "OTHER", "Autre"

    class Priority(models.TextChoices):
        LOW = "LOW", "Basse"
        MEDIUM = "MEDIUM", "Moyenne"
        HIGH = "HIGH", "Haute"
        URGENT = "URGENT", "Urgent"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Ouvert"
        IN_PROGRESS = "IN_PROGRESS", "En cours"
        RESOLVED = "RESOLVED", "Résolu"
        CLOSED = "CLOSED", "Fermé"

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="support_tickets",
    )
    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="support_tickets",
    )
    vehicule = models.ForeignKey(
        Vehicule,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="vehicule_tickets",
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    ticket_type = models.CharField(max_length=30, choices=TicketType.choices)
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN
    )

    assigned_admin = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_support_tickets",
    )

    # Pour trier et faire du "dernier message"
    last_activity_at = models.DateTimeField(auto_now_add=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def mark_activity(self):
        self.last_activity_at = timezone.now()
        self.save(update_fields=["last_activity_at", "updated_at"])

    def __str__(self):
        return f"Ticket {self.id} - {self.title}"


class TicketMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    ticket = models.ForeignKey(
        SupportTicket,
        on_delete=models.CASCADE,
        related_name="messages"
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="support_messages",
    )
    message = models.TextField()
    attachment_url = models.URLField(blank=True)

    # Pour différencier "vu / pas vu"
    is_internal = models.BooleanField(default=False)  # note interne admin/support
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Message {self.sender.email} - Ticket {self.ticket.id}"

# support/models.py (suite)

class IncidentReport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class IncidentType(models.TextChoices):
        ACCIDENT = "ACCIDENT", "Accident"
        THEFT = "THEFT", "Vol"
        BREAKDOWN = "BREAKDOWN", "Panne / problème mécanique"
        DAMAGE = "DAMAGE", "Dégâts véhicule"
        OTHER = "OTHER", "Autre"

    class Severity(models.TextChoices):
        LOW = "LOW", "Basse"
        MEDIUM = "MEDIUM", "Moyenne"
        HIGH = "HIGH", "Haute"
        CRITICAL = "CRITICAL", "Critique"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Ouvert"
        IN_PROGRESS = "IN_PROGRESS", "En cours"
        RESOLVED = "RESOLVED", "Résolu"
        CLOSED = "CLOSED", "Fermé"

    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incidents",
    )
    reported_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reported_incidents",
    )
    handled_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="handled_incidents",
    )

    incident_type = models.CharField(
        max_length=30, choices=IncidentType.choices
    )
    severity = models.CharField(
        max_length=20, choices=Severity.choices, default=Severity.MEDIUM
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN
    )

    description = models.TextField()
    location = models.CharField(max_length=255, blank=True)
    occurred_at = models.DateTimeField(null=True, blank=True)

    # Pour stocker photos, documents, etc.
    # (tu peux faire un modèle IncidentAttachment si tu veux + propre)
    attachment_url = models.URLField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    def mark_resolved(self, user: User | None = None):
        self.status = self.Status.RESOLVED
        self.resolved_at = timezone.now()
        if user:
            self.handled_by = user
        self.save(update_fields=["status", "resolved_at", "handled_by", "updated_at"])

    def __str__(self):
        return f"Incident {self.incident_type} - {self.reservation_id}"
