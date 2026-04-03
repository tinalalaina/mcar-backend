import os
import re
from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from django.contrib.auth.password_validation import validate_password

from .models import User
from gasycar.utils import delete_file


ALLOWED_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
}

BLOCKED_EXTENSIONS = {
    ".gif",
    ".mp4",
    ".mp3",
    ".wav",
    ".avi",
    ".mov",
    ".mkv",
    ".pdf",
    ".svg",
}

BLOCKED_CONTENT_TYPES = {
    "image/gif",
    "video/mp4",
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "video/x-msvideo",
    "video/quicktime",
    "application/pdf",
    "image/svg+xml",
}


def normalize_mg_phone(value):
    raw_value = str(value or "").strip()
    if not raw_value:
        return ""

    digits = re.sub(r"\D", "", raw_value)

    if not digits:
        return raw_value

    if digits.startswith("00261"):
        digits = digits[5:]
    elif digits.startswith("261"):
        digits = digits[3:]

    if len(digits) == 10 and digits.startswith("0"):
        return digits

    if len(digits) == 9:
        return f"0{digits}"

    return raw_value


def validate_uploaded_image_file(value, field_name="image"):
    if value in (None, ""):
        return value

    max_size = 10 * 1024 * 1024  # 10 MB
    if value.size > max_size:
        raise serializers.ValidationError(
            f"{field_name} ne doit pas dépasser 10 MB."
        )

    filename = str(getattr(value, "name", "") or "")
    ext = os.path.splitext(filename)[1].lower()
    content_type = str(getattr(value, "content_type", "") or "").lower()

    if ext in BLOCKED_EXTENSIONS or content_type in BLOCKED_CONTENT_TYPES:
        raise serializers.ValidationError(
            f"Format non autorisé pour {field_name}."
        )

    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise serializers.ValidationError(
            f"Format non supporté pour {field_name}. Formats acceptés : JPG, JPEG, PNG, WEBP, BMP, TIFF."
        )

    if content_type and not content_type.startswith("image/"):
        raise serializers.ValidationError(
            f"{field_name} doit être une vraie image."
        )

    return value


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            "email",
            "password",
            "password_confirm",
            "first_name",
            "last_name",
            "phone",
            "role",
        )
        extra_kwargs = {
            "email": {"required": True},
            "first_name": {"required": True},
            "last_name": {"required": True},
            "role": {"required": False},
        }

    def validate_email(self, value):
        email = value.lower().strip()
        existing_verified_user = User.objects.filter(
            email=email,
            email_verified=True
        ).first()

        if existing_verified_user:
            raise serializers.ValidationError(
                "Un compte avec cet email existe déjà."
            )

        return email

    def validate_phone(self, value):
        return normalize_mg_phone(value)

    def validate_role(self, value):
        allowed_roles = ["CLIENT", "PRESTATAIRE"]
        if value not in allowed_roles:
            raise serializers.ValidationError(
                "Le rôle doit être CLIENT ou PRESTATAIRE."
            )
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Les mots de passe ne correspondent pas."}
            )

        if not attrs.get("role"):
            attrs["role"] = "CLIENT"

        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")

        user = User.objects.create_user(password=password, **validated_data)
        user.is_active = False
        user.email_verified = False
        user.is_staff = False if user.role in ["CLIENT", "PRESTATAIRE"] else user.is_staff
        user.save(update_fields=["is_active", "email_verified", "is_staff"])

        return user


class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, attrs):
        email = attrs.get("email", "").lower().strip()
        password = attrs.get("password")

        if email and password:
            user = authenticate(username=email, password=password)
            if not user:
                raise serializers.ValidationError(
                    "Vérifiez votre email ou mot de passe."
                )
            if not user.is_active:
                raise serializers.ValidationError("Compte désactivé ou non vérifié.")
            if not user.email_verified:
                raise serializers.ValidationError(
                    "Veuillez vérifier votre email avant de vous connecter."
                )

            attrs["user"] = user
            return attrs

        raise serializers.ValidationError("Email et mot de passe requis.")


class UserProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "role",
            "is_active",
            "email_verified",
            "phone_verified",
            "is_company",
            "cin_number",
            "cin_photo_recto",
            "cin_photo_verso",
            "residence_certificate",
            "permis_conduire",
            "permis_conduire_recto",
            "permis_conduire_verso",
            "image",
            "address",
            "date_of_birth",
            "nif",
            "stat",
            "date_joined",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "email",
            "role",
            "is_active",
            "email_verified",
            "phone_verified",
            "date_joined",
            "updated_at",
            "full_name",
        )

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["phone"] = normalize_mg_phone(data.get("phone"))
        return data


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "phone",
            "cin_number",
            "address",
            "date_of_birth",
            "nif",
            "stat",
            "is_company",
            "permis_conduire",
            "permis_conduire_recto",
            "permis_conduire_verso",
        )

    def validate_phone(self, value):
        return normalize_mg_phone(value)


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "email",
            "role",
            "is_active",
            "is_company",
            "permis_conduire",
            "permis_conduire_recto",
            "permis_conduire_verso",
        )

    def validate_phone(self, value):
        return normalize_mg_phone(value)


class OTPRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    purpose = serializers.ChoiceField(
        choices=["email_verification", "password_reset"]
    )


class OTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)
    purpose = serializers.ChoiceField(
        choices=["email_verification", "password_reset"]
    )


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()
    reset_token = serializers.CharField(max_length=128)
    new_password = serializers.CharField(min_length=8)
    new_password_confirm = serializers.CharField(min_length=8)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "Les mots de passe ne correspondent pas."}
            )

        validate_password(attrs["new_password"])
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField(min_length=8)
    new_password_confirm = serializers.CharField(min_length=8)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "Les mots de passe ne correspondent pas."}
            )
        return attrs


class CustomTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        try:
            return super().validate(attrs)
        except get_user_model().DoesNotExist:
            raise AuthenticationFailed(
                "Utilisateur introuvable ou supprimé.",
                code="user_not_found"
            )


class UserPhotoUploadSerializer(serializers.Serializer):
    photo = serializers.FileField()

    def validate_photo(self, value):
        return validate_uploaded_image_file(value, "photo")

    def update(self, instance, validated_data):
        if instance.image:
            delete_file(instance.image.path)

        instance.image = validated_data["photo"]
        instance.save(update_fields=["image", "updated_at"])
        return instance