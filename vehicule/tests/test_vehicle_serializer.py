from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from vehicule.models import Vehicule, VehiclePricing
from vehicule.serializers import VehiculeSerializer

User = get_user_model()

class VehiculeSerializerTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", email="owner@test.com", password="password")

    def test_create_vehicle_with_legacy_pricing(self):
        """Test creating a vehicle using flat pricing fields creates VehiclePricing(URBAIN)"""
        data = {
            "proprietaire": self.owner.id,
            "titre": "Legacy Creation Car",
            "annee": 2022,
            "prix_jour": "100000.00",
            "prix_heure": "5000.00",
            "remise_par_jour": "10.00",
            # Required fields
            "adresse_localisation": "Tana",
            "type_vehicule": "TOURISME"
        }
        
        serializer = VehiculeSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        vehicle = serializer.save()
        
        # Verify Vehicle Created
        self.assertEqual(vehicle.titre, "Legacy Creation Car")
        
        # Verify Pricing Created
        pricing = VehiclePricing.objects.get(vehicle=vehicle, zone_type="URBAIN")
        self.assertEqual(pricing.prix_jour, Decimal("100000.00"))
        self.assertEqual(pricing.prix_heure, Decimal("5000.00"))
        self.assertEqual(pricing.remise_par_jour, Decimal("10.00"))

    def test_update_vehicle_with_legacy_pricing(self):
        """Test updating a vehicle with flat fields updates VehiclePricing"""
        # Create initial
        vehicle = Vehicule.objects.create(proprietaire=self.owner, titre="Update Car", prix_jour=0) # prix_jour dummy
        pricing = VehiclePricing.objects.create(vehicle=vehicle, zone_type="URBAIN", prix_jour=Decimal("50000.00"))
        
        data = {
            "prix_jour": "75000.00",
            "remise_par_mois": "15.00"
        }
        
        serializer = VehiculeSerializer(instance=vehicle, data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        
        pricing.refresh_from_db()
        self.assertEqual(pricing.prix_jour, Decimal("75000.00"))
        self.assertEqual(pricing.remise_par_mois, Decimal("15.00"))
