#  import drf
from django.db import IntegrityError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

# models
from .models import Review

# serialzier
from .serializers import ReviewSerializer


def is_support_or_admin(user):
    return bool(
        user
        and user.is_authenticated
        and (user.is_staff or getattr(user, "role", None) in ["ADMIN", "SUPPORT"])
    )


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.select_related("author", "target", "reservation")
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Review.objects.select_related("author", "target", "reservation")
        user = self.request.user

        if is_support_or_admin(user):
            return qs

        if self.action == "written_by_user":
            user_id = self.kwargs.get("user_id")
            if user_id and str(user.id) == str(user_id):
                return qs.filter(author_id=user_id)

        return qs.filter(moderation_status=Review.ModerationStatus.APPROVED)

    # ============================================================
    # ❤️ SÉCURITÉ : Empêcher crash si contrainte d’unicité échoue
    # ============================================================
    def perform_create(self, serializer):
        try:
            serializer.save(author=self.request.user)
        except IntegrityError:
            raise ValidationError({
                "detail": "Vous avez déjà laissé un avis pour cette réservation ou cet utilisateur."
            })

    def perform_update(self, serializer):
        if not is_support_or_admin(self.request.user):
            raise PermissionDenied("Seuls les administrateurs et le support peuvent modifier un avis.")

        try:
            serializer.save()
        except IntegrityError:
            raise ValidationError({
                "detail": "Impossible de modifier : une contrainte d’unicité empêche cette action."
            })

    # ============================================================
    # 🔥 1) Reviews liés à une réservation
    # GET /reviews/reservation/<reservation_id>/
    # ============================================================
    @action(detail=False, methods=["get"], url_path=r"reservation/(?P<reservation_id>[0-9a-f-]+)")
    def by_reservation(self, request, reservation_id):
        reviews = self.get_queryset().filter(reservation_id=reservation_id)
        serializer = self.get_serializer(reviews, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path=r"vehicle/(?P<vehicle_id>[0-9a-f-]+)")
    def by_vehicle(self, request, vehicle_id):
        reviews = self.get_queryset().filter(reservation__vehicle_id=vehicle_id)
        serializer = self.get_serializer(reviews, many=True)
        return Response(serializer.data)

    # ============================================================
    # 🔥 2) Reviews écrits PAR un user
    # GET /reviews/user/<user_id>/written/
    # ============================================================
    @action(detail=False, methods=["get"], url_path=r"user/(?P<user_id>[0-9a-f-]+)/written")
    def written_by_user(self, request, user_id):
        reviews = self.get_queryset().filter(author_id=user_id)
        serializer = self.get_serializer(reviews, many=True)
        return Response(serializer.data)

    # ============================================================
    # 🔥 3) Reviews reçus PAR un user
    # GET /reviews/user/<user_id>/received/
    # ============================================================
    @action(detail=False, methods=["get"], url_path=r"user/(?P<user_id>[0-9a-f-]+)/received")
    def received_by_user(self, request, user_id):
        reviews = self.get_queryset().filter(target_id=user_id)
        serializer = self.get_serializer(reviews, many=True)
        return Response(serializer.data)

    # ============================================================
    # 🔥 4) Réservations en attente d'avis (pour un véhicule donné)
    # GET /reviews/pending/?vehicle_id=...
    # ============================================================
    @action(detail=False, methods=["get"], url_path="pending")
    def pending(self, request):
        vehicle_id = request.query_params.get("vehicle_id")
        if not vehicle_id:
            return Response({"detail": "vehicle_id is required"}, status=400)

        from reservations.models import Reservation

        reservations = Reservation.objects.filter(
            client=request.user,
            vehicle_id=vehicle_id,
            status=Reservation.Status.COMPLETED,
        ).exclude(
            reviews__author=request.user
        ).order_by("-end_datetime")

        data = [
            {
                "id": str(r.id),
                "start_date": r.start_datetime,
                "end_date": r.end_datetime,
                "total_amount": str(r.total_amount)
            }
            for r in reservations
        ]
        return Response(data)

    @action(detail=True, methods=["post"], url_path="moderate")
    def moderate(self, request, pk=None):
        if not is_support_or_admin(request.user):
            raise PermissionDenied("Seuls les administrateurs et le support peuvent modérer un avis.")

        review = self.get_object()
        moderation_status = request.data.get("moderation_status")
        allowed_statuses = {
            Review.ModerationStatus.APPROVED,
            Review.ModerationStatus.REJECTED,
            Review.ModerationStatus.PENDING,
        }

        if moderation_status not in allowed_statuses:
            raise ValidationError({
                "moderation_status": "Statut de modération invalide."
            })

        review.moderation_status = moderation_status
        review.save(update_fields=["moderation_status", "updated_at"])

        serializer = self.get_serializer(review)
        return Response(serializer.data, status=status.HTTP_200_OK)
