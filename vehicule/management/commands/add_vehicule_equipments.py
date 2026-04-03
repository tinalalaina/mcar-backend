from django.core.management.base import BaseCommand
from vehicule.models import VehicleEquipments

class Command(BaseCommand):
    help = "Ajoute les équipements de véhicules standards dans la base de données"

    def handle(self, *args, **kwargs):
        equipments = [
            # Sécurité
            ("ABS", "ABS", "Système antiblocage des roues"),
            ("ESP", "Contrôle de stabilité", "Programme électronique de stabilité"),
            ("AIRBAG", "Airbags", "Airbags avant, latéraux ou rideaux"),
            ("AIDE_FREINAGE", "Aide au freinage", "Assistance au freinage d’urgence"),

            # Confort
            ("CLIM_AUTO", "Climatisation automatique", "Climatisation multi-zone"),
            ("CLIM_MANU", "Climatisation manuelle", "Contrôle manuel de la climatisation"),
            ("GPS", "GPS intégré", "Système de navigation embarqué"),
            ("REGUL_VITESSE", "Régulateur de vitesse", "Maintient la vitesse constante"),
            ("LIMITEUR_VITESSE", "Limiteur de vitesse", "Empêche de dépasser une vitesse définie"),
            ("VOLANT_CUIR", "Volant cuir", "Volant garni cuir premium"),
            ("SIEGES_CHAUFFANTS", "Sièges chauffants", "Sièges avant chauffants"),
            ("SIEGES_REGL", "Sièges réglables", "Réglages électriques ou manuels"),
            ("DEMARREUR_SANS_CLE", "Démarrage sans clé", "Keyless start"),

            # Divertissement
            ("BLUETOOTH", "Bluetooth", "Connexion sans fil pour téléphone"),
            ("USB", "Port USB", "Prise USB pour recharge et données"),
            ("AUDIO_PREMIUM", "Système audio premium", "Haut-parleurs renforcés"),

            # Extérieur
            ("PHARES_LED", "Phares LED", "Éclairage LED haute luminosité"),
            ("ANTI_BROUILLARD", "Feux antibrouillard", "Améliore la visibilité"),
            ("ROUE_SECOURS", "Roue de secours", "Roue de secours complète ou galette"),
            ("ATTELAGE", "Attelage", "Crochet de remorque"),

            # Aides à la conduite
            ("CAMERA_RECUL", "Caméra de recul", "Caméra arrière pour assistance stationnement"),
            ("RADAR_AV", "Radars avant", "Capteurs de proximité avant"),
            ("RADAR_AR", "Radars arrière", "Capteurs de proximité arrière"),
            ("AIDE_DEMARRAGE_COTE", "Aide démarrage en côte", "Hill assist"),
            ("MAINTIEN_VOIE", "Alerte maintien de voie", "Lane assist"),
            ("SURVEILLANCE_ANGLE_MORT", "Angle mort", "Détection d’angle mort"),
            ("PILOTAGE_AUTO", "Conduite assistée", "Pilotage semi-automatique selon modèles"),

            # Off-road / Utilitaire
            ("4X4", "Transmission 4x4", "Meilleure motricité sur terrains difficiles"),
            ("PROTECTION_SOUS_BASSE", "Protection sous-bassement", "Protection renforcée off-road"),
            ("PORTE_BAGAGES", "Porte-bagages", "Barres ou galerie"),
            ("COFFRE_TOIT", "Coffre de toit", "Coffre rigide supplémentaire"),

            # High-tech
            ("ANDROID_AUTO", "Android Auto", "Support Android Auto"),
            ("APPLE_CARPLAY", "Apple CarPlay", "Support CarPlay"),
            ("CHARGEUR_INDUCT", "Chargeur induction", "Chargeur sans fil pour smartphone"),
        ]

        inserted_count = 0

        for code, label, description in equipments:
            obj, created = VehicleEquipments.objects.get_or_create(
                code=code,
                defaults={
                    "label": label,
                    "description": description
                }
            )
            if created:
                inserted_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"✔ {inserted_count} équipements insérés avec succès.")
        )
