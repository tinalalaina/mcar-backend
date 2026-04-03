from django.core.management.base import BaseCommand
from vehicule.models import Marque, Category, Transmission, FuelType, StatusVehicule, ModeleVehicule
import random

class Command(BaseCommand):
    help = "Remplit la base avec des données de référence véhicules (marques, modèles, etc.)"

    def handle(self, *args, **kwargs):
        # Marques et modèles associés
        marques_modeles = {
            "Toyota": ["Corolla", "Yaris", "Rav4", "Hilux", "Land Cruiser"],
            "Peugeot": ["208", "308", "3008", "5008"],
            "Renault": ["Clio", "Captur", "Kadjar", "Duster"],
            "Hyundai": ["i10", "i20", "Kona", "Tucson", "Santa Fe"],
            "Ford": ["Fiesta", "Focus", "Kuga", "Ranger"],
            "BMW": ["X1", "X3", "X5", "Série 1", "Série 3"],
            "Mercedes": ["Classe A", "Classe C", "GLA", "GLC"],
            "Volkswagen": ["Polo", "Golf", "Tiguan", "Touareg"],
            "Kia": ["Picanto", "Ceed", "Sportage", "Sorento"],
            "Dacia": ["Sandero", "Logan", "Duster"],
        }

        marque_objs = {}
        for marque_nom, modeles in marques_modeles.items():
            marque_obj, _ = Marque.objects.get_or_create(nom=marque_nom)
            marque_objs[marque_nom] = marque_obj
            for modele_label in modeles:
                ModeleVehicule.objects.get_or_create(label=modele_label)

        # Catégories principales et sous-catégories
        cat_data = {
            "Voiture": ["Citadine", "Berline", "Break", "Coupé", "4x4", "SUV", "Utilitaire"],
            "Moto": ["Scooter", "Trail", "Routière", "Sportive"],
            "Camion": ["Semi-remorque", "Fourgon", "Ben", "Pick-up"],
        }

        for cat_principale, sous_cats in cat_data.items():
            parent_cat, _ = Category.objects.get_or_create(nom=cat_principale)
            for sous_cat in sous_cats:
                Category.objects.get_or_create(nom=sous_cat, parent=parent_cat)

        # Transmissions
        transmissions = ["Manuelle", "Automatique", "Semi-automatique", "CVT", "Double embrayage"]
        for nom in transmissions:
            Transmission.objects.get_or_create(nom=nom)

        # Carburants
        fuels = ["Essence", "Diesel", "Électrique", "Hybride", "GPL", "GNV", "Hydrogène"]
        for nom in fuels:
            FuelType.objects.get_or_create(nom=nom)

        # Statuts véhicules
        statuts = ["Disponible", "En location", "Maintenance", "Hors service", "Réservé", "Nettoyage"]
        for nom in statuts:
            StatusVehicule.objects.get_or_create(nom=nom)

        self.stdout.write(self.style.SUCCESS("✔ Données enrichies de véhicules insérées avec succès."))
