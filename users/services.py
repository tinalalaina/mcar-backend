from datetime import timedelta, datetime
import secrets
import string

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken as JWTRefreshToken

from .models import (
    OTPCode,
    PendingRegistration,
    RefreshToken as RefreshTokenModel,
    User,
    PasswordResetSession,
)


class OTPService:
    @staticmethod
    def generate_code():
        length = int(getattr(settings, "OTP_LENGTH", 6))
        return "".join(secrets.choice(string.digits) for _ in range(length))

    @staticmethod
    def get_expiry_time():
        return timezone.now() + timedelta(
            minutes=int(getattr(settings, "OTP_VALIDITY_MINUTES", 10))
        )

    @classmethod
    def upsert_pending_registration(cls, validated_data):
        email = validated_data["email"].strip().lower()

        if User.objects.filter(email=email, email_verified=True).exists():
            raise ValueError("Un compte avec cet email existe déjà.")

        pending, _ = PendingRegistration.objects.update_or_create(
            email=email,
            defaults={
                "password_hash": make_password(validated_data["password"]),
                "first_name": validated_data["first_name"].strip(),
                "last_name": validated_data["last_name"].strip(),
                "phone": validated_data.get("phone"),
                "role": validated_data.get("role", "CLIENT"),
                "otp_code": cls.generate_code(),
                "otp_expires_at": cls.get_expiry_time(),
            },
        )
        return pending

    @classmethod
    def resend_pending_registration_otp(cls, email: str):
        email = email.strip().lower()

        if User.objects.filter(email=email, email_verified=True).exists():
            raise ValueError("Ce compte est déjà vérifié.")

        pending = PendingRegistration.objects.filter(email=email).first()
        if not pending:
            raise ValueError("Aucune inscription en attente pour cet email.")

        pending.otp_code = cls.generate_code()
        pending.otp_expires_at = cls.get_expiry_time()
        pending.save(update_fields=["otp_code", "otp_expires_at", "updated_at"])
        return pending

    @staticmethod
    def send_registration_otp_email(pending: PendingRegistration):
        subject = "Code de vérification de votre compte"
        message = (
            f"Bonjour {pending.first_name},\n\n"
            f"Votre code de vérification est : {pending.otp_code}\n\n"
            f"Ce code expire dans {getattr(settings, 'OTP_VALIDITY_MINUTES', 10)} minutes.\n\n"
            f"Madagasycar"
        )

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[pending.email],
            fail_silently=False,
        )

    @staticmethod
    def verify_registration_otp(email: str, code: str):
        email = email.strip().lower()
        code = str(code).strip()

        pending = PendingRegistration.objects.filter(email=email).first()
        if not pending:
            raise ValueError("Aucune inscription en attente pour cet email.")

        if timezone.now() >= pending.otp_expires_at:
            raise ValueError("Code OTP expiré.")

        if pending.otp_code != code:
            raise ValueError("Code OTP invalide.")

        with transaction.atomic():
            existing_user = User.objects.filter(email=email).first()

            if existing_user and existing_user.email_verified:
                pending.delete()
                raise ValueError("Ce compte est déjà vérifié.")

            if existing_user and not existing_user.email_verified:
                user = existing_user
                user.first_name = pending.first_name
                user.last_name = pending.last_name
                user.phone = pending.phone
                user.role = pending.role
                user.password = pending.password_hash
                user.is_active = True
                user.email_verified = True
                user.is_staff = (
                    False if user.role in ["CLIENT", "PRESTATAIRE"] else user.is_staff
                )
                user.save()
            else:
                user = User.objects.create(
                    email=pending.email,
                    first_name=pending.first_name,
                    last_name=pending.last_name,
                    phone=pending.phone,
                    role=pending.role,
                    password=pending.password_hash,
                    is_active=True,
                    email_verified=True,
                    is_staff=False if pending.role in ["CLIENT", "PRESTATAIRE"] else True,
                )

            pending.delete()
            return user

    @classmethod
    def create_otp(cls, user: User, purpose: str) -> OTPCode:
        OTPCode.objects.filter(
            user=user,
            purpose=purpose,
            is_used=False,
        ).update(is_used=True)

        return OTPCode.objects.create(
            user=user,
            code=cls.generate_code(),
            purpose=purpose,
            expires_at=cls.get_expiry_time(),
            is_used=False,
        )

    @staticmethod
    def send_otp_email(user: User, code: str, purpose: str):
        if purpose == "email_verification":
            subject = "Code de vérification de votre compte"
            message = (
                f"Bonjour {user.first_name or ''},\n\n"
                f"Votre code de vérification est : {code}\n\n"
                f"Ce code expire dans {getattr(settings, 'OTP_VALIDITY_MINUTES', 10)} minutes.\n\n"
                f"Madagasycar"
            )
        elif purpose == "password_reset":
            subject = "Code de réinitialisation de mot de passe"
            message = (
                f"Bonjour {user.first_name or ''},\n\n"
                f"Votre code de réinitialisation est : {code}\n\n"
                f"Ce code expire dans {getattr(settings, 'OTP_VALIDITY_MINUTES', 10)} minutes.\n\n"
                f"Madagasycar"
            )
        else:
            raise ValueError("Purpose OTP invalide.")

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

    @staticmethod
    def verify_otp(email: str, code: str, purpose: str):
        email = email.strip().lower()
        code = str(code).strip()
        purpose = purpose.strip()

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise ValueError("Utilisateur introuvable.")

        otp = (
            OTPCode.objects.filter(
                user=user,
                purpose=purpose,
                code=code,
                is_used=False,
            )
            .order_by("-created_at")
            .first()
        )

        if not otp:
            raise ValueError("Code OTP invalide.")

        if timezone.now() >= otp.expires_at:
            otp.is_used = True
            otp.save(update_fields=["is_used"])
            raise ValueError("Code OTP expiré.")

        otp.is_used = True
        otp.save(update_fields=["is_used"])

        if purpose == "email_verification":
            user.email_verified = True
            user.is_active = True
            user.save(update_fields=["email_verified", "is_active"])

        return user

    @classmethod
    def create_password_reset_session(cls, user: User):
        PasswordResetSession.objects.filter(
            user=user,
            is_used=False,
        ).update(is_used=True)

        return PasswordResetSession.objects.create(
            user=user,
            token=secrets.token_urlsafe(48),
            expires_at=timezone.now() + timedelta(minutes=15),
            is_used=False,
        )

    @staticmethod
    def consume_password_reset_session(email: str, reset_token: str):
        email = email.strip().lower()
        reset_token = reset_token.strip()

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise ValueError("Utilisateur introuvable.")

        session = (
            PasswordResetSession.objects.filter(
                user=user,
                token=reset_token,
                is_used=False,
            )
            .order_by("-created_at")
            .first()
        )

        if not session:
            raise ValueError("Session de réinitialisation invalide.")

        if timezone.now() >= session.expires_at:
            session.is_used = True
            session.save(update_fields=["is_used"])
            raise ValueError("Session de réinitialisation expirée.")

        session.is_used = True
        session.save(update_fields=["is_used"])

        return user


class TokenService:
    @staticmethod
    def create_refresh_token(user: User, token: str):
        try:
            jwt_token = JWTRefreshToken(token)
            exp_timestamp = jwt_token["exp"]
            expires_at = datetime.fromtimestamp(
                exp_timestamp,
                tz=timezone.get_current_timezone(),
            )
        except Exception:
            expires_at = timezone.now() + timedelta(minutes=15)

        return RefreshTokenModel.objects.create(
            user=user,
            token=token,
            expires_at=expires_at,
            is_blacklisted=False,
        )

    @staticmethod
    def blacklist_refresh_token(token: str):
        RefreshTokenModel.objects.filter(token=token).update(is_blacklisted=True)

    @staticmethod
    def is_refresh_token_valid(token: str) -> bool:
        try:
            JWTRefreshToken(token)
        except Exception:
            return False

        stored = RefreshTokenModel.objects.filter(token=token).first()
        if stored is None:
            return True

        return stored.is_valid()