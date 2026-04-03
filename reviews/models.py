# apps/reviews/models.py
import uuid

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from users.models import User


class Review(models.Model):
    """
    Avis et notes entre utilisateurs, basés sur une réservation.
    - Un avis est toujours lié à une réservation réelle.
    - author = celui qui écrit l'avis (client ou propriétaire)
    - target = celui qui reçoit l'avis (propriétaire ou client)
    """

    class ReviewType(models.TextChoices):
        CLIENT_TO_OWNER = "CLIENT_TO_OWNER", "Client → Propriétaire"
        OWNER_TO_CLIENT = "OWNER_TO_CLIENT", "Propriétaire → Client"

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )

    reservation = models.ForeignKey(
        "reservations.Reservation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviews",
        help_text="Réservation sur laquelle porte cet avis.",
    )

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="reviews_written",
        help_text="Utilisateur qui a rédigé l'avis.",
    )

    target = models.ForeignKey(
       User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviews_received",
        help_text="Utilisateur qui reçoit l'avis (client ou propriétaire).",
    )

    review_type = models.CharField(
        max_length=32,
        choices=ReviewType.choices,
        help_text="Sens de l'avis : client vers propriétaire ou inverse.",
    )

    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Note de 1 à 5.",
    )

    comment = models.TextField(
        blank=True,
        help_text="Commentaire optionnel pour détailler l'expérience.",
    )

    is_verified = models.BooleanField(
        default=True,
        help_text="True si l'avis est lié à une réservation réellement effectuée.",
    )

    class ModerationStatus(models.TextChoices):
        PENDING = "PENDING", "En attente"
        APPROVED = "APPROVED", "Approuvé"
        REJECTED = "REJECTED", "Rejeté"

    moderation_status = models.CharField(
        max_length=20,
        choices=ModerationStatus.choices,
        default=ModerationStatus.PENDING,
        db_index=True,
        help_text="Statut de modération par le support avant publication.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reviews"
        ordering = ("-created_at",)
        verbose_name = "Avis"
        verbose_name_plural = "Avis"
        constraints = [
            # Pour les avis AVEC réservation : empêche qu'un même utilisateur laisse 
            # plusieurs avis dans le même sens pour la même réservation
            models.UniqueConstraint(
                fields=["reservation", "author", "review_type"],
                condition=models.Q(reservation__isnull=False),
                name="unique_review_per_reservation_and_direction",
            ),
            # Pour les avis SANS réservation : permet à un utilisateur de laisser
            # un seul avis par cible (propriétaire) dans chaque sens
            models.UniqueConstraint(
                fields=["author", "target", "review_type"],
                condition=models.Q(reservation__isnull=True),
                name="unique_review_without_reservation",
            ),
        ]

    def __str__(self):
        return f"Review {self.id} - {self.rating}/5 par {self.author_id} → {self.target_id}"
