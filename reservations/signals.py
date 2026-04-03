import logging

from django.db.models.signals import pre_delete, pre_save, post_save
from django.dispatch import receiver

from .models import Reservation, ReservationPayment
from gasycar.utils import delete_file
from users.models import User
from notification.models import Notification

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


def _cleanup_old_file(instance, field_name: str, model_class):
    if not instance.pk:
        return

    try:
        previous = model_class.objects.get(pk=instance.pk)
    except model_class.DoesNotExist:
        return

    old_file = getattr(previous, field_name)
    new_file = getattr(instance, field_name)

    if old_file and old_file != new_file:
        if hasattr(old_file, "url"):
            delete_file(old_file.url)
        elif hasattr(old_file, "path"):
            delete_file(old_file.path)
        else:
            delete_file(str(old_file))


def send_ws_notification(user_id, notification: Notification):
    channel_layer = get_channel_layer()
    group_name = f"user_{user_id}"

    message_data = {
        "id": str(notification.id),
        "title": notification.title,
        "body": notification.body,
        "type": notification.notification_type,
        "created_at": notification.created_at.isoformat(),
        "is_read": False,
        "reservation": str(notification.reservation.id) if notification.reservation else None,
    }

    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            "type": "notification_message",
            "message": message_data,
        },
    )


def create_notification(user, notification_type, title, body, reservation=None):
    notification = Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        body=body,
        reservation=reservation,
    )
    send_ws_notification(user.id, notification)
    return notification


def get_admin_support_users():
    return User.objects.filter(role__in=["ADMIN", "SUPPORT"], is_active=True)


def notify_many_users(users, notification_type, title, body, reservation=None):
    seen = set()

    for user in users:
        if not user:
            continue
        if user.id in seen:
            continue
        seen.add(user.id)

        create_notification(
            user=user,
            notification_type=notification_type,
            title=title,
            body=body,
            reservation=reservation,
        )


@receiver(pre_save, sender=ReservationPayment)
def reservationpayment_pre_save(sender, instance, **kwargs):
    _cleanup_old_file(instance, "proof_image", ReservationPayment)

    if instance.pk:
        try:
            previous = ReservationPayment.objects.select_related(
                "reservation",
                "reservation__client",
                "reservation__vehicle",
                "reservation__vehicle__proprietaire",
            ).get(pk=instance.pk)
            instance._previous_status = previous.status
        except ReservationPayment.DoesNotExist:
            instance._previous_status = None
    else:
        instance._previous_status = None


@receiver(pre_delete, sender=ReservationPayment)
def reservationpayment_pre_delete(sender, instance, **kwargs):
    if instance.proof_image:
        if hasattr(instance.proof_image, "url"):
            delete_file(instance.proof_image.url)
        elif hasattr(instance.proof_image, "path"):
            delete_file(instance.proof_image.path)
        else:
            delete_file(str(instance.proof_image))


@receiver(pre_save, sender=Reservation)
def reservation_pre_save(sender, instance, **kwargs):
    if instance.pk:
        try:
            previous = Reservation.objects.select_related(
                "client",
                "vehicle",
                "vehicle__proprietaire",
            ).get(pk=instance.pk)
            instance._previous_status = previous.status
        except Reservation.DoesNotExist:
            instance._previous_status = None
    else:
        instance._previous_status = None


