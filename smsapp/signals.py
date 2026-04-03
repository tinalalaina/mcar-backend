from .helpsms import send_sms_befiana

from django.db.models.signals import post_save
from django.dispatch import receiver
import logging

# models
from reservations.models import Reservation



# post_save signal to send SMS after a model instance is created
@receiver(post_save, sender=Reservation)
def send_reservation_sms(sender, instance, created, **kwargs):

    if created:
        full_phone = instance.client.phone
        # Strip country code for client phone safely
        phone_client = ""
        if full_phone:
            if full_phone.startswith('+261'):
                phone_client = full_phone.replace('+261', '', 1)
            else:
                phone_client = full_phone.lstrip('+')

        # information de proprietaite

        first_name_property = instance.vehicle.proprietaire.first_name
        last_name_property = instance.vehicle.proprietaire.last_name
        phone_property = instance.vehicle.proprietaire.phone
        full_name_property = f"{first_name_property} {last_name_property}"

        # Message for the owner
        message = f"Une réservation a été créée avec reference {instance.reference} pour votre véhicule et information de proprietaire  {full_name_property} (Tel: {phone_property})."
  
        result = send_sms_befiana(phone_client, message)

        if result.get("success"):
            logging.info(f"SMS de réservation envoyé avec succès à {full_phone}")
        else:
            logging.error(f"Échec de l'envoi du SMS de réservation à {full_phone}: {result.get('error')}")


