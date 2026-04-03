from django.core.management.base import BaseCommand
from reservations.models import Reservation, generate_reservation_reference


class Command(BaseCommand):
    help = 'Génère les références pour les réservations existantes sans référence'

    def handle(self, *args, **options):
        # Trouver toutes les réservations sans référence
        reservations = Reservation.objects.filter(reference='')
        count = 0
        
        self.stdout.write(f'Trouvé {reservations.count()} réservations sans référence')
        
        for reservation in reservations:
            # Générer une référence unique
            reservation.reference = generate_reservation_reference()
            reservation.save()
            count += 1
            self.stdout.write(f'Référence générée: {reservation.reference} pour réservation {reservation.id}')
        
        self.stdout.write(self.style.SUCCESS(f'{count} références générées avec succès'))