@receiver(post_save, sender=Reservation)
def notify_reservation_events(sender, instance, created, **kwargs):
    client = instance.client
    owner = getattr(instance.vehicle, "proprietaire", None)
    admin_support_users = list(get_admin_support_users())

    if created:
        # Client
        create_notification(
            user=client,
            notification_type=Notification.NotificationType.RESERVATION,
            title="Réservation en attente",
            body=(
                f"Votre réservation {instance.reference} pour {instance.vehicle.titre} "
                f"a été reçue et est en attente de traitement."
            ),
            reservation=instance,
        )

        # Prestataire
        if owner:
            create_notification(
                user=owner,
                notification_type=Notification.NotificationType.RESERVATION,
                title="Nouvelle réservation reçue",
                body=(
                    f"Nouvelle demande de réservation {instance.reference} "
                    f"pour votre véhicule {instance.vehicle.titre}."
                ),
                reservation=instance,
            )

        # Admin + Support
        notify_many_users(
            users=admin_support_users,
            notification_type=Notification.NotificationType.RESERVATION,
            title="Nouvelle réservation à suivre",
            body=(
                f"La réservation {instance.reference} a été créée pour "
                f"{instance.vehicle.titre}."
            ),
            reservation=instance,
        )
        return

    previous_status = getattr(instance, "_previous_status", None)
    if previous_status == instance.status:
        return

    if instance.status == Reservation.Status.CONFIRMED:
        create_notification(
            user=client,
            notification_type=Notification.NotificationType.RESERVATION,
            title="Réservation confirmée",
            body=(
                f"Votre réservation {instance.reference} a été confirmée par le prestataire."
            ),
            reservation=instance,
        )

        if owner:
            create_notification(
                user=owner,
                notification_type=Notification.NotificationType.RESERVATION,
                title="Réservation confirmée",
                body=(
                    f"Vous avez confirmé la réservation {instance.reference}."
                ),
                reservation=instance,
            )

        notify_many_users(
            users=admin_support_users,
            notification_type=Notification.NotificationType.RESERVATION,
            title="Réservation confirmée",
            body=f"La réservation {instance.reference} a été confirmée.",
            reservation=instance,
        )

    elif instance.status == Reservation.Status.CANCELLED:
        create_notification(
            user=client,
            notification_type=Notification.NotificationType.RESERVATION,
            title="Réservation annulée",
            body=f"La réservation {instance.reference} a été annulée.",
            reservation=instance,
        )

        if owner:
            create_notification(
                user=owner,
                notification_type=Notification.NotificationType.RESERVATION,
                title="Réservation annulée",
                body=f"La réservation {instance.reference} a été annulée.",
                reservation=instance,
            )

        notify_many_users(
            users=admin_support_users,
            notification_type=Notification.NotificationType.RESERVATION,
            title="Réservation annulée",
            body=f"La réservation {instance.reference} a été annulée.",
            reservation=instance,
        )

    elif instance.status == Reservation.Status.IN_PROGRESS:
        create_notification(
            user=client,
            notification_type=Notification.NotificationType.RESERVATION,
            title="Location démarrée",
            body=f"La réservation {instance.reference} est maintenant en cours.",
            reservation=instance,
        )

        if owner:
            create_notification(
                user=owner,
                notification_type=Notification.NotificationType.RESERVATION,
                title="Location démarrée",
                body=f"La réservation {instance.reference} est maintenant en cours.",
                reservation=instance,
            )

        notify_many_users(
            users=admin_support_users,
            notification_type=Notification.NotificationType.RESERVATION,
            title="Location démarrée",
            body=f"La réservation {instance.reference} est passée en cours.",
            reservation=instance,
        )

    elif instance.status == Reservation.Status.COMPLETED:
        create_notification(
            user=client,
            notification_type=Notification.NotificationType.RESERVATION,
            title="Location terminée",
            body=f"La réservation {instance.reference} est terminée.",
            reservation=instance,
        )

        if owner:
            create_notification(
                user=owner,
                notification_type=Notification.NotificationType.RESERVATION,
                title="Location terminée",
                body=f"La réservation {instance.reference} est terminée.",
                reservation=instance,
            )

        notify_many_users(
            users=admin_support_users,
            notification_type=Notification.NotificationType.RESERVATION,
            title="Location terminée",
            body=f"La réservation {instance.reference} est terminée.",
            reservation=instance,
        )


