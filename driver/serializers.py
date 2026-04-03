from rest_framework import serializers
from .models import Driver



class DriverReadSerializer(serializers.ModelSerializer):
    # licenses field removed as it's now part of the model
    full_name = serializers.SerializerMethodField()
    owner_name = serializers.SerializerMethodField()

    class Meta:
        model = Driver
        fields = "__all__"

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    
    def get_owner_name(self, obj):
        if obj.owner:
            return obj.owner.full_name
        return None

class DriverWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "owner")
    
    def validate_user(self, value):
        # Allow null user
        if value is None:
            return None
        # Check if user already has a driver profile (except current instance)
        if Driver.objects.filter(user=value).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise serializers.ValidationError("Cet utilisateur est déjà associé à un chauffeur.")
        return value

    def validate(self, attrs):
        """
        Règle métier: le certificat de résidence a une validité fixe de 3 mois.
        L'utilisateur ne peut pas modifier cette durée manuellement.
        """
        has_issued_date = "residence_issued_date" in attrs
        has_validity_months = "residence_validity_months" in attrs

        if has_issued_date:
            if attrs.get("residence_issued_date"):
                attrs["residence_validity_months"] = 3
            else:
                attrs["residence_validity_months"] = None
        elif has_validity_months:
            # Ignore toute tentative de modification manuelle de la validité
            attrs.pop("residence_validity_months", None)

        return attrs
