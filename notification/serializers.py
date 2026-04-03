from rest_framework import serializers
from .models import Notification, TicketNotification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "notification_type",
            "title",
            "body",
            "is_read",
            "created_at",
            "read_at",
            "reservation",
            "vehicle",
            "vehicle_document",
            "action_url",
            "extra_data",
        ]
        read_only_fields = ["id", "created_at", "read_at"]


class TicketNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketNotification
        fields = "__all__"
        read_only_fields = ("id", "created_at")