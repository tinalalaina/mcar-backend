from decimal import Decimal
import uuid
from typing import Optional

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from .models import (
    Reservation,
    ReservationService,
    ReservationPayment,
    ReservationPricingConfig,
)
from users.serializers import UserProfileSerializer
from vehicule.serializers import VehiculeSerializer, VehicleEquipmentsSerializer
from modepayment.models import ModePayment
from modepayment.serializers import ModePaymentSerializer
from users.models import User
from driver.models import Driver
from driver.serializers import DriverReadSerializer


class ReservationPaymentSerializer(serializers.ModelSerializer):
    reservation = serializers.PrimaryKeyRelatedField(
        queryset=Reservation.objects.all()
    )
    mode = serializers.PrimaryKeyRelatedField(
        queryset=ModePayment.objects.all(), allow_null=True, required=False
    )
    processed_by = serializers.PrimaryKeyRelatedField(read_only=True)

    mode_data = ModePaymentSerializer(source="mode", read_only=True)

    class Meta:
        model = ReservationPayment
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "processed_by")

    def validate_reservation(self, value: Reservation):
        existing_payment = getattr(value, "payment", None)

        if existing_payment and (
            self.instance is None or existing_payment.pk != self.instance.pk
        ):
            raise serializers.ValidationError(
                "Cette réservation a déjà un enregistrement de paiement."
            )

        return value

    def create(self, validated_data):
        return super().create(validated_data)


