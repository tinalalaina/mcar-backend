import uuid
from django.db import models
from django.utils import timezone
from users.models import User


class Marque(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nom


class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sous_categories",
        verbose_name="Catégorie parente",
    )

    class Meta:
        verbose_name = "Catégorie de véhicule"
        verbose_name_plural = "Catégories de véhicules"
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class Transmission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nom


class FuelType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nom


class StatusVehicule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nom


class VehicleEquipments(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    label = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Prix par jour (Ar)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.label


class IncludedEquipment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    label = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Équipement inclus"
        verbose_name_plural = "Équipements inclus"
        ordering = ["label"]

    def __str__(self):
        return self.label


class ModeleVehicule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    label = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.label

class Vehicule(models.Model):
    class VehiculeType(models.TextChoices):
        TOURISME = "TOURISME", "Véhicule de tourisme"
        UTILITAIRE = "UTILITAIRE", "Véhicule utilitaire"

    class WorkflowStatus(models.TextChoices):
        DRAFT = "DRAFT", "Brouillon"
        PENDING_REVIEW = "PENDING_REVIEW", "En attente de validation"
        PUBLISHED = "PUBLISHED", "Publié"
        REJECTED = "REJECTED", "Rejeté"

    POPULAR_MIN_RESERVATIONS = 3
    NEW_LISTING_DAYS = 30

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    proprietaire = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="vehicules",
        verbose_name="Propriétaire",
    )

    driver = models.ForeignKey(
        "driver.Driver",
        on_delete=models.SET_NULL,
        related_name="assigned_vehicles",
        verbose_name="Chauffeur attitré",
        null=True,
        blank=True,
    )

    # Identité
    titre = models.CharField("Titre d'annonce", max_length=255, db_index=True)
    marque = models.ForeignKey(
        "Marque",
        on_delete=models.SET_NULL,
        related_name="vehicules",
        verbose_name="Marque",
        null=True,
        blank=True,
    )
    modele = models.ForeignKey(
        "ModeleVehicule",
        on_delete=models.SET_NULL,
        related_name="vehicules",
        verbose_name="Modèle",
        null=True,
        blank=True,
    )
    annee = models.PositiveIntegerField("Année")
    numero_immatriculation = models.CharField(
        "Numéro d'immatriculation",
        max_length=50,
        blank=True,
    )
    numero_serie = models.CharField(
        "Numéro de série (VIN)",
        max_length=100,
        blank=True,
    )

    # Catégorie / type
    categorie = models.ForeignKey(
        "Category",
        on_delete=models.SET_NULL,
        related_name="vehicules",
        verbose_name="Catégorie",
        null=True,
        blank=True,
    )
    transmission = models.ForeignKey(
        "Transmission",
        on_delete=models.SET_NULL,
        related_name="vehicules",
        verbose_name="Boîte de vitesse",
        null=True,
        blank=True,
    )
    type_carburant = models.ForeignKey(
        "FuelType",
        on_delete=models.SET_NULL,
        related_name="vehicules",
        verbose_name="Type de carburant",
        null=True,
        blank=True,
    )
    statut = models.ForeignKey(
        "StatusVehicule",
        on_delete=models.SET_NULL,
        related_name="vehicules",
        verbose_name="Statut",
        null=True,
        blank=True,
    )

    type_vehicule = models.CharField(
        "Type de véhicule",
        max_length=20,
        choices=VehiculeType.choices,
        default=VehiculeType.TOURISME,
        db_index=True,
    )

    # Caractéristiques principales
    nombre_places = models.PositiveIntegerField("Nombre de places", default=5)
    nombre_portes = models.PositiveIntegerField("Nombre de portes", default=4)
    couleur = models.CharField(max_length=50, blank=True)
    kilometrage_actuel_km = models.PositiveIntegerField(
        "Kilométrage actuel (km)",
        default=0,
    )
    volume_coffre_litres = models.PositiveIntegerField(
        "Volume du coffre (L)",
        blank=True,
        null=True,
    )

    # Localisation
    adresse_localisation = models.TextField("Adresse de localisation")
    ville = models.CharField(max_length=100, blank=True, db_index=True)
    zone = models.CharField(
        max_length=100,
        blank=True,
        help_text="Zone / quartier",
    )

    # Tarification
    devise = models.CharField(max_length=10, default="MGA")
    montant_caution = models.DecimalField(
        "Montant de la caution",
        max_digits=10,
        decimal_places=2,
    )

    # Statut & qualité
    est_certifie = models.BooleanField("Véhicule certifié", default=False)
    est_sponsorise = models.BooleanField(
        "Véhicule sponsorisé",
        default=False,
        db_index=True,
    )
    est_coup_de_coeur = models.BooleanField(
        "Véhicule coup de cœur",
        default=False,
        db_index=True,
    )
    est_disponible = models.BooleanField(
        "Disponible à la location",
        default=True,
        db_index=True,
    )

    # Réputation
    note_moyenne = models.DecimalField(
        "Note moyenne",
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
    )
    nombre_locations = models.PositiveIntegerField("Nombre de locations", default=0)
    nombre_favoris = models.PositiveIntegerField(
        "Nombre d'ajouts en favoris",
        default=0,
    )

    # Texte
    description = models.TextField(blank=True)
    conditions_particulieres = models.TextField(
        "Conditions particulières",
        blank=True,
    )

    equipements = models.ManyToManyField(
        "VehicleEquipments",
        related_name="vehicules",
        blank=True,
    )
    included_equipments = models.ManyToManyField(
        "IncludedEquipment",
        related_name="vehicules",
        blank=True,
    )

    # Validation métier
    valide = models.BooleanField(default=False, db_index=True)
    workflow_status = models.CharField(
        max_length=30,
        choices=WorkflowStatus.choices,
        default=WorkflowStatus.DRAFT,
        db_index=True,
    )
    review_comment = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_vehicules",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.marque and self.modele:
            return f"{self.marque.nom} {self.modele.label} ({self.annee}) - {self.proprietaire}"
        return f"{self.titre} - {self.proprietaire}"

    @property
    def latest_documents(self):
        return self.documents.order_by("-updated_at").first()

    @property
    def documents_complete(self):
        doc = self.latest_documents
        return bool(doc and doc.carte_grise and doc.visite_technique and doc.assurance)

    @property
    def documents_validated(self):
        doc = self.latest_documents
        return bool(doc and doc.is_valide)

    @property
    def has_visible_photo(self):
        return self.photos.exists()

    @property
    def has_valid_pricing(self):
        return self.pricing_grid.filter(prix_jour__gt=0).exists()

    @property
    def is_new_listing(self):
        """
        Un véhicule est "nouveau" uniquement si :
        - il a bien une date de publication,
        - il est validé,
        - il est publié,
        - et sa publication date de 30 jours ou moins.
        """
        if not self.published_at:
            return False

        if not self.valide:
            return False

        if self.workflow_status != self.WorkflowStatus.PUBLISHED:
            return False

        delta = timezone.now() - self.published_at
        return delta.days <= self.NEW_LISTING_DAYS

    @property
    def is_popular(self):
        return (self.nombre_locations or 0) >= self.POPULAR_MIN_RESERVATIONS

    @property
    def is_publicly_visible(self):
        owner_is_active = getattr(self.proprietaire, "is_active", True)
        return bool(
            owner_is_active
            and self.valide
            and self.workflow_status == self.WorkflowStatus.PUBLISHED
            and self.documents_validated
            and self.has_visible_photo
            and self.has_valid_pricing
        )

