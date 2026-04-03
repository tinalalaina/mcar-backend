from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
import uuid
from django.utils import timezone
from django.utils.crypto import get_random_string


class CustomUserManager(BaseUserManager):
    def make_random_password(self, length=12, allowed_chars=None):
        if allowed_chars is None:
            allowed_chars = (
                "abcdefghijklmnopqrstuvwxyz"
                "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                "0123456789"
            )
        return get_random_string(length=length, allowed_chars=allowed_chars)

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("L'email est obligatoire")

        email = self.normalize_email(email).lower().strip()
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_active", False)
        extra_fields.setdefault("email_verified", False)
        extra_fields.setdefault("is_company", False)

        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("email_verified", True)
        extra_fields.setdefault("is_company", False)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Le superuser doit avoir is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Le superuser doit avoir is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
        ("CLIENT", "Client"),
        ("PRESTATAIRE", "Prestataire"),
        ("ADMIN", "Administrateur"),
        ("SUPPORT", "Support"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="CLIENT")
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)

    # mémorise le choix "Êtes-vous une entreprise ?"
    is_company = models.BooleanField(default=False)

    first_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50, blank=True)
    cin_number = models.CharField(max_length=50, blank=True, null=True)

    cin_photo_recto = models.ImageField(
        upload_to="cin/photos/recto/",
        blank=True,
        null=True
    )
    cin_photo_verso = models.ImageField(
        upload_to="cin/photos/verso/",
        blank=True,
        null=True
    )
    residence_certificate = models.ImageField(
        upload_to="residence/certificates/",
        blank=True,
        null=True
    )
    permis_conduire = models.ImageField(
        upload_to="permis/photos/",
        blank=True,
        null=True
    )
    permis_conduire_recto = models.ImageField(
        upload_to="permis/photos/recto/",
        blank=True,
        null=True
    )
    permis_conduire_verso = models.ImageField(
        upload_to="permis/photos/verso/",
        blank=True,
        null=True
    )

    image = models.ImageField(upload_to="profile/photos/", blank=True, null=True)

    address = models.TextField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    nif = models.CharField(max_length=100, blank=True, null=True)
    stat = models.CharField(max_length=100, blank=True, null=True)

    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "users"

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


class PendingRegistration(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    password_hash = models.CharField(max_length=128)

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    phone = models.CharField(max_length=20, blank=True, null=True)
    role = models.CharField(max_length=20, choices=User.ROLE_CHOICES, default="CLIENT")

    otp_code = models.CharField(max_length=6)
    otp_expires_at = models.DateTimeField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pending_registrations"
        indexes = [
            models.Index(fields=["email"]),
        ]

    def is_otp_valid(self, code: str) -> bool:
        return (
            self.otp_code == str(code).strip()
            and timezone.now() < self.otp_expires_at
        )


class OTPCode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="otp_codes")
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=50)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "otp_codes"
        indexes = [
            models.Index(fields=["user", "purpose", "is_used"]),
        ]

    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at


class RefreshToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="refresh_tokens")
    token = models.CharField(max_length=500, unique=True)
    expires_at = models.DateTimeField()
    is_blacklisted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "refresh_tokens"
        indexes = [
            models.Index(fields=["user", "is_blacklisted"]),
        ]

    def is_valid(self):
        return not self.is_blacklisted and timezone.now() < self.expires_at


class PasswordResetSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="password_reset_sessions")
    token = models.CharField(max_length=128, unique=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "password_reset_sessions"
        indexes = [
            models.Index(fields=["user", "is_used"]),
            models.Index(fields=["token"]),
        ]

    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at