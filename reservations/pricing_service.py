from decimal import Decimal
import math

from vehicule.models import Vehicule
from reservations.models import Reservation, ReservationPricingConfig


class PricingService:
    @staticmethod
    def _apply_percentage_discount(amount: Decimal, discount_percent) -> Decimal:
        if discount_percent in (None, ""):
            return amount
        discount = Decimal(str(discount_percent)) / Decimal("100")
        return amount * (Decimal("1.00") - discount)

    @staticmethod
    def calculate_amounts(
        vehicle: Vehicule,
        start_datetime,
        end_datetime,
        pricing_zone=Reservation.PricingZone.URBAIN,
        driving_mode=Reservation.DrivingMode.SELF_DRIVE,
        driver_source=Reservation.DriverSource.NONE,
        assigned_driver=None,
        equipments=None,
    ):
        equipments = equipments or []

        if end_datetime <= start_datetime:
            raise ValueError("La date de fin doit être supérieure à la date de début.")

        duration = end_datetime - start_datetime
        total_seconds = duration.total_seconds()
        days = max(1, math.ceil(total_seconds / 86400))
        hours = max(1, math.ceil(total_seconds / 3600))

        pricing = vehicle.pricing_grid.filter(zone_type=pricing_zone).first()
        if not pricing and pricing_zone == Reservation.PricingZone.PROVINCE:
            raise ValueError("Tarifs province non définis pour ce véhicule.")

        if not pricing:
            pricing = vehicle.pricing_grid.filter(
                zone_type=Reservation.PricingZone.URBAIN
            ).first()

        if not pricing or pricing.prix_jour is None:
            raise ValueError(
                "Aucune grille tarifaire valide n'est configurée pour ce véhicule."
            )

        daily_rate = Decimal(str(pricing.prix_jour))
        base_amount = Decimal("0.00")

        # Location courte (moins de 24h) : on privilégie le tarif horaire s'il existe
        if hours < 24 and pricing.prix_heure:
            hourly_rate = Decimal(str(pricing.prix_heure))
            hourly_rate = PricingService._apply_percentage_discount(
                hourly_rate, pricing.remise_par_heure
            )
            base_amount = hourly_rate * hours
        else:
            weekly_discount_percent = getattr(
                pricing, "remise_par_semaine", None
            ) or pricing.remise_longue_duree_pourcent

            if days >= 30 and pricing.prix_mois:
                months = days // 30
                remaining_days = days % 30
                monthly_rate = Decimal(str(pricing.prix_mois))
                base_amount = (monthly_rate * months) + (
                    daily_rate * remaining_days
                )
                base_amount = PricingService._apply_percentage_discount(
                    base_amount, pricing.remise_par_mois
                )
            elif days >= 7 and pricing.prix_par_semaine:
                weeks = days // 7
                remaining_days = days % 7
                weekly_rate = Decimal(str(pricing.prix_par_semaine))
                base_amount = (weekly_rate * weeks) + (
                    daily_rate * remaining_days
                )
                base_amount = PricingService._apply_percentage_discount(
                    base_amount, weekly_discount_percent
                )
            else:
                discounted_day_rate = PricingService._apply_percentage_discount(
                    daily_rate, pricing.remise_par_jour
                )
                base_amount = discounted_day_rate * days

        driver_amount = Decimal("0.00")
        driver_unit_amount = Decimal("0.00")
        if driving_mode == Reservation.DrivingMode.WITH_DRIVER:
            if driver_source == Reservation.DriverSource.PROVIDER and assigned_driver:
                provider_driver_rate = getattr(assigned_driver, "driver_rate", None)
                if provider_driver_rate not in (None, ""):
                    driver_unit_amount = Decimal(str(provider_driver_rate))
                else:
                    driver_unit_amount = Decimal("40000.00")
            elif driver_source == Reservation.DriverSource.ADMIN_POOL:
                driver_unit_amount = Decimal("50000.00")
            else:
                driver_unit_amount = Decimal("40000.00")
            driver_amount = driver_unit_amount * days

        equipment_amount = sum(
            (Decimal(eq.price or 0) * days for eq in equipments),
            Decimal("0.00"),
        )

        service_fee = ReservationPricingConfig.get_solo().service_fee
        options_amount = driver_amount + equipment_amount
        total_amount = base_amount + options_amount + service_fee

        return {
            "days": days,
            "base_amount": base_amount,
            "driver_amount": driver_amount,
            "driver_unit_amount": driver_unit_amount,
            "equipment_amount": equipment_amount,
            "options_amount": options_amount,
            "service_fee": service_fee,
            "total_amount": total_amount,
        }
