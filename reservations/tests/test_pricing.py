from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from vehicule.models import Vehicule, VehiclePricing
from reservations.models import Reservation, ReservationService
from reservations.pricing_service import PricingService
from driver.models import Driver

User = get_user_model()

class PricingTest(TestCase):
    def setUp(self):
        # Create Users
        self.owner = User.objects.create_user(username="owner", email="owner@test.com", password="password")
        self.client = User.objects.create_user(username="client", email="client@test.com", password="password")
        self.admin = User.objects.create_superuser(username="admin", email="admin@test.com", password="password")

        # Create Vehicle
        self.vehicle = Vehicule.objects.create(
            proprietaire=self.owner,
            titre="Test Car",
            montant_caution=Decimal("500000.00"),
            annee=2020,
            nombre_places=4,
            nombre_portes=5,
            kilometrage_actuel_km=10000,
            adresse_localisation="Tana",
            ville="Tana",
            zone="URBAIN" # Legacy field
        )

        # Create Pricing Grid
        VehiclePricing.objects.create(
            vehicle=self.vehicle,
            zone_type="URBAIN",
            prix_jour=Decimal("100000.00")
        )
        VehiclePricing.objects.create(
            vehicle=self.vehicle,
            zone_type="PROVINCE",
            prix_jour=Decimal("150000.00")
        )

        # Dates
        self.start = timezone.now()
        self.end = self.start + timedelta(days=2) # 2 days
        
    def test_pricing_urbain_self_drive(self):
        """Test Standard Urban Self-Drive"""
        res = PricingService.calculate_amounts(
            vehicle=self.vehicle,
            start_datetime=self.start,
            end_datetime=self.end,
            pricing_zone=Reservation.PricingZone.URBAIN,
            driving_mode=Reservation.DrivingMode.SELF_DRIVE,
            driver_source=Reservation.DriverSource.NONE
        )
        self.assertEqual(res['base_amount'], Decimal("200000.00")) # 100k * 2
        self.assertEqual(res['driver_amount'], Decimal("0.00"))
        self.assertEqual(res['total_amount'], Decimal("200000.00"))

    def test_pricing_province_self_drive(self):
        """Test Province Self-Drive (Higher rate)"""
        res = PricingService.calculate_amounts(
            vehicle=self.vehicle,
            start_datetime=self.start,
            end_datetime=self.end,
            pricing_zone=Reservation.PricingZone.PROVINCE,
            driving_mode=Reservation.DrivingMode.SELF_DRIVE,
            driver_source=Reservation.DriverSource.NONE
        )
        self.assertEqual(res['base_amount'], Decimal("300000.00")) # 150k * 2
        self.assertEqual(res['total_amount'], Decimal("300000.00"))

    def test_pricing_urbain_with_driver_provider(self):
        """Test Urban with Provider Driver"""
        res = PricingService.calculate_amounts(
            vehicle=self.vehicle,
            start_datetime=self.start,
            end_datetime=self.end,
            pricing_zone=Reservation.PricingZone.URBAIN,
            driving_mode=Reservation.DrivingMode.WITH_DRIVER,
            driver_source=Reservation.DriverSource.PROVIDER
        )
        # 100k * 2 + 40k * 2
        self.assertEqual(res['base_amount'], Decimal("200000.00"))
        self.assertEqual(res['driver_amount'], Decimal("80000.00")) 
        self.assertEqual(res['total_amount'], Decimal("280000.00"))

    def test_pricing_urbain_with_driver_admin_pool(self):
        """Test Urban with Admin Pool Driver (Higher fee)"""
        res = PricingService.calculate_amounts(
            vehicle=self.vehicle,
            start_datetime=self.start,
            end_datetime=self.end,
            pricing_zone=Reservation.PricingZone.URBAIN,
            driving_mode=Reservation.DrivingMode.WITH_DRIVER,
            driver_source=Reservation.DriverSource.ADMIN_POOL
        )
        # 100k * 2 + 50k * 2
        self.assertEqual(res['base_amount'], Decimal("200000.00"))
        self.assertEqual(res['driver_amount'], Decimal("100000.00")) 
        self.assertEqual(res['total_amount'], Decimal("300000.00"))

    def test_reservation_creation_api(self):
        """Test Creating Reservation via API uses logic"""
        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(user=self.client)

        data = {
            "vehicle": self.vehicle.id,
            "start_datetime": self.start.isoformat(),
            "end_datetime": self.end.isoformat(),
            "total_days": 2,
            "base_amount": 100, # Should be ignored/overwritten
            "total_amount": 100, # Should be ignored/overwritten
            "caution_amount": 0,
            "driving_mode": "WITH_DRIVER",
            "pricing_zone": "PROVINCE",
            "client": self.client.id,
            "status": "PENDING",
            "pickup_location": "Tana",
            "dropoff_location": "Tana"
        }
        
        response = client.post("/api/reservations/", data, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        
        res_id = response.data['id']
        reservation = Reservation.objects.get(id=res_id)
        
        # Check Logic Application
        # Zone: PROVINCE -> 150k/day
        # Mode: WITH_DRIVER -> +50k/day (Admin Pool because vehicle has no driver assigned)
        
        # Verify Driver Source Logic
        # Vehicle has no driver -> Should be ADMIN_POOL
        self.assertEqual(reservation.driver_source, Reservation.DriverSource.ADMIN_POOL)
        
        # Verify Amounts
        # Base: 150k * 2 = 300k
        # Driver: 50k * 2 = 100k (Admin Pool rate)
        # Total: 400k
        
        self.assertEqual(reservation.base_amount, Decimal("300000.00"))
        self.assertEqual(reservation.total_amount, Decimal("400000.00"))
        
        # Verify Service Line Created for Driver
        service = ReservationService.objects.get(reservation=reservation, service_type="CHAUFFEUR")
        self.assertEqual(service.price, Decimal("50000.00"))
        self.assertEqual(service.quantity, 2)

