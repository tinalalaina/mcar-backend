from rest_framework import serializers

from .models import SupportTicket, TicketMessage, IncidentReport


def is_support_staff(user) -> bool:
    return bool(
        user
        and user.is_authenticated
        and (
            getattr(user, "role", None) in ["ADMIN", "SUPPORT"]
            or getattr(user, "is_staff", False)
        )
    )


class TicketMessageSerializer(serializers.ModelSerializer):
    sender_email = serializers.EmailField(source="sender.email", read_only=True)
    sender_role = serializers.CharField(source="sender.role", read_only=True)
    sender_name = serializers.SerializerMethodField()
    sender_avatar = serializers.SerializerMethodField()

    class Meta:
        model = TicketMessage
        fields = (
            "id",
            "ticket",
            "sender",
            "sender_email",
            "sender_role",
            "sender_name",
            "sender_avatar",
            "message",
            "attachment_url",
            "is_internal",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "sender",
            "sender_email",
            "sender_role",
            "sender_name",
            "sender_avatar",
            "created_at",
            "updated_at",
        )

    def get_sender_name(self, obj):
        full_name = f"{obj.sender.first_name or ''} {obj.sender.last_name or ''}".strip()
        return full_name or obj.sender.email or "Utilisateur"

    def get_sender_avatar(self, obj):
        for attr in ["avatar_url", "image", "profile_photo"]:
            value = getattr(obj.sender, attr, None)
            if value:
                try:
                    return value.url
                except Exception:
                    return str(value)
        return None


class SupportTicketListSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicket
        fields = (
            "id",
            "user",
            "reservation",
            "vehicule",
            "title",
            "description",
            "ticket_type",
            "priority",
            "status",
            "assigned_admin",
            "last_activity_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class SupportTicketDetailSerializer(serializers.ModelSerializer):
    messages = serializers.SerializerMethodField()

    class Meta:
        model = SupportTicket
        fields = (
            "id",
            "user",
            "reservation",
            "vehicule",
            "title",
            "description",
            "ticket_type",
            "priority",
            "status",
            "assigned_admin",
            "last_activity_at",
            "created_at",
            "updated_at",
            "messages",
        )
        read_only_fields = fields

    def get_messages(self, obj):
        request = self.context.get("request")
        qs = obj.messages.select_related("sender").order_by("created_at")

        if not request or not is_support_staff(request.user):
            qs = qs.filter(is_internal=False)

        return TicketMessageSerializer(qs, many=True, context=self.context).data


class SupportTicketCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicket
        fields = (
            "id",
            "title",
            "description",
            "ticket_type",
            "priority",
            "reservation",
            "vehicule",
        )
        read_only_fields = ("id",)

    def validate_title(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Le titre est obligatoire.")
        return value

    def validate_description(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("La description est obligatoire.")
        return value

    def validate(self, attrs):
        reservation = attrs.get("reservation")
        vehicule = attrs.get("vehicule")

        if reservation and vehicule:
            raise serializers.ValidationError(
                "Un ticket doit concerner soit une réservation, soit un véhicule, pas les deux."
            )

        return attrs


class SupportTicketStaffUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicket
        fields = (
            "title",
            "description",
            "ticket_type",
            "priority",
            "status",
            "reservation",
            "vehicule",
            "assigned_admin",
        )

    def validate(self, attrs):
        reservation = attrs.get("reservation")
        vehicule = attrs.get("vehicule")
        assigned_admin = attrs.get("assigned_admin")

        if reservation and vehicule:
            raise serializers.ValidationError(
                "Un ticket doit concerner soit une réservation, soit un véhicule, pas les deux."
            )

        if assigned_admin:
            role = getattr(assigned_admin, "role", None)
            if role not in ["ADMIN", "SUPPORT"] and not getattr(assigned_admin, "is_staff", False):
                raise serializers.ValidationError(
                    {"assigned_admin": "Le ticket doit être assigné à un admin ou à un support."}
                )

        return attrs


class IncidentReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = IncidentReport
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "resolved_at")