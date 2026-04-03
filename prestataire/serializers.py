from rest_framework import serializers
from .models import Prestataire
from users.serializers import validate_uploaded_image_file, normalize_mg_phone


class PrestataireSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prestataire
        fields = "__all__"
        read_only_fields = (
            "id",
            "user",
            "status",
            "validated_by",
            "created_at",
            "updated_at",
        )

    def validate_logo(self, value):
        return validate_uploaded_image_file(value, "logo")

    def validate_nif_document(self, value):
        return validate_uploaded_image_file(value, "nif_document")

    def validate_stat_document(self, value):
        return validate_uploaded_image_file(value, "stat_document")

    def validate_rcs_document(self, value):
        return validate_uploaded_image_file(value, "rcs_document")

    def validate_cif_document(self, value):
        return validate_uploaded_image_file(value, "cif_document")

    def validate_phone(self, value):
        return normalize_mg_phone(value)

    def validate_secondary_phone(self, value):
        return normalize_mg_phone(value)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["phone"] = normalize_mg_phone(data.get("phone"))
        data["secondary_phone"] = normalize_mg_phone(data.get("secondary_phone"))
        return data