@receiver(post_save, sender=ReservationPayment)
def notify_payment_events(sender, instance, created, **kwargs):
    reservation = instance.reservation
    client = reservation.client
    owner = getattr(reservation.vehicle, "proprietaire", None)
    admin_support_users = list(get_admin_support_users())
    previous_status = getattr(instance, "_previous_status", None)

    if created:
        # Client
        create_notification(
            user=client,
            notification_type=Notification.NotificationType.PAYMENT,
            title="Paiement soumis",
            body=(
                f"Votre preuve de paiement pour la réservation {reservation.reference} "
                f"a été envoyée avec succès."
            ),
            reservation=reservation,
        )

        # Prestataire
        if owner:
            create_notification(
                user=owner,
                notification_type=Notification.NotificationType.PAYMENT,
                title="Preuve de paiement reçue",
                body=(
                    f"Une preuve de paiement a été soumise pour la réservation "
                    f"{reservation.reference}."
                ),
                reservation=reservation,
            )

        # Admin + Support
        notify_many_users(
            users=admin_support_users,
            notification_type=Notification.NotificationType.PAYMENT,
            title="Paiement à valider",
            body=(
                f"Un paiement a été soumis pour la réservation {reservation.reference}."
            ),
            reservation=reservation,
        )
        return

    if previous_status == instance.status:
        return

    if instance.status == ReservationPayment.PaymentStatus.VALIDATED:
        create_notification(
            user=client,
            notification_type=Notification.NotificationType.PAYMENT,
            title="Paiement validé",
            body=(
                f"Votre paiement pour la réservation {reservation.reference} a été validé."
            ),
            reservation=reservation,
        )

        if owner:
            create_notification(
                user=owner,
                notification_type=Notification.NotificationType.PAYMENT,
                title="Paiement validé",
                body=(
                    f"Le paiement de la réservation {reservation.reference} est validé. "
                    f"Vous pouvez maintenant confirmer la réservation."
                ),
                reservation=reservation,
            )

        notify_many_users(
            users=admin_support_users,
            notification_type=Notification.NotificationType.PAYMENT,
            title="Paiement validé",
            body=f"Le paiement de la réservation {reservation.reference} a été validé.",
            reservation=reservation,
        )

    elif instance.status == ReservationPayment.PaymentStatus.REJECTED:
        create_notification(
            user=client,
            notification_type=Notification.NotificationType.PAYMENT,
            title="Paiement rejeté",
            body=(
                f"Votre paiement pour la réservation {reservation.reference} a été rejeté."
            ),
            reservation=reservation,
        )

        if owner:
            create_notification(
                user=owner,
                notification_type=Notification.NotificationType.PAYMENT,
                title="Paiement rejeté",
                body=(
                    f"Le paiement de la réservation {reservation.reference} a été rejeté."
                ),
                reservation=reservation,
            )

        notify_many_users(
            users=admin_support_users,
            notification_type=Notification.NotificationType.PAYMENT,
            title="Paiement rejeté",
            body=f"Le paiement de la réservation {reservation.reference} a été rejeté.",
            reservation=reservation,
        )

    elif instance.status == ReservationPayment.PaymentStatus.REFUNDED:
        create_notification(
            user=client,
            notification_type=Notification.NotificationType.PAYMENT,
            title="Paiement remboursé",
            body=(
                f"Le paiement de la réservation {reservation.reference} a été remboursé."
            ),
            reservation=reservation,
        )

        if owner:
            create_notification(
                user=owner,
                notification_type=Notification.NotificationType.PAYMENT,
                title="Paiement remboursé",
                body=(
                    f"Le paiement de la réservation {reservation.reference} a été remboursé."
                ),
                reservation=reservation,
            )

        notify_many_users(
            users=admin_support_users,
            notification_type=Notification.NotificationType.PAYMENT,
            title="Paiement remboursé",
            body=f"Le paiement de la réservation {reservation.reference} a été remboursé.",
            reservation=reservation,
        )