class VehicleConditionReport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vehicle = models.OneToOneField(
        "Vehicule",
        on_delete=models.CASCADE,
        related_name="condition_report",
        verbose_name="Rapport d'état des lieux",
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vehicle_condition_reports",
    )
    view_notes = models.JSONField(default=dict, blank=True)
    saved_view_timestamps = models.JSONField(default=dict, blank=True)
    points = models.JSONField(default=list, blank=True)
    custom_photos_by_view = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Rapport d'état véhicule"
        verbose_name_plural = "Rapports d'état véhicules"

    def __str__(self):
        return f"Rapport état - {self.vehicle.titre}"


class VehiclePricing(models.Model):
    class ZoneType(models.TextChoices):
        URBAIN = "URBAIN", "Zone Urbaine"
        PROVINCE = "PROVINCE", "Province / Hors-ville"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vehicle = models.ForeignKey(
        "Vehicule",
        on_delete=models.CASCADE,
        related_name="pricing_grid",
        verbose_name="Véhicule",
    )
    zone_type = models.CharField(
        max_length=20,
        choices=ZoneType.choices,
        default=ZoneType.URBAIN,
    )

    prix_jour = models.DecimalField("Prix par jour", max_digits=10, decimal_places=2)
    prix_heure = models.DecimalField(
        "Prix par heure",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    prix_mois = models.DecimalField(
        "Prix par mois",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    prix_par_semaine = models.DecimalField(
        "Prix par semaine",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    remise_par_heure = models.DecimalField(
        "Remise par heure (%)",
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    remise_par_jour = models.DecimalField(
        "Remise par jour (%)",
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    remise_par_mois = models.DecimalField(
        "Remise par mois (%)",
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    remise_longue_duree_pourcent = models.DecimalField(
        "Remise longue durée (%)",
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Exemple : 10.00 = -10% pour les longues durées",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Grille Tarifaire"
        verbose_name_plural = "Grilles Tarifaires"
        unique_together = ("vehicle", "zone_type")

    def __str__(self):
        return f"{self.vehicle} - {self.zone_type} - {self.prix_jour}"


class VehiclePhoto(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vehicle = models.ForeignKey(
        "Vehicule",
        on_delete=models.CASCADE,
        related_name="photos",
    )
    image = models.ImageField(upload_to="vehicles/photos/")
    is_primary = models.BooleanField(default=False)
    caption = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Photo {self.vehicle} ({self.id})"


class VehicleAvailability(models.Model):
    class AvailabilityType(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Disponible"
        BLOCKED = "BLOCKED", "Indisponible manuelle"
        MAINTENANCE = "MAINTENANCE", "Maintenance / Réparation"
        RESERVED = "RESERVED", "Réservé automatiquement"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vehicle = models.ForeignKey(
        "Vehicule",
        on_delete=models.CASCADE,
        related_name="availabilities",
    )
    start_date = models.DateField()
    end_date = models.DateField()
    type = models.CharField(
        max_length=20,
        choices=AvailabilityType.choices,
        default=AvailabilityType.BLOCKED,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Disponibilité véhicule"
        verbose_name_plural = "Disponibilités véhicule"
        ordering = ["start_date"]

    def __str__(self):
        return f"{self.vehicle} - {self.type} du {self.start_date} au {self.end_date}"

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.end_date < self.start_date:
            raise ValidationError("La date de fin doit être supérieure à la date de début.")

        overlapping = VehicleAvailability.objects.filter(
            vehicle=self.vehicle,
            start_date__lte=self.end_date,
            end_date__gte=self.start_date,
        ).exclude(id=self.id)

        if overlapping.exists():
            raise ValidationError("Il existe déjà une période de disponibilité pour ces dates.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


def vehicle_doc_upload_path(instance, filename):
    return f"vehicles/docs/{instance.vehicle_id}/{filename}"


class VehicleDocuments(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vehicle = models.ForeignKey(
        "Vehicule",
        on_delete=models.CASCADE,
        related_name="documents",
    )
    carte_grise = models.FileField(
        upload_to=vehicle_doc_upload_path,
        null=True,
        blank=True,
    )
    visite_technique = models.FileField(
        upload_to=vehicle_doc_upload_path,
        null=True,
        blank=True,
    )
    assurance = models.FileField(
        upload_to=vehicle_doc_upload_path,
        null=True,
        blank=True,
    )

    is_valide = models.BooleanField(default=False, db_index=True)
    rejection_reason = models.TextField(blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_vehicle_documents",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Documents {self.vehicle} ({self.id})"

    @property
    def is_complete(self):
        return bool(self.carte_grise and self.visite_technique and self.assurance)


class VehiculeFavorite(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="vehicule_favorites",
        verbose_name="Utilisateur",
    )
    vehicle = models.ForeignKey(
        "Vehicule",
        on_delete=models.CASCADE,
        related_name="favorited_by",
        verbose_name="Véhicule",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Favori véhicule"
        verbose_name_plural = "Favoris véhicules"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "vehicle"],
                name="unique_user_vehicle_favorite",
            ),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} ❤️ {self.vehicle}"
