from django.test import TestCase
from vehicule.models import Vehicule, VehiclePricing
from vehicule.serializers import VehiculeSerializer
from django.contrib.auth import get_user_model

User = get_user_model()

class VehiculeSerializerDualTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="testowner", role="PRESTATAIRE")
        self.data = {
            "proprietaire": self.user.id,
            "titre": "Test Valid",
            "marque": "Toyota",
            "modele": "RAV4",
            "annee": 2020,
            "numero_immatriculation": "1234TBA",
            "numero_serie": "XYZ123",
            "categorie": "SUV",
            "transmission": "Manuelle",
            "type_carburant": "Diesel",
            "type_vehicule": "TOURISME",
            "nombre_places": 5,
            "nombre_portes": 4,
            "couleur": "Noir",
            "kilometrage_actuel_km": 50000,
            "adresse_localisation": "Tana",
            "ville": "Antananarivo",
            "zone": "Centre",
            "est_disponible": True,
            "description": "Belle voiture",
            "conditions_particulieres": "Non fumeur",
            "nombre_locations": 0,
            "nombre_favoris": 0,
            "devise": "Ar",
            "montant_caution": "100000",
            
            # URBAIN PRICING
            "prix_jour": "100000",
            
            # PROVINCE PRICING
            "province_prix_jour": "150000",
            "province_prix_par_semaine": "900000"
        }

    def test_create_dual_pricing(self):
        serializer = VehiculeSerializer(data=self.data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        vehicule = serializer.save()
        
        # Verify Urbain
        urbain = VehiclePricing.objects.get(vehicle=vehicule, zone_type="URBAIN")
        self.assertEqual(urbain.prix_jour, 100000)
        
        # Verify Province
        province = VehiclePricing.objects.get(vehicle=vehicule, zone_type="PROVINCE")
        self.assertEqual(province.prix_jour, 150000)
        self.assertEqual(province.prix_par_semaine, 900000)
        
    def test_update_dual_pricing(self):
        serializer = VehiculeSerializer(data=self.data)
        serializer.is_valid()
        vehicule = serializer.save()
        
        update_data = {
            "province_prix_jour": "160000"
        }
        
        serializer = VehiculeSerializer(vehicule, data=update_data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        
        province = VehiclePricing.objects.get(vehicle=vehicule, zone_type="PROVINCE")
        self.assertEqual(province.prix_jour, 160000)
