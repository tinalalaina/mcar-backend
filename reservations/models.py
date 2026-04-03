from django.db import models
from vehicule.models import Vehicule
import uuid
from users.models import User
from modepayment.models import ModePayment


def generate_reservation_reference():
    from django.utils import timezone
    from reservations.models import Reservation

    today = timezone.now().date()
    date_str = today.strftime("%Y%m%d")
    prefix = f"RES-{date_str}-"

    last_reservation = Reservation.objects.filter(
        reference__startswith=prefix
    ).order_by("-reference").first()

    if last_reservation:
        last_number = int(last_reservation.reference.split("-")[-1])
        new_number = last_number + 1
    else:
        new_number = 1

    return f"{prefix}{new_number:04d}"


class ReservationQuerySet(models.QuerySet):
    def with_relations(self):
        return self.select_related("client", "vehicle").prefetch_related("services")


class Reservation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    reference = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        db_index=True,
        blank=True,
        help_text="Référence unique auto-générée (ex: RES-20251219-0001)",
    )

    class Status(models.TextChoices):
        PENDING = "PENDING", "En attente"
        CONFIRMED = "CONFIRMED", "Confirmée"
        IN_PROGRESS = "IN_PROGRESS", "En cours"
        COMPLETED = "COMPLETED", "Terminée"
        CANCELLED = "CANCELLED", "Annulée"

    client = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="reservations",
    )
    vehicle = models.ForeignKey(
        Vehicule,
        on_delete=models.CASCADE,
        related_name="reservations",
    )
    driver = models.ForeignKey(
        "driver.Driver",
        on_delete=models.SET_NULL,
        related_name="reservations",
        verbose_name="Chauffeur assigné",
        null=True,
        blank=True,
    )

    equipments = models.ManyToManyField(
        "vehicule.VehicleEquipments",
        related_name="reservations",
        blank=True,
        verbose_name="Équipements supplémentaires",
    )

    class DrivingMode(models.TextChoices):
        SELF_DRIVE = "SELF_DRIVE", "Je conduis (Self-drive)"
        WITH_DRIVER = "WITH_DRIVER", "Avec chauffeur pro"

    class PricingZone(models.TextChoices):
        URBAIN = "URBAIN", "Zone Urbaine"
        PROVINCE = "PROVINCE", "Province"

    class DriverSource(models.TextChoices):
        NONE = "NONE", "Aucun (Self-drive)"
        PROVIDER = "PROVIDER", "Chauffeur Prestataire"
        ADMIN_POOL = "ADMIN_POOL", "Pool Admin"

    driving_mode = models.CharField(
        max_length=20,
        choices=DrivingMode.choices,
        default=DrivingMode.SELF_DRIVE,
    )
    pricing_zone = models.CharField(
        max_length=20,
        choices=PricingZone.choices,
        default=PricingZone.URBAIN,
    )
    driver_source = models.CharField(
        max_length=20,
        choices=DriverSource.choices,
        default=DriverSource.NONE,
    )
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    total_days = models.PositiveIntegerField()
    base_amount = models.DecimalField(max_digits=10, decimal_places=2)
    options_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    caution_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    with_chauffeur = models.BooleanField(default=False)
    pickup_location = models.TextField()
    dropoff_location = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ReservationQuerySet.as_manager()

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = generate_reservation_reference()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Reservation {self.reference} - {self.client.email}"


class ReservationPricingConfig(models.Model):
    service_fee = models.DecimalField(max_digits=10, decimal_places=2, default=5000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuration tarification réservation"
        verbose_name_plural = "Configuration tarification réservation"

    def __str__(self):
        return f"Frais de service: {self.service_fee} Ar"

    @classmethod
    def get_solo(cls):
        config = cls.objects.order_by("created_at").first()
        if config:
            return config
        return cls.objects.create(service_fee=5000)


class ReservationServiceQuerySet(models.QuerySet):
    def with_relations(self):
        return self.select_related(
            "reservation",
            "reservation__client",
            "reservation__vehicle",
        )


class ReservationService(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class ServiceType(models.TextChoices):
        ASSURANCE = "ASSURANCE", "Assurance"
        CHAUFFEUR = "CHAUFFEUR", "Chauffeur"
        EQUIPEMENT = "EQUIPEMENT", "Équipement"
        AUTRE = "AUTRE", "Autre"

    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.CASCADE,
        related_name="services",
    )
    service_type = models.CharField(max_length=20, choices=ServiceType.choices)
    service_name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ReservationServiceQuerySet.as_manager()

    def __str__(self):
        return f"{self.service_name} - {self.reservation}"


class ReservationPayment(models.Model):
    class PaymentStatus(models.TextChoices):
        PENDING = "PENDING", "En attente"
        VALIDATED = "VALIDATED", "Validé"
        REJECTED = "REJECTED", "Rejeté"
        REFUNDED = "REFUNDED", "Remboursé"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    reservation = models.OneToOneField(
        Reservation,
        on_delete=models.CASCADE,
        related_name="payment",
    )

    mode = models.ForeignKey(
        ModePayment,
        on_delete=models.SET_NULL,
        null=True,
        related_name="payments",
    )

    reason = models.CharField(max_length=255, db_index=True)

    proof_image = models.ImageField(
        upload_to="payments/proofs/",
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )

    processed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="validated_payments",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment {self.id} - {self.status}"


from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from vehicule.models import VehicleAvailability


@receiver(post_save, sender=Reservation)
def manage_vehicle_availability(sender, instance, created, **kwargs):
    blocking_statuses = [
        Reservation.Status.CONFIRMED,
        Reservation.Status.IN_PROGRESS,
    ]

    VehicleAvailability.objects.filter(
        vehicle=instance.vehicle,
        type=VehicleAvailability.AvailabilityType.RESERVED,
        description=f"Reservation {instance.id}",
    ).delete()

    if instance.status in blocking_statuses:
        VehicleAvailability.objects.create(
            vehicle=instance.vehicle,
            start_date=instance.start_datetime.date(),
            end_date=instance.end_datetime.date(),
            type=VehicleAvailability.AvailabilityType.RESERVED,
            description=f"Reservation {instance.id}",
        )


@receiver(post_delete, sender=Reservation)
def delete_vehicle_availability(sender, instance, **kwargs):
    VehicleAvailability.objects.filter(
        vehicle=instance.vehicle,
        type=VehicleAvailability.AvailabilityType.RESERVED,
        description=f"Reservation {instance.id}",
    ).delete()