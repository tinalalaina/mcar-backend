import uuid
from django.db import models
from django.utils import timezone
from users.models import User


class Driver(models.Model):
    """
    Informations principales du chauffeur.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL, # Changed to SET_NULL to avoid deleting driver if user is deleted
        related_name="driver_profile",
        null=True,
        blank=True
    )

    
    # Propriétaire du chauffeur (Prestataire)
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="my_drivers",
        verbose_name="Propriétaire (Prestataire)",
        null=True, # Allow null temporarily for migration compatibility, or default to admin
        blank=True
    )

    # Informations personnelles
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField(null=True, blank=True)
    nationality = models.CharField(max_length=100, blank=True)

    # Informations professionnelles
    experience_years = models.PositiveIntegerField(default=0)
    is_available = models.BooleanField(default=True)
    driver_rate = models.DecimalField("Tarif chauffeur", max_digits=12, decimal_places=2, null=True, blank=True)

    phone_number = models.CharField(max_length=50)
    secondary_phone = models.CharField(max_length=50, blank=True)

    # Adresse
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)

    # Photo du chauffeur
    profile_photo = models.ImageField(
        upload_to="drivers/photos/",
        blank=True,
        null=True
    )

    # Permis de conduire (Champs fusionnés de DriverLicense)
    license_number = models.CharField("Numéro de permis", max_length=100, blank=True)
    license_category = models.CharField("Catégorie", max_length=50, blank=True, help_text="Ex: B, C") 
    license_issued_date = models.DateField("Date de délivrance", null=True, blank=True)
    license_expiry_date = models.DateField("Date d'expiration", null=True, blank=True)
    license_photo = models.ImageField(
        "Scan du permis",
        upload_to="drivers/licenses/",
        null=True,
        blank=True
    )

    # Certificat de résidence
    residence_certificate = models.FileField(
        "Certificat de résidence",
        upload_to="drivers/residence/",
        null=True,
        blank=True
    )
    residence_issued_date = models.DateField("Date de délivrance certificat de résidence", null=True, blank=True)
    residence_validity_months = models.PositiveIntegerField("Validité certificat de résidence (mois)", null=True, blank=True)

    # CIN
    cin_number = models.CharField("Numéro CIN", max_length=100, blank=True)
    cin_recto = models.ImageField(
        "Recto du CIN",
        upload_to="drivers/cins/",
        null=True,
        blank=True
    )
    cin_verso = models.ImageField(
        "Verso du CIN",
        upload_to="drivers/cins/",
        null=True,
        blank=True
    )

    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Driver {self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def is_admin_pool(self):
        """Retourne True si le chauffeur appartient au pool admin (pas de owner spécifique ou owner=superadmin)"""
        return self.owner is None or self.owner.is_superuser