class ReservationSerializer(serializers.ModelSerializer):
    client = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )
    client_data = UserProfileSerializer(source="client", read_only=True)
    vehicle_data = VehiculeSerializer(source="vehicle", read_only=True)
    payment = ReservationPaymentSerializer(read_only=True)

    driver = serializers.PrimaryKeyRelatedField(read_only=True)
    driver_data = DriverReadSerializer(source="driver", read_only=True)

    equipments_data = VehicleEquipmentsSerializer(
        source="equipments", many=True, read_only=True
    )

    services_data = serializers.SerializerMethodField()

    driving_mode = serializers.ChoiceField(
        choices=Reservation.DrivingMode.choices, required=False
    )
    pricing_zone = serializers.ChoiceField(
        choices=Reservation.PricingZone.choices, required=False
    )
    guest_email = serializers.EmailField(write_only=True, required=False, allow_blank=True)
    guest_phone = serializers.CharField(write_only=True, required=False, allow_blank=True)
    guest_first_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    guest_last_name = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Reservation
        fields = "__all__"
        read_only_fields = (
            "id",
            "reference",
            "status",
            "total_days",
            "created_at",
            "updated_at",
            "base_amount",
            "options_amount",
            "total_amount",
            "driver_source",
            "driver",
        )

    def get_services_data(self, obj):
        services = obj.services.all()
        return ReservationServiceSerializer(services, many=True).data

    def validate(self, attrs):
        if self.instance is None:
            has_client = attrs.get("client") is not None
            has_guest = any(
                attrs.get(field)
                for field in (
                    "guest_email",
                    "guest_phone",
                    "guest_first_name",
                    "guest_last_name",
                )
            )
            if not has_client and not has_guest:
                raise ValidationError(
                    {"client": "Un client existant ou des informations invité sont requis."}
                )

        vehicle = attrs.get("vehicle") or getattr(self.instance, "vehicle", None)
        start_datetime = attrs.get("start_datetime") or getattr(self.instance, "start_datetime", None)
        end_datetime = attrs.get("end_datetime") or getattr(self.instance, "end_datetime", None)

        if start_datetime and end_datetime and end_datetime <= start_datetime:
            raise ValidationError(
                {"end_datetime": "La date de fin doit être après la date de début."}
            )

        if vehicle and start_datetime and end_datetime:
            overlapping_reservations = Reservation.objects.filter(
                vehicle=vehicle,
                status__in=[
                    Reservation.Status.PENDING,
                    Reservation.Status.CONFIRMED,
                    Reservation.Status.IN_PROGRESS,
                ],
                start_datetime__lt=end_datetime,
                end_datetime__gt=start_datetime,
            )
            if self.instance:
                overlapping_reservations = overlapping_reservations.exclude(id=self.instance.id)

            if overlapping_reservations.exists():
                raise ValidationError(
                    {"start_datetime": "Ce véhicule est déjà réservé sur ces dates."}
                )

        return attrs

    def _get_or_create_guest_client(
        self,
        guest_email: Optional[str],
        guest_phone: Optional[str],
        guest_first_name: Optional[str],
        guest_last_name: Optional[str],
    ) -> User:
        normalized_email = guest_email.strip() if guest_email else ""
        normalized_phone = guest_phone.strip() if guest_phone else ""

        user = None
        if normalized_email:
            user = User.objects.filter(email__iexact=normalized_email).first()
        if not user and normalized_phone:
            user = User.objects.filter(phone=normalized_phone).first()

        if user:
            return user

        email = normalized_email or f"guest-{uuid.uuid4()}@guest.local"
        password = User.objects.make_random_password()
        return User.objects.create_user(
            email=email,
            password=password,
            first_name=guest_first_name or "",
            last_name=guest_last_name or "",
            phone=normalized_phone or None,
            role="CLIENT",
            email_verified=True,
            is_active=True,
        )

    def _compute_pricing_data(
        self,
        *,
        vehicle,
        start_datetime,
        end_datetime,
        driving_mode,
        pricing_zone,
        selected_equipments,
    ):
        from .pricing_service import PricingService

        driver_source = Reservation.DriverSource.NONE
        assigned_driver = None
        with_chauffeur = False

        if driving_mode == Reservation.DrivingMode.WITH_DRIVER:
            with_chauffeur = True
            if vehicle.driver:
                driver_source = Reservation.DriverSource.PROVIDER
                assigned_driver = vehicle.driver
            else:
                driver_source = Reservation.DriverSource.ADMIN_POOL
                assigned_driver = None

        pricing_result = PricingService.calculate_amounts(
            vehicle=vehicle,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            pricing_zone=pricing_zone,
            driving_mode=driving_mode,
            driver_source=driver_source,
            assigned_driver=assigned_driver,
            equipments=selected_equipments,
        )

        driver_amount = Decimal(str(pricing_result["driver_amount"]))
        base_amount = Decimal(str(pricing_result["base_amount"]))
        options_amount = Decimal(str(pricing_result["options_amount"]))
        total_amount = Decimal(str(pricing_result["total_amount"]))

        return {
            "driver": assigned_driver,
            "driver_source": driver_source,
            "driving_mode": driving_mode,
            "pricing_zone": pricing_zone,
            "with_chauffeur": with_chauffeur,
            "total_days": pricing_result["days"],
            "base_amount": base_amount,
            "options_amount": options_amount,
            "total_amount": total_amount,
            "caution_amount": vehicle.montant_caution,
            "has_driver_service": driver_amount > 0 and pricing_result["days"] > 0,
            "driver_service_price": (
                driver_amount / pricing_result["days"]
                if driver_amount > 0 and pricing_result["days"] > 0
                else Decimal("0.00")
            ),
            "driver_service_quantity": pricing_result["days"],
        }

    def create(self, validated_data):
        guest_email = validated_data.pop("guest_email", None)
        guest_phone = validated_data.pop("guest_phone", None)
        guest_first_name = validated_data.pop("guest_first_name", None)
        guest_last_name = validated_data.pop("guest_last_name", None)

        selected_equipments = list(validated_data.pop("equipments", []))

        if not validated_data.get("client"):
            validated_data["client"] = self._get_or_create_guest_client(
                guest_email=guest_email,
                guest_phone=guest_phone,
                guest_first_name=guest_first_name,
                guest_last_name=guest_last_name,
            )

        vehicle = validated_data["vehicle"]
        start_datetime = validated_data["start_datetime"]
        end_datetime = validated_data["end_datetime"]
        driving_mode = validated_data.get(
            "driving_mode", Reservation.DrivingMode.SELF_DRIVE
        )
        pricing_zone = validated_data.get(
            "pricing_zone", Reservation.PricingZone.URBAIN
        )

        pricing_data = self._compute_pricing_data(
            vehicle=vehicle,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            driving_mode=driving_mode,
            pricing_zone=pricing_zone,
            selected_equipments=selected_equipments,
        )

        validated_data.update(
            {
                "driver": pricing_data["driver"],
                "driver_source": pricing_data["driver_source"],
                "driving_mode": pricing_data["driving_mode"],
                "pricing_zone": pricing_data["pricing_zone"],
                "with_chauffeur": pricing_data["with_chauffeur"],
                "total_days": pricing_data["total_days"],
                "base_amount": pricing_data["base_amount"],
                "options_amount": pricing_data["options_amount"],
                "total_amount": pricing_data["total_amount"],
                "caution_amount": pricing_data["caution_amount"],
                "status": Reservation.Status.PENDING,
            }
        )

        reservation = super().create(validated_data)

        if selected_equipments:
            reservation.equipments.set(selected_equipments)

        if pricing_data["has_driver_service"]:
            ReservationService.objects.create(
                reservation=reservation,
                service_type=ReservationService.ServiceType.CHAUFFEUR,
                service_name="Chauffeur Pro",
                price=pricing_data["driver_service_price"],
                quantity=pricing_data["driver_service_quantity"],
            )

        return reservation

    def update(self, instance, validated_data):
        selected_equipments = validated_data.pop("equipments", None)

        # Les champs invités n'ont pas à être utilisés en update
        validated_data.pop("guest_email", None)
        validated_data.pop("guest_phone", None)
        validated_data.pop("guest_first_name", None)
        validated_data.pop("guest_last_name", None)

        vehicle = validated_data.get("vehicle", instance.vehicle)
        start_datetime = validated_data.get("start_datetime", instance.start_datetime)
        end_datetime = validated_data.get("end_datetime", instance.end_datetime)
        driving_mode = validated_data.get("driving_mode", instance.driving_mode)
        pricing_zone = validated_data.get("pricing_zone", instance.pricing_zone)

        if selected_equipments is None:
            selected_equipments = list(instance.equipments.all())
        else:
            selected_equipments = list(selected_equipments)

        pricing_data = self._compute_pricing_data(
            vehicle=vehicle,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            driving_mode=driving_mode,
            pricing_zone=pricing_zone,
            selected_equipments=selected_equipments,
        )

        validated_data.update(
            {
                "driver": pricing_data["driver"],
                "driver_source": pricing_data["driver_source"],
                "driving_mode": pricing_data["driving_mode"],
                "pricing_zone": pricing_data["pricing_zone"],
                "with_chauffeur": pricing_data["with_chauffeur"],
                "total_days": pricing_data["total_days"],
                "base_amount": pricing_data["base_amount"],
                "options_amount": pricing_data["options_amount"],
                "total_amount": pricing_data["total_amount"],
                "caution_amount": pricing_data["caution_amount"],
            }
        )

        reservation = super().update(instance, validated_data)
        reservation.equipments.set(selected_equipments)

        chauffeur_services = reservation.services.filter(
            service_type=ReservationService.ServiceType.CHAUFFEUR
        )

        if pricing_data["has_driver_service"]:
            chauffeur_service = chauffeur_services.first()
            if chauffeur_service:
                chauffeur_service.service_name = "Chauffeur Pro"
                chauffeur_service.price = pricing_data["driver_service_price"]
                chauffeur_service.quantity = pricing_data["driver_service_quantity"]
                chauffeur_service.save()
            else:
                ReservationService.objects.create(
                    reservation=reservation,
                    service_type=ReservationService.ServiceType.CHAUFFEUR,
                    service_name="Chauffeur Pro",
                    price=pricing_data["driver_service_price"],
                    quantity=pricing_data["driver_service_quantity"],
                )
        else:
            chauffeur_services.delete()

        return reservation


class ReservationServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReservationService
        fields = "__all__"


class ReservationPricingConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReservationPricingConfig
        fields = ["service_fee", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


class MonthlyReservationStatisticSerializer(serializers.Serializer):
    month = serializers.CharField()
    count = serializers.IntegerField()


class ReservationStatisticsSerializer(serializers.Serializer):
    total_reservations = serializers.IntegerField()
    total_amount_sum = serializers.DecimalField(max_digits=12, decimal_places=2)
    by_status = serializers.DictField(child=serializers.IntegerField())
    reservations_per_month = MonthlyReservationStatisticSerializer(many=True)


class DailyIncomeSerializer(serializers.Serializer):
    date = serializers.DateField()
    total_income = serializers.DecimalField(max_digits=12, decimal_places=2)
