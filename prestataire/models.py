# prestataires/models.py
import uuid
from django.db import models
from users.models import User


class Prestataire(models.Model):
    """
    Représente un fournisseur / loueur / partenaire qui ajoute des véhicules
    sur la plateforme.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Lien avec le user (propriétaire du compte prestataire)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="prestataire_profile"
    )

    # Informations de base
    company_name = models.CharField(max_length=255, help_text="Nom commercial ou entreprise")
    logo = models.ImageField(upload_to="prestataires/logos/", blank=True, null=True)

    # Identifiant légal Madagascar
    nif = models.CharField(
        max_length=50,
        unique=True,
        help_text="Numéro NIF (Identifiant fiscal)",
    )
    stat = models.CharField(
        max_length=50,
        unique=True,
        help_text="Numéro STAT",
    )
    rcs = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Numéro RCS (Registre du commerce)"
    )
    cif = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Code d’identification fiscale"
    )

    # Documents officiels (scannés)
    nif_document = models.FileField(upload_to="prestataires/docs/nif/", blank=True, null=True)
    stat_document = models.FileField(upload_to="prestataires/docs/stat/", blank=True, null=True)
    rcs_document = models.FileField(upload_to="prestataires/docs/rcs/", blank=True, null=True)
    cif_document = models.FileField(upload_to="prestataires/docs/cif/", blank=True, null=True)

    # Coordonnées
    phone = models.CharField(max_length=50)
    secondary_phone = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(max_length=255)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)

    # Statut du prestataire
    class Status(models.TextChoices):
        PENDING_VERIFICATION = "PENDING_VERIFICATION", "En attente de vérification"
        ACTIVE = "ACTIVE", "Actif"
        SUSPENDED = "SUSPENDED", "Suspendu"
        REJECTED = "REJECTED", "Rejeté"

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING_VERIFICATION
    )

    # Par quel admin/support il a été vérifié
    validated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="validated_prestataires"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_verified(self):
        return self.status == Prestataire.Status.ACTIVE

    def __str__(self):
        return f"{self.company_name} ({self.nif})"
