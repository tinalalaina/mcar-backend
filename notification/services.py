from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Notification


def _serialize_notification(notification: Notification) -> dict:
    return {
        "id": str(notification.id),
        "notification_type": notification.notification_type,
        "title": notification.title,
        "body": notification.body,
        "is_read": notification.is_read,
        "created_at": notification.created_at.isoformat(),
        "reservation": str(notification.reservation_id) if notification.reservation_id else None,
        "vehicle": str(notification.vehicle_id) if notification.vehicle_id else None,
        "action_url": notification.action_url or "",
        "metadata": notification.metadata or {},
    }


def push_notification(notification: Notification) -> None:
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    async_to_sync(channel_layer.group_send)(
        f"user_{notification.user_id}",
        {
            "type": "notification_message",
            "message": _serialize_notification(notification),
        },
    )


def create_and_push_notification(
    *,
    user,
    notification_type: str,
    title: str,
    body: str,
    reservation=None,
    vehicle=None,
    action_url: str = "",
    metadata: dict | None = None,
):
    notification = Notification.objects.create(
        user=user,
        reservation=reservation,
        vehicle=vehicle,
        notification_type=notification_type,
        title=title,
        body=body,
        action_url=action_url or "",
        metadata=metadata or {},
    )
    push_notification(notification)
    return notification