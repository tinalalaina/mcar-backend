# apps/reviews/serializers.py
from rest_framework import serializers
from .models import Review
from reservations.models import Reservation


from django.contrib.auth import get_user_model

User = get_user_model()


class ReviewAuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "image"]


class ReviewSerializer(serializers.ModelSerializer):
    author_details = ReviewAuthorSerializer(source="author", read_only=True)

    class Meta:
        model = Review
        fields = "__all__"
        read_only_fields = (
            "author",
            "is_verified",
            "moderation_status",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)

        reservation = attrs.get("reservation") or getattr(self.instance, "reservation", None)
        review_type = attrs.get("review_type") or getattr(self.instance, "review_type", None)
        target = attrs.get("target") or getattr(self.instance, "target", None)

        if reservation is None:
            raise serializers.ValidationError(
                {"reservation": "Un avis doit obligatoirement être lié à une réservation réelle."}
            )

        allowed_statuses = {Reservation.Status.COMPLETED}
        if reservation.status not in allowed_statuses:
            raise serializers.ValidationError(
                {"reservation": "Vous pouvez laisser un avis uniquement pour une réservation terminée."}
            )

        if not user or not user.is_authenticated:
            raise serializers.ValidationError({"detail": "Authentification requise."})

        owner = reservation.vehicle.proprietaire
        client = reservation.client

        if review_type == Review.ReviewType.CLIENT_TO_OWNER:
            if user.id != client.id:
                raise serializers.ValidationError(
                    {"review_type": "Seul le client de cette réservation peut noter le propriétaire."}
                )
            if not target or target.id != owner.id:
                raise serializers.ValidationError(
                    {"target": "La cible doit être le propriétaire du véhicule réservé."}
                )
        elif review_type == Review.ReviewType.OWNER_TO_CLIENT:
            if user.id != owner.id:
                raise serializers.ValidationError(
                    {"review_type": "Seul le propriétaire du véhicule peut noter ce client."}
                )
            if not target or target.id != client.id:
                raise serializers.ValidationError(
                    {"target": "La cible doit être le client de la réservation."}
                )

        return attrs

    def create(self, validated_data):
        validated_data["is_verified"] = True
        validated_data["moderation_status"] = Review.ModerationStatus.PENDING
        return super().create(validated_data)
