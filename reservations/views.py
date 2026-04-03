from decimal import Decimal
from itertools import chain

from django.db import transaction
from django.db.models import Count, Prefetch, Sum, Value
from django.db.models.functions import Coalesce, TruncDate, TruncMonth
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils.crypto import get_random_string
from django.utils.timezone import now, timedelta

from drf_yasg.utils import swagger_auto_schema

from rest_framework import permissions, status, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import action, api_view, authentication_classes, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework_simplejwt.authentication import JWTAuthentication

from driver.models import Driver
from gasycar.utils import send_email_notification
from modepayment.models import ModePayment
from smsapp.helpsms import send_sms_befiana
from users.models import User
from reviews.models import Review
from vehicule.models import Vehicule

from .forms import ReservationPaymentForm
from .models import Reservation, ReservationPayment, ReservationPricingConfig, ReservationService
from .serializers import (
    DailyIncomeSerializer,
    ReservationPaymentSerializer,
    ReservationPricingConfigSerializer,
    ReservationSerializer,
    ReservationServiceSerializer,
    ReservationStatisticsSerializer,
)


def authenticate_request(request):
    """
    Authentifie une requête Django à partir du token Bearer dans l’URL
    ou dans l’Authorization header.
    """
    jwt_auth = JWTAuthentication()

    token_param = request.GET.get("token")
    if token_param:
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {token_param}"

    try:
        user_auth_tuple = jwt_auth.authenticate(request)
        if user_auth_tuple:
            return user_auth_tuple[0]
    except Exception:
        pass

    return None


def is_admin_or_support(user):
    return (
        getattr(user, "role", None) in ["ADMIN", "SUPPORT"]
        or getattr(user, "is_superuser", False)
    )


def get_reservation_queryset_for_user(user):
    qs = (
        Reservation.objects.with_relations()
        .select_related(
            "client",
            "vehicle",
            "vehicle__proprietaire",
            "driver",
            "payment",
            "payment__mode",
        )
        .prefetch_related("equipments", "services")
    )

    if is_admin_or_support(user):
        return qs

    if getattr(user, "role", None) == "PRESTATAIRE":
        return qs.filter(vehicle__proprietaire=user)

    return qs.filter(client=user)


def get_reservation_service_queryset_for_user(user):
    qs = (
        ReservationService.objects.with_relations()
        .select_related(
            "reservation",
            "reservation__client",
            "reservation__vehicle",
            "reservation__vehicle__proprietaire",
        )
    )

    if is_admin_or_support(user):
        return qs

    if getattr(user, "role", None) == "PRESTATAIRE":
        return qs.filter(reservation__vehicle__proprietaire=user)

    return qs.filter(reservation__client=user)


# Workflow strict des transitions de réservation
RESERVATION_ALLOWED_TRANSITIONS = {
    Reservation.Status.PENDING: {
        Reservation.Status.CONFIRMED,
        Reservation.Status.CANCELLED,
    },
    Reservation.Status.CONFIRMED: {
        Reservation.Status.IN_PROGRESS,
        Reservation.Status.CANCELLED,
    },
    Reservation.Status.IN_PROGRESS: {
        Reservation.Status.COMPLETED,
    },
    Reservation.Status.COMPLETED: set(),
    Reservation.Status.CANCELLED: set(),
}


def reservation_payment_is_validated(reservation: Reservation) -> bool:
    payment = getattr(reservation, "payment", None)
    return bool(payment and payment.status == ReservationPayment.PaymentStatus.VALIDATED)


def ensure_reservation_transition_allowed(user, reservation: Reservation, target_status: str):
    """
    Vérifie si l'utilisateur a le droit d'effectuer la transition demandée.
    """
    current_status = reservation.status
    allowed_targets = RESERVATION_ALLOWED_TRANSITIONS.get(current_status, set())

    if target_status not in allowed_targets:
        raise PermissionDenied(
            f"Transition non autorisée : {current_status} -> {target_status}."
        )

    role = getattr(user, "role", None)

    # CONFIRMATION
    if target_status == Reservation.Status.CONFIRMED:
        if not reservation_payment_is_validated(reservation):
            raise PermissionDenied(
                "Le paiement doit être validé avant de confirmer la réservation."
            )

        if role != "PRESTATAIRE":
            raise PermissionDenied(
                "Seul le prestataire propriétaire peut confirmer cette réservation."
            )

        if reservation.vehicle.proprietaire_id != user.id:
            raise PermissionDenied("Accès non autorisé.")

        return

    # DÉMARRAGE
    if target_status == Reservation.Status.IN_PROGRESS:
        if role == "PRESTATAIRE":
            if reservation.vehicle.proprietaire_id != user.id:
                raise PermissionDenied("Accès non autorisé.")
            return

        if is_admin_or_support(user):
            return

        raise PermissionDenied(
            "Seul le prestataire propriétaire, l'administrateur ou le support peut démarrer cette réservation."
        )

    # FIN DE LOCATION
    if target_status == Reservation.Status.COMPLETED:
        if role == "PRESTATAIRE":
            if reservation.vehicle.proprietaire_id != user.id:
                raise PermissionDenied("Accès non autorisé.")
            return

        if is_admin_or_support(user):
            return

        raise PermissionDenied(
            "Seul le prestataire propriétaire, l'administrateur ou le support peut terminer cette réservation."
        )

    # ANNULATION
    if target_status == Reservation.Status.CANCELLED:
        if role == "CLIENT":
            if reservation.client_id != user.id:
                raise PermissionDenied("Accès non autorisé.")
            if current_status not in {
                Reservation.Status.PENDING,
                Reservation.Status.CONFIRMED,
            }:
                raise PermissionDenied(
                    "Le client ne peut annuler qu'une réservation en attente ou confirmée."
                )
            return

        if role == "PRESTATAIRE":
            if reservation.vehicle.proprietaire_id != user.id:
                raise PermissionDenied("Accès non autorisé.")
            return

        if is_admin_or_support(user):
            return

        raise PermissionDenied(
            "Vous n'êtes pas autorisé à annuler cette réservation."
        )

    raise PermissionDenied("Transition non gérée.")

