from django.shortcuts import get_object_or_404
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.timezone import now

from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework.decorators import action

from users.models import User
from notification.models import TicketNotification, Notification
from notification.serializers import TicketNotificationSerializer, NotificationSerializer


@receiver(post_save, sender=User)
def notify_user_creation(sender, instance, created, **kwargs):
    """
    Hook conservé pour d'éventuels traitements de notification.
    """
    if not created:
        return


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "patch", "delete", "post"]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by("-created_at")

    @action(detail=False, methods=["post"])
    def mark_all_read(self, request):
        self.get_queryset().filter(is_read=False).update(
            is_read=True,
            read_at=now(),
        )
        return Response({"status": "success"})

    @action(detail=True, methods=["patch"])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.read_at = now()
        notification.save(update_fields=["is_read", "read_at"])
        return Response(self.get_serializer(notification).data)


class TicketNotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TicketNotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TicketNotification.objects.filter(user=self.request.user).order_by("-created_at")