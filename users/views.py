# users/views.py

import logging

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.files.storage import default_storage
from django.db import transaction
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from drf_yasg.utils import swagger_auto_schema

from rest_framework import permissions, status
from rest_framework.decorators import api_view
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import validate_uploaded_image_file
from gasycar.utils import delete_file

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from gasycar.utils import send_email_notification

from .models import OTPCode, User
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserProfileSerializer,
    UserUpdateSerializer,
    AdminUserUpdateSerializer,
    OTPRequestSerializer,
    OTPVerifySerializer,
    PasswordResetSerializer,
    ChangePasswordSerializer,
    CustomTokenRefreshSerializer,
    UserPhotoUploadSerializer,
)
from .services import OTPService, TokenService

logger = logging.getLogger(__name__)

class UserRegistrationView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            pending = OTPService.upsert_pending_registration(serializer.validated_data)
            OTPService.send_registration_otp_email(pending)

            return Response(
                {
                    "message": "Un code de vérification a été envoyé à votre email.",
                    "email": pending.email,
                },
                status=status.HTTP_201_CREATED,
            )
        except ValueError as e:
            return Response(
                {"email": [str(e)]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.exception(
                "Erreur lors de l'inscription avec OTP pour email=%s",
                request.data.get("email"),
            )
            return Response(
                {
                    "detail": "Échec de l'inscription avec OTP.",
                    "error": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

class WithOutUserRegistrationView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            UserProfileSerializer(user, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class UserLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response(
                {"detail": "Email et mot de passe requis."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(request, email=email, password=password)

        if user is None:
            return Response(
                {"detail": "Vérifiez votre email ou mot de passe."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_active:
            return Response(
                {"detail": "Compte inactif."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not user.email_verified:
            return Response(
                {"detail": "Veuillez vérifier votre email avant de vous connecter."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        user_data = UserProfileSerializer(
            user, context={"request": request}
        ).data

        return Response(
            {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": user_data,
            },
            status=status.HTTP_200_OK,
        )

class OTPRequestView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        purpose = serializer.validated_data["purpose"]

        try:
            if purpose == "email_verification":
                pending = OTPService.resend_pending_registration_otp(email)
                OTPService.send_registration_otp_email(pending)
                return Response(
                    {"message": "Code email_verification envoyé avec succès."},
                    status=status.HTTP_200_OK,
                )

            user = User.objects.get(email=email)
            otp = OTPService.create_otp(user, purpose)
            OTPService.send_otp_email(user, otp.code, purpose)

            return Response(
                {"message": f"Code {purpose} envoyé avec succès."},
                status=status.HTTP_200_OK,
            )

        except User.DoesNotExist:
            return Response(
                {"error": "Aucun utilisateur avec cet email."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.exception("Erreur lors de l'envoi OTP pour email=%s", email)
            return Response(
                {
                    "detail": "Impossible d'envoyer le code OTP.",
                    "error": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

class OTPVerifyView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        code = serializer.validated_data["code"]
        purpose = serializer.validated_data["purpose"]

        try:
            if purpose == "email_verification":
                user = OTPService.verify_registration_otp(email=email, code=code)

                response_data = {
                    "message": "Vérification réussie.",
                    "verified": True,
                    "email": user.email,
                    "role": user.role,
                    "user_id": str(user.id),
                }

                refresh = RefreshToken.for_user(user)
                response_data.update(
                    {
                        "access_token": str(refresh.access_token),
                        "refresh_token": str(refresh),
                    }
                )

                return Response(response_data, status=status.HTTP_200_OK)

            if purpose == "password_reset":
                user = OTPService.verify_otp(email=email, code=code, purpose=purpose)
                reset_session = OTPService.create_password_reset_session(user)

                return Response(
                    {
                        "message": "Code vérifié avec succès.",
                        "verified": True,
                        "email": user.email,
                        "reset_token": reset_session.token,
                    },
                    status=status.HTTP_200_OK,
                )

            return Response(
                {"error": "Purpose OTP invalide.", "verified": False},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except ValueError as e:
            return Response(
                {"error": str(e), "verified": False},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.exception("Erreur OTP verify pour email=%s", email)
            return Response(
                {
                    "error": "Erreur serveur pendant la vérification OTP.",
                    "details": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

class PasswordResetView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data["email"]
        reset_token = serializer.validated_data["reset_token"]
        new_password = serializer.validated_data["new_password"]

        try:
            user = OTPService.consume_password_reset_session(email, reset_token)
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save()

        return Response(
            {"message": "Mot de passe réinitialisé avec succès."},
            status=status.HTTP_200_OK,
        )

class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        old_password = serializer.validated_data["old_password"]
        new_password = serializer.validated_data["new_password"]

        if not user.check_password(old_password):
            return Response(
                {"error": "Ancien mot de passe incorrect."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save()

        return Response(
            {"message": "Mot de passe modifié avec succès."},
            status=status.HTTP_200_OK,
        )


class TokenRefreshAllView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        refresh_token = request.data.get("refresh_token")

        if not refresh_token:
            return Response(
                {"error": "Refresh token requis."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not TokenService.is_refresh_token_valid(refresh_token):
            return Response(
                {"error": "Refresh token invalide ou expiré."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            refresh = RefreshToken(refresh_token)
            user_id = refresh["user_id"]
            user = User.objects.get(id=user_id)

            new_refresh = RefreshToken.for_user(user)
            new_access_token = str(new_refresh.access_token)
            new_refresh_token = str(new_refresh)

            TokenService.blacklist_refresh_token(refresh_token)
            TokenService.create_refresh_token(user, new_refresh_token)

            return Response(
                {
                    "access_token": new_access_token,
                    "refresh_token": new_refresh_token,
                },
                status=status.HTTP_200_OK,
            )

        except Exception:
            return Response(
                {"error": "Token invalide."},
                status=status.HTTP_401_UNAUTHORIZED,
            )


class CustomTokenRefreshView(TokenRefreshView):
    serializer_class = CustomTokenRefreshSerializer

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        return response


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh_token")

        if refresh_token:
            TokenService.blacklist_refresh_token(refresh_token)

        return Response(
            {"message": "Déconnexion réussie."},
            status=status.HTTP_200_OK,
        )


class UserListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        users = User.objects.all().order_by("-date_joined")
        serializer = UserProfileSerializer(
            users, many=True, context={"request": request}
        )
        return Response(serializer.data)


class DeleteNonAdminUsersView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        current_user = request.user

        if current_user.role != "ADMIN" and not current_user.is_superuser:
            return Response(
                {"detail": "Accès réservé aux administrateurs."},
                status=status.HTTP_403_FORBIDDEN,
            )

        password = request.data.get("password")
        if not password:
            return Response(
                {"detail": "Le mot de passe administrateur est requis."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not current_user.check_password(password):
            return Response(
                {"detail": "Mot de passe administrateur invalide."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        deleted_count, _ = User.objects.exclude(role="ADMIN").delete()

        return Response(
            {
                "message": "Suppression en masse terminée.",
                "deleted_count": deleted_count,
            },
            status=status.HTTP_200_OK,
        )


@api_view(["POST"])
def signup(request):
    email = request.data.get("email")
    if User.objects.filter(email=email).exists():
        return Response(
            {"error": "Email already exists"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if (
        request.data.get("email") is None
        or request.data.get("password") is None
        or request.data.get("first_name") is None
        or request.data.get("last_name") is None
    ):
        return Response(
            {"error": "All input is request"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = User.objects.create_user(
        email=request.data["email"],
        password=request.data["password"],
        first_name=request.data["first_name"],
        last_name=request.data["last_name"],
        role=request.data["role"],
    )

    if request.data.get("phone"):
        user.phone = request.data.get("phone")

    user.save()

    serializer = UserProfileSerializer(
        user, many=False, context={"request": request}
    )
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@swagger_auto_schema(method="get", operation_description="Get all prestataire users")
@api_view(["GET"])
def get_prestataire_users(request):
    prestataire_users = User.objects.filter(role="PRESTATAIRE")
    serializer = UserProfileSerializer(
        prestataire_users, many=True, context={"request": request}
    )
    return Response(serializer.data, status=status.HTTP_200_OK)


@swagger_auto_schema(method="get", operation_description="Get all client users")
@api_view(["GET"])
def get_client_users(request):
    client_users = User.objects.filter(role="CLIENT")
    serializer = UserProfileSerializer(
        client_users, many=True, context={"request": request}
    )
    return Response(serializer.data, status=status.HTTP_200_OK)


@swagger_auto_schema(method="get", operation_description="Get all support users")
@api_view(["GET"])
def get_support_users(request):
    support_users = User.objects.filter(role="SUPPORT")
    serializer = UserProfileSerializer(
        support_users, many=True, context={"request": request}
    )
    return Response(serializer.data, status=status.HTTP_200_OK)


class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_user(self, request, user_id=None):
        if user_id is None:
            return request.user

        user = get_object_or_404(User, id=user_id)

        if (
            str(request.user.id) != str(user.id)
            and request.user.role != "ADMIN"
            and not request.user.is_superuser
        ):
            return None

        return user

    def _apply_uploaded_files(self, user, request):
        file_fields = [
            "image",
            "cin_photo_recto",
            "cin_photo_verso",
            "residence_certificate",
            "permis_conduire",
            "permis_conduire_recto",
            "permis_conduire_verso",
        ]

        changed = False

        for field_name in file_fields:
            uploaded_file = request.FILES.get(field_name)

            if uploaded_file:
                validate_uploaded_image_file(uploaded_file, field_name)

                old_file = getattr(user, field_name, None)
                if old_file and getattr(old_file, "name", None):
                    try:
                        delete_file(old_file.path)
                    except Exception:
                        pass

                setattr(user, field_name, uploaded_file)
                changed = True
                continue

            # possibilité d'effacer le champ avec null / ""
            if field_name in request.data:
                raw_value = str(request.data.get(field_name)).strip().lower()
                if raw_value in ("", "null", "none"):
                    old_file = getattr(user, field_name, None)
                    if old_file and getattr(old_file, "name", None):
                        try:
                            delete_file(old_file.path)
                        except Exception:
                            pass
                    setattr(user, field_name, None)
                    changed = True

        if changed:
            user.save()

    def get(self, request, user_id=None):
        user = self.get_user(request, user_id)

        if user is None:
            return Response(
                {"detail": "Accès interdit."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = UserProfileSerializer(user, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, user_id=None):
        user = self.get_user(request, user_id)

        if user is None:
            return Response(
                {"detail": "Accès interdit."},
                status=status.HTTP_403_FORBIDDEN,
            )

        current_user = request.user
        is_admin_edit = (
            user_id is not None
            and (current_user.role == "ADMIN" or current_user.is_superuser)
            and str(current_user.id) != str(user.id)
        )

        serializer_class = (
            AdminUserUpdateSerializer if is_admin_edit else UserUpdateSerializer
        )

        serializer = serializer_class(
            user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        try:
            self._apply_uploaded_files(user, request)
        except Exception as exc:
            return Response(
                {"image": [str(exc)]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            UserProfileSerializer(user, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def patch(self, request, user_id=None):
        return self.put(request, user_id=user_id)

    def delete(self, request, user_id=None):
        user = self.get_user(request, user_id)

        if user is None:
            return Response(
                {"detail": "Accès interdit."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if user_id is not None:
            current_user = request.user

            if current_user.role != "ADMIN" and not current_user.is_superuser:
                return Response(
                    {"detail": "Accès réservé aux administrateurs."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            password = request.data.get("password")
            if not password:
                return Response(
                    {"detail": "Le mot de passe administrateur est requis."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if not current_user.check_password(password):
                return Response(
                    {"detail": "Mot de passe administrateur invalide."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

        user.delete()
        return Response(
            {"message": "User deleted successfully"},
            status=status.HTTP_204_NO_CONTENT,
        )

class UserInfoView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(
            request.user, context={"request": request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class RequestResetPasswordView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response(
                {"error": "email is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(email=email).first()
        if user:
            token = PasswordResetTokenGenerator().make_token(user)
            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
            reset_path = reverse(
                "reset_password",
                kwargs={"uidb64": uidb64, "token": token},
            )

            configured_base_url = getattr(
                settings, "PASSWORD_RESET_BASE_URL", ""
            ).rstrip("/")
            if configured_base_url:
                reset_link = f"{configured_base_url}{reset_path}"
            else:
                reset_link = request.build_absolute_uri(reset_path)
                if settings.DEBUG is False and reset_link.startswith("http://"):
                    reset_link = reset_link.replace("http://", "https://", 1)

            subject = "Réinitialisation de mot de passe"
            html_message = render_to_string(
                "password_reset_email.html",
                {"reset_link": reset_link},
            )
            send_email_notification(html_message, email, subject)

            return Response(
                {
                    "message": "Un email de réinitialisation a été envoyé à votre adresse. Veuillez vérifier votre boîte de réception."
                },
                status=status.HTTP_202_ACCEPTED,
            )
        else:
            return Response(
                {"message": "Votre compte n'existe pas. Vérifiez votre email."},
                status=status.HTTP_202_ACCEPTED,
            )


def reset_password(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    is_token_valid = (
        user is not None and PasswordResetTokenGenerator().check_token(user, token)
    )

    if request.method == "GET":
        if not is_token_valid:
            return render(
                request,
                "reset_password.html",
                {"error": "Le lien de réinitialisation est invalide ou expiré."},
            )

        return render(request, "reset_password.html")

    if request.method == "POST":
        password = request.POST.get("password")
        password2 = request.POST.get("password2")

        if not is_token_valid:
            return render(
                request,
                "reset_password.html",
                {"error": "Le lien de réinitialisation est invalide ou expiré."},
            )

        if not password or not password2:
            return render(
                request,
                "reset_password.html",
                {"error": "Veuillez remplir les deux champs mot de passe."},
            )

        if password != password2:
            return render(
                request,
                "reset_password.html",
                {"error": "Les mots de passe ne correspondent pas."},
            )

        user.set_password(password)
        user.save()
        return render(request, "password_reset_success.html")

    return render(
        request,
        "reset_password.html",
        {"error": "Méthode non autorisée pour cette opération."},
    )


class UserProfilePhotoView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_user(self, request, user_id=None):
        if user_id is None:
            return request.user

        user = get_object_or_404(User, id=user_id)

        if (
            str(request.user.id) != str(user.id)
            and request.user.role != "ADMIN"
            and not request.user.is_superuser
        ):
            return None

        return user

    def post(self, request, user_id=None):
        user = self.get_user(request, user_id)

        if user is None:
            return Response(
                {"detail": "Accès interdit."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = UserPhotoUploadSerializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "message": "Photo mise à jour avec succès.",
                "photo_url": user.image.url if user.image else None,
            },
            status=status.HTTP_200_OK,
        )

    def patch(self, request, user_id=None):
        return self.post(request, user_id=user_id)

    def delete(self, request, user_id=None):
        user = self.get_user(request, user_id)

        if user is None:
            return Response(
                {"detail": "Accès interdit."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if user.image:
            if user.image.name and default_storage.exists(user.image.name):
                default_storage.delete(user.image.name)
            user.image = None
            user.save(update_fields=["image", "updated_at"])

        return Response(
            {"message": "Photo supprimée avec succès."},
            status=status.HTTP_200_OK,
        )