class SecuredAPIView(APIView):
    authentication_classes = [JWTAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]


class AdminSupportOnlyAPIView(SecuredAPIView):
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not is_admin_or_support(request.user):
            self.permission_denied(
                request,
                message="Accès réservé aux administrateurs et au support.",
            )


class IsOwnerOrStaff(permissions.BasePermission):
    """
    Autorise si l'utilisateur est staff ou s'il est lié à la réservation.
    """

    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_staff:
            return True

        reservation = getattr(obj, "reservation", None)
        user_id = getattr(request.user, "id", None)

        if not reservation or not user_id:
            return False

        if getattr(reservation, "client_id", None) == user_id:
            return True

        return getattr(reservation.vehicle, "proprietaire_id", None) == user_id

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated


class ReservationPaymentViewSet(viewsets.ModelViewSet):
    queryset = ReservationPayment.objects.select_related(
        "reservation",
        "reservation__client",
        "reservation__vehicle",
        "reservation__vehicle__proprietaire",
        "mode",
        "processed_by",
    ).all()
    serializer_class = ReservationPaymentSerializer
    authentication_classes = [JWTAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        if is_admin_or_support(user):
            return qs

        if getattr(user, "role", None) == "PRESTATAIRE":
            return qs.filter(reservation__vehicle__proprietaire=user)

        return qs.filter(reservation__client=user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    @transaction.atomic
    def perform_create(self, serializer):
        user = self.request.user
        reservation = serializer.validated_data["reservation"]

        if hasattr(reservation, "payment"):
            raise ValidationError(
                {"reservation": "Cette réservation a déjà un paiement."}
            )

        if reservation.status == Reservation.Status.CANCELLED:
            raise ValidationError(
                {"reservation": "Impossible de payer une réservation annulée."}
            )

        allowed = (
            is_admin_or_support(user)
            or reservation.client_id == user.id
            or reservation.vehicle.proprietaire_id == user.id
        )

        if not allowed:
            raise PermissionDenied(
                "Vous n'êtes pas autorisé à créer un paiement pour cette réservation."
            )

        serializer.save(status=ReservationPayment.PaymentStatus.PENDING)

    @transaction.atomic
    def perform_update(self, serializer):
        user = self.request.user
        payment = self.get_object()
        payload_keys = set(self.request.data.keys())
        new_status = serializer.validated_data.get("status", payment.status)

        # On interdit de changer la réservation liée
        if "reservation" in payload_keys:
            raise PermissionDenied(
                "La réservation liée au paiement ne peut pas être modifiée."
            )

        # ADMIN / SUPPORT : peuvent traiter le paiement
        if is_admin_or_support(user):
            processed_by = (
                user
                if new_status in [
                    ReservationPayment.PaymentStatus.VALIDATED,
                    ReservationPayment.PaymentStatus.REJECTED,
                    ReservationPayment.PaymentStatus.REFUNDED,
                ]
                else payment.processed_by
            )
            serializer.save(processed_by=processed_by)
            return

        # CLIENT / PRESTATAIRE : peuvent seulement modifier certaines infos tant que paiement PENDING
        allowed_non_staff_fields = {"mode", "reason", "proof_image"}
        if payload_keys - allowed_non_staff_fields:
            raise PermissionDenied(
                "Seul un administrateur ou le support peut modifier le statut du paiement."
            )

        if payment.status != ReservationPayment.PaymentStatus.PENDING:
            raise PermissionDenied(
                "Un paiement déjà traité ne peut plus être modifié."
            )

        serializer.save(processed_by=payment.processed_by)




LOYALTY_TIERS = [
    {
        "name": "Bronze",
        "min_points": 0,
        "max_points": 299,
        "perks": ["Accès au programme", "Historique des points"],
        "discount_label": "Accès au programme"
    },
    {
        "name": "Silver",
        "min_points": 300,
        "max_points": 799,
        "perks": ["Bonus ponctuels", "Offres fidélité"],
        "discount_label": "Bonus fidélité ponctuels"
    },
    {
        "name": "Gold",
        "min_points": 800,
        "max_points": 1499,
        "perks": ["-10% sur certaines locations", "Avantages exclusifs", "Priorité promo"],
        "discount_label": "-10% sur certaines locations"
    },
    {
        "name": "Platinum",
        "min_points": 1500,
        "max_points": None,
        "perks": ["Privilèges premium", "Bonus majorés", "Accès anticipé aux offres"],
        "discount_label": "-15% sur certaines locations"
    },
]

LOYALTY_RESERVATION_POINTS = 100
LOYALTY_REVIEW_POINTS = 25
LOYALTY_PROFILE_COMPLETION_POINTS = 80


def user_profile_is_complete(user: User) -> bool:
    return all(
        [
            bool((user.first_name or "").strip()),
            bool((user.last_name or "").strip()),
            bool((user.phone or "").strip()),
            bool((user.address or "").strip()),
            bool((user.cin_number or "").strip()),
            bool(user.cin_photo_recto),
            bool(user.cin_photo_verso),
            bool(user.residence_certificate),
            bool(user.permis_conduire or user.permis_conduire_recto),
        ]
    )


def get_loyalty_tier(points: int):
    for tier in LOYALTY_TIERS:
        max_points = tier["max_points"]
        if max_points is None or points <= max_points:
            return tier
    return LOYALTY_TIERS[-1]


def serialize_loyalty_tiers(current_tier_name: str):
    serialized = []
    for tier in LOYALTY_TIERS:
        max_points = tier["max_points"]
        threshold_label = (
            f"{tier['min_points']} à {max_points} points"
            if max_points is not None
            else f"{tier['min_points']}+ points"
        )
        serialized.append(
            {
                "name": tier["name"],
                "thresholdLabel": threshold_label,
                "active": tier["name"] == current_tier_name,
                "perks": tier["perks"],
            }
        )
    return serialized


class LoyaltyOverviewAPIView(SecuredAPIView):
    def get(self, request, format=None):
        user = request.user

        completed_reservations = list(
            Reservation.objects.filter(client=user, status=Reservation.Status.COMPLETED)
            .select_related("vehicle", "vehicle__marque", "vehicle__modele")
            .order_by("-end_datetime", "-updated_at")
        )
        approved_reviews = list(
            Review.objects.filter(
                author=user,
                is_verified=True,
                moderation_status=Review.ModerationStatus.APPROVED,
                review_type=Review.ReviewType.CLIENT_TO_OWNER,
                reservation__isnull=False,
            )
            .select_related("reservation", "reservation__vehicle")
            .order_by("-created_at")
        )

        profile_completed = user_profile_is_complete(user)

        history = []
        total_points = 0

        for reservation in completed_reservations:
            vehicle_label = getattr(reservation.vehicle, "titre", "") or str(reservation.vehicle)
            history.append(
                {
                    "id": f"reservation-{reservation.id}",
                    "title": f"Location terminée · {vehicle_label}",
                    "date": timezone.localtime(reservation.end_datetime).date().isoformat() if reservation.end_datetime else timezone.localdate().isoformat(),
                    "points": LOYALTY_RESERVATION_POINTS,
                    "status": "earned",
                    "description": "Points accordés après une location finalisée avec succès.",
                    "source": "reservation",
                }
            )
            total_points += LOYALTY_RESERVATION_POINTS

        for review in approved_reviews:
            history.append(
                {
                    "id": f"review-{review.id}",
                    "title": "Avis vérifié publié",
                    "date": timezone.localtime(review.created_at).date().isoformat(),
                    "points": LOYALTY_REVIEW_POINTS,
                    "status": "earned",
                    "description": "Bonus engagement après publication d’un retour client utile.",
                    "source": "review",
                }
            )
            total_points += LOYALTY_REVIEW_POINTS

        if profile_completed:
            history.append(
                {
                    "id": f"profile-{user.id}",
                    "title": "Profil complété",
                    "date": timezone.localtime(user.updated_at or user.date_joined).date().isoformat(),
                    "points": LOYALTY_PROFILE_COMPLETION_POINTS,
                    "status": "earned",
                    "description": "Bonus ponctuel débloqué après complétion du profil et des documents.",
                    "source": "profile",
                }
            )
            total_points += LOYALTY_PROFILE_COMPLETION_POINTS

        history.sort(key=lambda item: item["date"], reverse=True)

        current_tier = get_loyalty_tier(total_points)
        current_index = LOYALTY_TIERS.index(current_tier)
        next_tier = LOYALTY_TIERS[current_index + 1] if current_index + 1 < len(LOYALTY_TIERS) else None

        if next_tier:
            points_to_next_tier = max(next_tier["min_points"] - total_points, 0)
            tier_span = max(next_tier["min_points"] - current_tier["min_points"], 1)
            progress = min(100, round(((total_points - current_tier["min_points"]) / tier_span) * 100))
            next_tier_label = next_tier["name"]
        else:
            points_to_next_tier = 0
            progress = 100
            next_tier_label = current_tier["name"]

        stats = [
            {
                "label": "Niveau actuel",
                "value": current_tier["name"],
                "helper": "Avantages fidélité actifs hors parrainage.",
            },
            {
                "label": "Points disponibles",
                "value": str(total_points),
                "helper": "Solde calculé depuis les réservations terminées, les avis approuvés et le profil complété.",
            },
            {
                "label": "Prochain palier",
                "value": f"{points_to_next_tier} pts" if next_tier else current_tier["name"],
                "helper": (
                    f"Encore {points_to_next_tier} points pour atteindre {next_tier['name']}."
                    if next_tier
                    else "Palier maximum déjà atteint."
                ),
            },
        ]

        return Response(
            {
                "title": "Mes points fidélité",
                "subtitle": "Suivez votre progression, découvrez vos avantages et visualisez les récompenses disponibles dans votre espace client.",
                "points": total_points,
                "nextTierLabel": next_tier_label,
                "pointsToNextTier": points_to_next_tier,
                "progress": progress,
                "memberSince": timezone.localtime(user.date_joined).strftime("%B %Y"),
                "discountLabel": current_tier["discount_label"],
                "stats": stats,
                "history": history,
                "tiers": serialize_loyalty_tiers(current_tier["name"]),
                "rules": {
                    "reservationPoints": LOYALTY_RESERVATION_POINTS,
                    "reviewPoints": LOYALTY_REVIEW_POINTS,
                    "profilePoints": LOYALTY_PROFILE_COMPLETION_POINTS,
                    "referralEnabled": False,
                },
            },
            status=status.HTTP_200_OK,
        )


class ReservationPricingConfigAPIView(SecuredAPIView):
    """
    Expose et met à jour la configuration globale de tarification réservation.
    """

    def get(self, request, format=None):
        config = ReservationPricingConfig.get_solo()
        serializer = ReservationPricingConfigSerializer(config)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, format=None):
        user = request.user
        if getattr(user, "role", None) != "ADMIN" and not user.is_superuser:
            return Response(
                {"detail": "Seul un administrateur peut modifier cette configuration."},
                status=status.HTTP_403_FORBIDDEN,
            )

        config = ReservationPricingConfig.get_solo()
        serializer = ReservationPricingConfigSerializer(
            config,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


def user_can_pay_reservation(user, reservation):
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if user.is_staff:
        return True
    if reservation.client_id == user.id:
        return True
    return reservation.vehicle.proprietaire_id == user.id


class ReservationViewSet(viewsets.ModelViewSet):
    serializer_class = ReservationSerializer
    authentication_classes = [JWTAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return get_reservation_queryset_for_user(self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    @transaction.atomic
    def perform_create(self, serializer):
        user = self.request.user
        vehicle = serializer.validated_data.get("vehicle")

        if getattr(user, "role", None) == "CLIENT":
            serializer.save(client=user)
            return

        if getattr(user, "role", None) == "PRESTATAIRE":
            if not vehicle or vehicle.proprietaire_id != user.id:
                raise PermissionDenied(
                    "Vous ne pouvez créer une réservation que sur vos propres véhicules."
                )
            serializer.save()
            return

        if is_admin_or_support(user):
            serializer.save()
            return

        raise PermissionDenied("Vous n'êtes pas autorisé à créer cette réservation.")

    @transaction.atomic
    def perform_update(self, serializer):
        payload_keys = set(self.request.data.keys())

        # Le statut ne passe plus par PATCH générique
        if "status" in payload_keys:
            raise PermissionDenied(
                "Le statut ne peut plus être modifié via PATCH générique. "
                "Utilisez les endpoints dédiés : accept, cancel, start, complete."
            )

        # Modification générique réservée à admin/support
        if not is_admin_or_support(self.request.user):
            raise PermissionDenied(
                "Seul un administrateur ou le support peut modifier les détails d'une réservation."
            )

        serializer.save()

    def destroy(self, request, *args, **kwargs):
        if not is_admin_or_support(request.user):
            return Response(
                {
                    "detail": "Seul un administrateur ou le support peut supprimer définitivement une réservation."
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().destroy(request, *args, **kwargs)

    def _transition(self, request, reservation: Reservation, target_status: str):
        ensure_reservation_transition_allowed(request.user, reservation, target_status)
        reservation.status = target_status
        reservation.save(update_fields=["status", "updated_at"])
        serializer = self.get_serializer(reservation)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        reservation = self.get_object()
        return self._transition(request, reservation, Reservation.Status.CONFIRMED)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        reservation = self.get_object()
        return self._transition(request, reservation, Reservation.Status.CANCELLED)

    @action(detail=True, methods=["post"], url_path="start")
    def start_trip(self, request, pk=None):
        reservation = self.get_object()
        return self._transition(request, reservation, Reservation.Status.IN_PROGRESS)

    @action(detail=True, methods=["post"], url_path="complete")
    def complete_trip(self, request, pk=None):
        reservation = self.get_object()
        return self._transition(request, reservation, Reservation.Status.COMPLETED)

    @action(detail=False, methods=["post"], url_path="delete-all")
    def delete_all(self, request):
        current_user = request.user

        if not getattr(current_user, "is_authenticated", False):
            return Response(
                {"detail": "Authentification requise."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not is_admin_or_support(current_user):
            return Response(
                {"detail": "Accès réservé aux administrateurs et au support."},
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

        reservations_qs = Reservation.objects.all()
        reservation_count = reservations_qs.count()

        if reservation_count == 0:
            return Response(
                {"message": "Aucune réservation à supprimer.", "deleted_count": 0},
                status=status.HTTP_200_OK,
            )

        with transaction.atomic():
            reservations_qs.delete()

        return Response(
            {
                "message": "Toutes les réservations et preuves de paiement liées ont été supprimées.",
                "deleted_count": reservation_count,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def assign_driver(self, request, pk=None):
        if not is_admin_or_support(request.user):
            return Response(
                {"detail": "Seul un administrateur ou le support peut assigner un chauffeur."},
                status=status.HTTP_403_FORBIDDEN,
            )

        from .pricing_service import PricingService

        reservation = self.get_object()
        driver_id = request.data.get("driver_id")

        if not driver_id:
            return Response(
                {"error": "driver_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            driver = Driver.objects.get(id=driver_id)
        except Driver.DoesNotExist:
            return Response(
                {"error": "Driver not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        reservation.driver = driver
        reservation.driver_source = Reservation.DriverSource.ADMIN_POOL
        reservation.with_chauffeur = True
        reservation.driving_mode = Reservation.DrivingMode.WITH_DRIVER

        pricing_result = PricingService.calculate_amounts(
            vehicle=reservation.vehicle,
            start_datetime=reservation.start_datetime,
            end_datetime=reservation.end_datetime,
            pricing_zone=reservation.pricing_zone,
            driving_mode=reservation.driving_mode,
            driver_source=reservation.driver_source,
        )

        reservation.total_days = pricing_result["days"]
        reservation.base_amount = pricing_result["base_amount"]
        reservation.options_amount = pricing_result["driver_amount"]
        reservation.total_amount = pricing_result["total_amount"]
        reservation.save()

        chauffeur_service, _ = ReservationService.objects.get_or_create(
            reservation=reservation,
            service_type=ReservationService.ServiceType.CHAUFFEUR,
            defaults={
                "service_name": "Chauffeur Pro",
                "price": pricing_result["driver_amount"] / pricing_result["days"],
                "quantity": pricing_result["days"],
            },
        )
        chauffeur_service.service_name = "Chauffeur Pro"
        chauffeur_service.price = pricing_result["driver_amount"] / pricing_result["days"]
        chauffeur_service.quantity = pricing_result["days"]
        chauffeur_service.save()

        return Response(
            ReservationSerializer(reservation, context={"request": request}).data
        )


class UserReservationsAPIView(SecuredAPIView):
    @swagger_auto_schema(
        operation_description="Retrieve reservations for a specific user"
    )
    def get(self, request, user_id, format=None):
        if not is_admin_or_support(request.user) and request.user.id != user_id:
            return Response(
                {"detail": "Accès non autorisé."},
                status=status.HTTP_403_FORBIDDEN,
            )

        reservations = get_reservation_queryset_for_user(request.user).filter(client__id=user_id)
        serializer = ReservationSerializer(
            reservations,
            many=True,
            context={"request": request},
        )
        return Response(serializer.data)


class VehicleReservationsAPIView(SecuredAPIView):
    @swagger_auto_schema(
        operation_description="Retrieve reservations for a specific vehicle"
    )
    def get(self, request, vehicle_id, format=None):
        vehicle = get_object_or_404(Vehicule, id=vehicle_id)

        if (
            not is_admin_or_support(request.user)
            and getattr(request.user, "role", None) == "PRESTATAIRE"
            and vehicle.proprietaire_id != request.user.id
        ):
            return Response(
                {"detail": "Accès non autorisé."},
                status=status.HTTP_403_FORBIDDEN,
            )

        reservations = get_reservation_queryset_for_user(request.user).filter(vehicle__id=vehicle_id)
        serializer = ReservationSerializer(
            reservations,
            many=True,
            context={"request": request},
        )
        return Response(serializer.data)


class StatusReservationsAPIView(SecuredAPIView):
    @swagger_auto_schema(operation_description="Retrieve reservations by status")
    def get(self, request, status, format=None):
        reservations = get_reservation_queryset_for_user(request.user).filter(status=status)
        serializer = ReservationSerializer(
            reservations,
            many=True,
            context={"request": request},
        )
        return Response(serializer.data)


class ActiveReservationsAPIView(SecuredAPIView):
    @swagger_auto_schema(operation_description="Retrieve active reservations")
    def get(self, request, format=None):
        active_statuses = [
            Reservation.Status.PENDING,
            Reservation.Status.CONFIRMED,
            Reservation.Status.IN_PROGRESS,
        ]
        reservations = get_reservation_queryset_for_user(request.user).filter(
            status__in=active_statuses
        )
        serializer = ReservationSerializer(
            reservations,
            many=True,
            context={"request": request},
        )
        return Response(serializer.data)


class CompletedReservationsAPIView(SecuredAPIView):
    @swagger_auto_schema(operation_description="Retrieve completed reservations")
    def get(self, request, format=None):
        completed_statuses = [
            Reservation.Status.COMPLETED,
            Reservation.Status.CANCELLED,
        ]
        reservations = get_reservation_queryset_for_user(request.user).filter(
            status__in=completed_statuses
        )
        serializer = ReservationSerializer(
            reservations,
            many=True,
            context={"request": request},
        )
        return Response(serializer.data)


class DateRangeReservationsAPIView(SecuredAPIView):
    @swagger_auto_schema(
        operation_description="Retrieve reservations within a date range"
    )
    def get(self, request, start_date, end_date, format=None):
        reservations = get_reservation_queryset_for_user(request.user).filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
        )
        serializer = ReservationSerializer(
            reservations,
            many=True,
            context={"request": request},
        )
        return Response(serializer.data)


class TotalReservationsCountAPIView(SecuredAPIView):
    @swagger_auto_schema(operation_description="Retrieve total count of reservations")
    def get(self, request, format=None):
        total_count = get_reservation_queryset_for_user(request.user).count()
        return Response({"total_reservations": total_count})


class TotalReservationsAmountAPIView(SecuredAPIView):
    @swagger_auto_schema(
        operation_description="Retrieve total amount of all reservations"
    )
    def get(self, request, format=None):
        total_amount = (
            get_reservation_queryset_for_user(request.user).aggregate(
                Sum("total_amount")
            )["total_amount__sum"]
            or 0
        )
        return Response({"total_reservations_amount": total_amount})


class ReservationStatisticsAPIView(AdminSupportOnlyAPIView):
    @swagger_auto_schema(
        operation_description="Retrieve aggregated reservation statistics for the admin dashboard"
    )
    def get(self, request, format=None):
        base_qs = Reservation.objects.all()

        aggregates = base_qs.aggregate(
            total_reservations=Count("id"),
            total_amount_sum=Coalesce(Sum("total_amount"), Value(Decimal("0"))),
        )

        status_counts = {choice[0]: 0 for choice in Reservation.Status.choices}
        for status_data in base_qs.values("status").annotate(count=Count("id")):
            status_counts[status_data["status"]] = status_data["count"]

        monthly_stats_qs = (
            base_qs.annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )
        monthly_stats = [
            {"month": entry["month"].strftime("%Y-%m"), "count": entry["count"]}
            for entry in monthly_stats_qs
            if entry["month"] is not None
        ]

        serializer = ReservationStatisticsSerializer(
            data={
                "total_reservations": aggregates["total_reservations"],
                "total_amount_sum": aggregates["total_amount_sum"],
                "by_status": status_counts,
                "reservations_per_month": monthly_stats,
            }
        )
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ChauffeurReservationsAPIView(SecuredAPIView):
    @swagger_auto_schema(operation_description="Retrieve reservations with chauffeur")
    def get(self, request, format=None):
        reservations = get_reservation_queryset_for_user(request.user).filter(
            with_chauffeur=True
        )
        serializer = ReservationSerializer(
            reservations,
            many=True,
            context={"request": request},
        )
        return Response(serializer.data)


class WithoutChauffeurReservationsAPIView(SecuredAPIView):
    @swagger_auto_schema(
        operation_description="Retrieve reservations without chauffeur"
    )
    def get(self, request, format=None):
        reservations = get_reservation_queryset_for_user(request.user).filter(
            with_chauffeur=False
        )
        serializer = ReservationSerializer(
            reservations,
            many=True,
            context={"request": request},
        )
        return Response(serializer.data)


class PickupLocationReservationsAPIView(SecuredAPIView):
    @swagger_auto_schema(
        operation_description="Retrieve reservations by pickup location"
    )
    def get(self, request, pickup_location, format=None):
        reservations = get_reservation_queryset_for_user(request.user).filter(
            pickup_location__icontains=pickup_location
        )
        serializer = ReservationSerializer(
            reservations,
            many=True,
            context={"request": request},
        )
        return Response(serializer.data)


class DropoffLocationReservationsAPIView(SecuredAPIView):
    @swagger_auto_schema(
        operation_description="Retrieve reservations by dropoff location"
    )
    def get(self, request, dropoff_location, format=None):
        reservations = get_reservation_queryset_for_user(request.user).filter(
            dropoff_location__icontains=dropoff_location
        )
        serializer = ReservationSerializer(
            reservations,
            many=True,
            context={"request": request},
        )
        return Response(serializer.data)


class MinTotalAmountReservationsAPIView(SecuredAPIView):
    @swagger_auto_schema(
        operation_description="Retrieve reservations with minimum total amount"
    )
    def get(self, request, min_amount, format=None):
        reservations = get_reservation_queryset_for_user(request.user).filter(
            total_amount__gte=min_amount
        )
        serializer = ReservationSerializer(
            reservations,
            many=True,
            context={"request": request},
        )
        return Response(serializer.data)


class MaxTotalAmountReservationsAPIView(SecuredAPIView):
    @swagger_auto_schema(
        operation_description="Retrieve reservations with maximum total amount"
    )
    def get(self, request, max_amount, format=None):
        reservations = get_reservation_queryset_for_user(request.user).filter(
            total_amount__lte=max_amount
        )
        serializer = ReservationSerializer(
            reservations,
            many=True,
            context={"request": request},
        )
        return Response(serializer.data)


class MinTotalDaysReservationsAPIView(SecuredAPIView):
    @swagger_auto_schema(
        operation_description="Retrieve reservations with minimum total days"
    )
    def get(self, request, min_days, format=None):
        reservations = get_reservation_queryset_for_user(request.user).filter(
            total_days__gte=min_days
        )
        serializer = ReservationSerializer(
            reservations,
            many=True,
            context={"request": request},
        )
        return Response(serializer.data)


class ReservationServiceViewSet(viewsets.ModelViewSet):
    serializer_class = ReservationServiceSerializer
    authentication_classes = [JWTAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return get_reservation_service_queryset_for_user(self.request.user)

    @transaction.atomic
    def perform_create(self, serializer):
        if not is_admin_or_support(self.request.user):
            raise PermissionDenied(
                "Seul un administrateur ou le support peut créer un service de réservation."
            )
        serializer.save()

    @transaction.atomic
    def perform_update(self, serializer):
        if not is_admin_or_support(self.request.user):
            raise PermissionDenied(
                "Seul un administrateur ou le support peut modifier un service de réservation."
            )
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        if not is_admin_or_support(request.user):
            return Response(
                {
                    "detail": "Seul un administrateur ou le support peut supprimer un service de réservation."
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().destroy(request, *args, **kwargs)


class ReservationServiceByReservationAPIView(SecuredAPIView):
    @swagger_auto_schema(
        operation_description="Retrieve reservation services for a specific reservation"
    )
    def get(self, request, reservation_id, format=None):
        services = get_reservation_service_queryset_for_user(request.user).filter(
            reservation__id=reservation_id
        )
        serializer = ReservationServiceSerializer(services, many=True)
        return Response(serializer.data)


class ReservationServiceByTypeAPIView(SecuredAPIView):
    @swagger_auto_schema(
        operation_description="Retrieve reservation services by service type"
    )
    def get(self, request, service_type, format=None):
        services = get_reservation_service_queryset_for_user(request.user).filter(
            service_type=service_type
        )
        serializer = ReservationServiceSerializer(services, many=True)
        return Response(serializer.data)


class ReservationServiceByNameAPIView(SecuredAPIView):
    @swagger_auto_schema(
        operation_description="Retrieve reservation services by service name"
    )
    def get(self, request, service_name, format=None):
        services = get_reservation_service_queryset_for_user(request.user).filter(
            service_name__icontains=service_name
        )
        serializer = ReservationServiceSerializer(services, many=True)
        return Response(serializer.data)


class ReservationServiceByPriceRangeAPIView(SecuredAPIView):
    @swagger_auto_schema(
        operation_description="Retrieve reservation services within a price range"
    )
    def get(self, request, min_price, max_price, format=None):
        services = get_reservation_service_queryset_for_user(request.user).filter(
            price__gte=min_price,
            price__lte=max_price,
        )
        serializer = ReservationServiceSerializer(services, many=True)
        return Response(serializer.data)


class ReservationServiceByMinQuantityAPIView(SecuredAPIView):
    @swagger_auto_schema(
        operation_description="Retrieve reservation services with minimum quantity"
    )
    def get(self, request, min_quantity, format=None):
        services = get_reservation_service_queryset_for_user(request.user).filter(
            quantity__gte=min_quantity
        )
        serializer = ReservationServiceSerializer(services, many=True)
        return Response(serializer.data)


class ReservationServiceByMaxQuantityAPIView(SecuredAPIView):
    @swagger_auto_schema(
        operation_description="Retrieve reservation services with maximum quantity"
    )
    def get(self, request, max_quantity, format=None):
        services = get_reservation_service_queryset_for_user(request.user).filter(
            quantity__lte=max_quantity
        )
        serializer = ReservationServiceSerializer(services, many=True)
        return Response(serializer.data)


class DailyIncomeAPIView(AdminSupportOnlyAPIView):
    @swagger_auto_schema(
        operation_description="Retrieve daily income based on reservation totals"
    )
    def get(self, request, format=None):
        daily_income_qs = (
            Reservation.objects.annotate(date=TruncDate("created_at"))
            .values("date")
            .annotate(total_income=Coalesce(Sum("total_amount"), Value(Decimal("0"))))
            .order_by("date")
        )
        serializer = DailyIncomeSerializer(daily_income_qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ReservationStatsViewSet(viewsets.ViewSet):
    authentication_classes = [JWTAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def _check_admin_or_support(self, request):
        if not is_admin_or_support(request.user):
            raise PermissionDenied(
                "Accès réservé aux administrateurs et au support."
            )

    @action(detail=False, methods=["get"])
    def day(self, request):
        self._check_admin_or_support(request)

        today = now().date()
        data = (
            Reservation.objects.filter(created_at__date=today)
            .extra(select={"hour": "EXTRACT(HOUR FROM created_at)"})
            .values("hour")
            .annotate(total=Count("id"))
            .order_by("hour")
        )

        graph = [{"hour": int(d["hour"]), "total": d["total"]} for d in data]
        return Response(graph)

    @action(detail=False, methods=["get"])
    def week(self, request):
        self._check_admin_or_support(request)

        today = now().date()
        start_week = today - timedelta(days=today.weekday())

        data = (
            Reservation.objects.filter(created_at__date__gte=start_week)
            .extra(select={"day": "TO_CHAR(created_at, 'Day')"})
            .values("day")
            .annotate(total=Count("id"))
            .order_by("day")
        )

        graph = [{"day": d["day"].strip(), "total": d["total"]} for d in data]
        return Response(graph)

    @action(detail=False, methods=["get"])
    def month(self, request):
        self._check_admin_or_support(request)

        today = now().date()
        data = (
            Reservation.objects.filter(created_at__month=today.month)
            .extra(select={"day": "EXTRACT(DAY FROM created_at)"})
            .values("day")
            .annotate(total=Count("id"))
            .order_by("day")
        )

        graph = [{"day": int(d["day"]), "total": d["total"]} for d in data]
        return Response(graph)


class OwnerVehicleReservationsAPIView(SecuredAPIView):
    """
    Récupère toutes les réservations faites par des clients
    sur les véhicules appartenant à un propriétaire.
    """

    @swagger_auto_schema(
        operation_description=(
            "Récupère les réservations des clients qui ont réservé "
            "un véhicule appartenant à cet utilisateur (propriétaire)."
        ),
        responses={200: ReservationSerializer(many=True)},
    )
    def get(self, request, owner_id):
        owner = get_object_or_404(User, id=owner_id)

        if not is_admin_or_support(request.user):
            if getattr(request.user, "role", None) != "PRESTATAIRE" or request.user.id != owner.id:
                return Response(
                    {"detail": "Accès non autorisé."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        vehicles = Vehicule.objects.filter(proprietaire=owner)
        reservations = get_reservation_queryset_for_user(request.user).filter(
            vehicle__in=vehicles
        )

        serializer = ReservationSerializer(
            reservations,
            many=True,
            context={"request": request},
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


def reservation_payment_page(request, reservation_id, payment_id):
    user = authenticate_request(request)
    if not user:
        return render(request, "403.html", status=403)

    reservation = get_object_or_404(Reservation, id=reservation_id)
    payment_mode = get_object_or_404(ModePayment, id=payment_id)

    if not user_can_pay_reservation(user, reservation):
        return render(request, "403.html", status=403)

    payment_ref = request.GET.get("ref")
    payment_token = request.GET.get("paytok")
    jwt_token = request.GET.get("token")

    return render(
        request,
        "ReservationPaymentPage.html",
        {
            "reservation": reservation,
            "payment_modes": [payment_mode],
            "hidden_payment_id": str(payment_mode.id),
            "hidden_reservation_id": str(reservation.id),
            "payment_reference": payment_ref,
            "payment_token": payment_token,
            "jwt_token": jwt_token,
        },
    )


def submit_reservation_payment(request):
    token = request.POST.get("auth_token")

    if token:
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {token}"

    user = authenticate_request(request)
    if not user:
        return render(
            request,
            "payment_error.html",
            {"message": "Authentification invalide"},
            status=403,
        )

    if request.method != "POST":
        return redirect("/")

    form = ReservationPaymentForm(request.POST, request.FILES)

    reservation_id = request.POST.get("reservation")
    payment_id = request.POST.get("payment_id")
    payment_mode = get_object_or_404(ModePayment, id=payment_id)

    reservation = get_object_or_404(
        Reservation.objects.select_related("client", "vehicle"),
        id=reservation_id,
    )

    if not user_can_pay_reservation(user, reservation):
        return render(
            request,
            "payment_error.html",
            {"message": "Accès non autorisé"},
            status=403,
        )

    if form.is_valid():
        if hasattr(reservation, "payment"):
            return render(
                request,
                "payment_error.html",
                {"message": "Un paiement est déjà enregistré pour cette réservation."},
            )

        payment = form.save(commit=False)
        payment.reservation = reservation
        payment.mode = payment_mode
        payment.status = ReservationPayment.PaymentStatus.PENDING
        payment.save()

        context = {
            "reservation": reservation,
            "payment": payment,
        }

        return render(request, "booking_detail.html", context)

    return render(
        request,
        "payment_error.html",
        {
            "message": "Le formulaire contient des erreurs.",
            "errors": form.errors,
        },
    )


@api_view(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def send_link_payment(request):
    methode_id = request.data.get("methode_payment")
    reservation_id = request.data.get("reservation_id")

    methode_payment = get_object_or_404(ModePayment, id=methode_id)
    reservation = get_object_or_404(Reservation, id=reservation_id)

    if not user_can_pay_reservation(request.user, reservation):
        return Response({"detail": "Non autorisé"}, status=403)

    token = str(request.auth)

    ref_prefix = (methode_payment.operateur or methode_payment.name)[:4].upper()
    payment_reference = f"REF-{ref_prefix}-{get_random_string(8).upper()}"

    payment_url = request.build_absolute_uri(
        f"/api/bookings/{reservation.id}/and/{methode_payment.id}/payment/?token={token}&ref={payment_reference}"
    )

    email_context = {
        "client_name": reservation.client.first_name or reservation.client.email,
        "payment_url": payment_url,
        "payment_mode_name": methode_payment.name,
        "payment_mode_number": methode_payment.numero,
        "payment_reference": payment_reference,
        "payment_id": methode_payment.id,
    }

    html_message = render_to_string("payment_link_email.html", email_context)

    subject = "Lien de confirmation de paiement"
    recipient = reservation.client.email

    try:
        send_email_notification(html_message, recipient, subject, is_html=True)
    except Exception as e:
        return Response(
            {"detail": "Erreur envoi e-mail", "error": str(e)},
            status=500,
        )

    try:
        message = (
            f"Bonjour {reservation.client.first_name}, veuillez confirmer votre paiement "
            f"de la réservation {reservation.reference} via ce lien : {payment_url}"
        )

        full_phone = reservation.client.phone
        phone_client = ""
        if full_phone:
            if full_phone.startswith("+261"):
                phone_client = full_phone.replace("+261", "", 1)
            else:
                phone_client = full_phone.lstrip("+")

        send_sms_befiana(phone_client, message)
    except Exception as e:
        return Response(
            {"detail": "Erreur envoi sms", "error": str(e)},
            status=500,
        )

    return Response({"detail": "Lien envoyé avec succès"})
