from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from reservations.models import Reservation
from reviews.models import Review
from users.models import User
from vehicule.models import Category, FuelType, Marque, ModeleVehicule, StatusVehicule, Transmission, Vehicule


class LoyaltyOverviewAPITest(TestCase):
    def setUp(self):
        self.client_api = APIClient()
        self.user = User.objects.create_user(
            email="client@example.com",
            password="Password123!",
            role="CLIENT",
            first_name="Jean",
            last_name="Client",
            phone="0340011223",
            address="Antananarivo",
            cin_number="CIN123",
            email_verified=True,
            is_active=True,
        )
        self.user.cin_photo_recto.name = "cin/recto.png"
        self.user.cin_photo_verso.name = "cin/verso.png"
        self.user.residence_certificate.name = "residence/cert.png"
        self.user.permis_conduire_recto.name = "permis/recto.png"
        self.user.save()

        self.owner = User.objects.create_user(
            email="owner@example.com",
            password="Password123!",
            role="PRESTATAIRE",
            first_name="Owner",
            last_name="Test",
            phone="0340099887",
            email_verified=True,
            is_active=True,
        )

        marque = Marque.objects.create(nom="Toyota")
        modele = ModeleVehicule.objects.create(label="Prado")
        transmission = Transmission.objects.create(nom="Auto")
        fuel = FuelType.objects.create(nom="Diesel")
        category = Category.objects.create(nom="SUV")
        status = StatusVehicule.objects.create(nom="Disponible")
        self.vehicle = Vehicule.objects.create(
            proprietaire=self.owner,
            marque=marque,
            modele=modele,
            transmission=transmission,
            type_carburant=fuel,
            categorie=category,
            statut=status,
            titre="Toyota Land Cruiser Prado",
            description="SUV",
            nombre_places=5,
            nombre_portes=5,
            kilometrage_actuel_km=10000,
            annee=2022,
            montant_caution=500000,
            adresse_localisation="Tana",
            ville='Antananarivo',
        )

        self.reservation = Reservation.objects.create(
            client=self.user,
            vehicle=self.vehicle,
            start_datetime=timezone.now() - timedelta(days=3),
            end_datetime=timezone.now() - timedelta(days=1),
            total_days=2,
            base_amount=200000,
            options_amount=0,
            total_amount=200000,
            caution_amount=500000,
            status=Reservation.Status.COMPLETED,
            with_chauffeur=False,
            pickup_location="Tana",
            dropoff_location="Tana",
        )

        Review.objects.create(
            reservation=self.reservation,
            author=self.user,
            target=self.owner,
            review_type=Review.ReviewType.CLIENT_TO_OWNER,
            rating=5,
            comment="Très bien",
            is_verified=True,
            moderation_status=Review.ModerationStatus.APPROVED,
        )

        self.client_api.force_authenticate(user=self.user)

    def test_loyalty_overview_returns_expected_summary(self):
        response = self.client_api.get("/api/bookings/loyalty/overview/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["points"], 205)
        self.assertEqual(response.data["pointsToNextTier"], 95)
        self.assertEqual(response.data["stats"][0]["value"], "Bronze")
        self.assertEqual(len(response.data["history"]), 3)
        self.assertEqual(response.data["rules"]["profilePoints"], 80)
        self.assertFalse(response.data["rules"]["referralEnabled"])
