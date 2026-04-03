from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import SupportTicket, TicketMessage
from notification.models import TicketNotification


@receiver(post_save, sender=TicketMessage)
def on_new_ticket_message(sender, instance: TicketMessage, created, **kwargs):
    if not created:
        return

    ticket = instance.ticket
    ticket.mark_activity()

    channel_layer = get_channel_layer()
    targets = []

    if instance.sender == ticket.user:
        if ticket.assigned_admin:
            targets.append(ticket.assigned_admin)
    else:
        targets.append(ticket.user)

    for user in targets:
        notif = TicketNotification.objects.create(
            user=user,
            ticket=ticket,
            type=TicketNotification.NotificationType.NEW_MESSAGE,
            title=f"Nouveau message sur le ticket {ticket.title}",
            message=instance.message[:200],
        )

        async_to_sync(channel_layer.group_send)(
            f"user_{user.id}",
            {
                "type": "ticket_notification",
                "event": "NEW_MESSAGE",
                "data": {
                    "ticket_id": str(ticket.id),
                    "notification_id": str(notif.id),
                    "title": notif.title,
                    "message": notif.message,
                },
            },
        )

    async_to_sync(channel_layer.group_send)(
        f"ticket_{ticket.id}",
        {
            "type": "ticket_message",
            "event": "NEW_TICKET_MESSAGE",
            "data": {
                "id": str(instance.id),
                "ticket_id": str(ticket.id),
                "sender": str(instance.sender.id),
                "sender_id": str(instance.sender.id),
                "sender_email": instance.sender.email,
                "message": instance.message,
                "is_internal": instance.is_internal,
                "attachment_url": instance.attachment_url,
                "created_at": instance.created_at.isoformat(),
                "updated_at": instance.updated_at.isoformat(),
            },
        },
    )


@receiver(pre_save, sender=SupportTicket)
def on_ticket_status_change(sender, instance: SupportTicket, **kwargs):
    if not instance.pk:
        return

    try:
        old = SupportTicket.objects.get(pk=instance.pk)
    except SupportTicket.DoesNotExist:
        return

    if old.status != instance.status:
        channel_layer = get_channel_layer()

        targets = [instance.user]
        if instance.assigned_admin:
            targets.append(instance.assigned_admin)

        sent_ids = set()

        for user in targets:
            if not user or user.id in sent_ids:
                continue
            sent_ids.add(user.id)

            notif = TicketNotification.objects.create(
                user=user,
                ticket=instance,
                type=TicketNotification.NotificationType.STATUS_CHANGED,
                title=f"Statut du ticket mis à jour ({instance.get_status_display()})",
                message=(
                    f"Le ticket « {instance.title} » est maintenant "
                    f"{instance.get_status_display()}."
                ),
            )

            async_to_sync(channel_layer.group_send)(
                f"user_{user.id}",
                {
                    "type": "ticket_notification",
                    "event": "STATUS_CHANGED",
                    "data": {
                        "ticket_id": str(instance.id),
                        "notification_id": str(notif.id),
                        "status": instance.status,
                        "status_label": instance.get_status_display(),
                        "title": notif.title,
                        "message": notif.message,
                    },
                },
            )