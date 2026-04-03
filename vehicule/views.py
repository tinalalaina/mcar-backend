import uuid

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_yasg.utils import swagger_auto_schema

from notification.models import Notification
from reservations.models import Reservation
from users.models import User
from users.serializers import UserProfileSerializer
from driver.models import Driver

from gasycar.utils import delete_file

from .models import (
    Category,
    FuelType,
    Marque,
    ModeleVehicule,
    StatusVehicule,
    Transmission,
    Vehicule,
    VehiculeFavorite,
    VehicleAvailability,
    VehicleConditionReport,
    VehicleDocuments,
    VehicleEquipments,
    IncludedEquipment,
    VehiclePhoto,
)
from .serializers import (
    CategorySerializer,
    FastCategorySerializer,
    FuelTypeSerializer,
    MarqueSerializer,
    ModeleVehiculeSerializer,
    StatusSerializer,
    TransmissionSerializer,
    VehiculeCardSerializer,
    VehiculeSearchSerializer,
    VehiculeSerializer,
    VehicleAvailabilitySerializer,
    VehicleConditionReportSerializer,
    VehicleDocumentsSerializer,
    VehicleEquipmentsSerializer,
    IncludedEquipmentSerializer,
    VehiclePhotoSerializer,
    VehiclePhotoUploadSerializer,
)

STAFF_ROLES = ["ADMIN", "SUPPORT"]

PUBLIC_COUNTED_RESERVATION_STATUSES = [
    Reservation.Status.CONFIRMED,
    Reservation.Status.IN_PROGRESS,
    Reservation.Status.COMPLETED,
]

POPULAR_MIN_RESERVATIONS = 3


def is_staff_user(user):
    return bool(
        user
        and user.is_authenticated
        and (getattr(user, "role", None) in STAFF_ROLES or user.is_staff)
    )


def build_vehicle_action_url(user, vehicle):
    role = getattr(user, "role", None)

    if role == "ADMIN":
        return f"/admin/vehicles/{vehicle.id}"
    if role == "SUPPORT":
        return f"/support/fleet/vehicule/{vehicle.id}"
    if role == "PRESTATAIRE" and vehicle.proprietaire_id == user.id:
        return f"/prestataire/vehicle/{vehicle.id}/manage"
    return f"/vehicule/{vehicle.id}"


def push_notification(notification):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    payload = {
        "id": str(notification.id),
        "title": notification.title,
        "body": notification.body,
        "notification_type": notification.notification_type,
        "created_at": notification.created_at.isoformat(),
        "is_read": notification.is_read,
        "reservation": str(notification.reservation_id)
        if notification.reservation_id
        else None,
        "vehicle": str(notification.vehicle_id) if notification.vehicle_id else None,
        "vehicle_document": str(notification.vehicle_document_id)
        if notification.vehicle_document_id
        else None,
        "action_url": notification.action_url,
        "extra_data": notification.extra_data or {},
    }

    async_to_sync(channel_layer.group_send)(
        f"user_{notification.user_id}",
        {
            "type": "notification_message",
            "message": payload,
        },
    )


def notify_users(
    users,
    notification_type,
    title,
    body,
    vehicle=None,
    vehicle_document=None,
    action_url_builder=None,
    extra_data=None,
):
    for user in users:
        action_url = ""
        if callable(action_url_builder):
            action_url = action_url_builder(user)

        notif = Notification.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            body=body,
            vehicle=vehicle,
            vehicle_document=vehicle_document,
            action_url=action_url,
            extra_data=extra_data or {},
        )
        push_notification(notif)


def annotate_public_metrics(qs):
    return qs.annotate(
        valid_reservations_count=Count(
            "reservations",
            filter=Q(reservations__status__in=PUBLIC_COUNTED_RESERVATION_STATUSES),
            distinct=True,
        )
    )


def filter_publicly_visible(qs):
    """
    Source de vérité unique pour TOUT affichage public.
    Un véhicule public doit être :
    - validé
    - publié
    - avec documents validés
    - propriétaire actif
    - avec au moins une photo
    - avec au moins un prix journalier > 0
    """
    return (
        annotate_public_metrics(qs)
        .filter(
            valide=True,
            workflow_status=Vehicule.WorkflowStatus.PUBLISHED,
            documents__is_valide=True,
            proprietaire__is_active=True,
            photos__isnull=False,
            pricing_grid__prix_jour__gt=0,
            published_at__isnull=False,
        )
        .distinct()
    )


def reset_vehicle_review_state(vehicle):
    vehicle.valide = False
    vehicle.workflow_status = Vehicule.WorkflowStatus.DRAFT
    vehicle.review_comment = ""
    vehicle.reviewed_by = None
    vehicle.reviewed_at = None
    vehicle.submitted_at = None
    vehicle.published_at = None
    vehicle.save(
        update_fields=[
            "valide",
            "workflow_status",
            "review_comment",
            "reviewed_by",
            "reviewed_at",
            "submitted_at",
            "published_at",
            "updated_at",
        ]
    )


class MarqueViewSet(viewsets.ModelViewSet):
    queryset = Marque.objects.all().order_by("-created_at")
    serializer_class = MarqueSerializer


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all().order_by("-created_at")
    serializer_class = CategorySerializer

    def list(self, request, *args, **kwargs):
        self.serializer_class = FastCategorySerializer
        return super().list(request, *args, **kwargs)


class TransmissionViewSet(viewsets.ModelViewSet):
    queryset = Transmission.objects.all().order_by("-created_at")
    serializer_class = TransmissionSerializer


class FuelTypeViewSet(viewsets.ModelViewSet):
    queryset = FuelType.objects.all().order_by("-created_at")
    serializer_class = FuelTypeSerializer


class StatusViewSet(viewsets.ModelViewSet):
    queryset = StatusVehicule.objects.all().order_by("-created_at")
    serializer_class = StatusSerializer


class ModeleVehiculeViewSet(viewsets.ModelViewSet):
    queryset = ModeleVehicule.objects.all().order_by("-created_at")
    serializer_class = ModeleVehiculeSerializer


class VehiculeApiViewSet(viewsets.ModelViewSet):
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_permissions(self):
        if self.action in ["list", "retrieve", "public_list"]:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.action in ["list", "review_queue", "public_list"]:
            return VehiculeCardSerializer
        return VehiculeSerializer

    def get_queryset(self):
        return (
            Vehicule.objects.all()
            .annotate(
                _reservation_count=Count(
                    "reservations",
                    filter=Q(
                        reservations__status__in=PUBLIC_COUNTED_RESERVATION_STATUSES
                    ),
                    distinct=True,
                )
            )
            .select_related(
                "proprietaire",
                "marque",
                "modele",
                "categorie",
                "transmission",
                "type_carburant",
                "statut",
                "driver",
                "reviewed_by",
            )
            .prefetch_related(
                "photos",
                "equipements",
                "included_equipments",
                "availabilities",
                "pricing_grid",
                "documents",
            )
            .order_by("-created_at")
        )

    @staticmethod
    def _attach_reservation_count(items):
        for item in items:
            computed = getattr(item, "_reservation_count", None)
            if computed is None:
                computed = getattr(item, "valid_reservations_count", None)
            if computed is not None:
                item.nombre_locations = int(computed)
        return items

    def _can_manage_vehicle(self, user, vehicle):
        if is_staff_user(user):
            return True
        return bool(user.is_authenticated and vehicle.proprietaire_id == user.id)

    def _staff_users(self):
        return User.objects.filter(
            Q(role="ADMIN") | Q(role="SUPPORT") | Q(is_staff=True)
        ).distinct()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        type_vehicule = request.query_params.get("type_vehicule")
        if type_vehicule:
            queryset = queryset.filter(type_vehicule=type_vehicule)

        est_sponsorise = request.query_params.get("est_sponsorise")
        if est_sponsorise is not None:
            queryset = queryset.filter(
                est_sponsorise=str(est_sponsorise).lower() in ["1", "true", "yes"]
            )

        est_disponible = request.query_params.get("est_disponible")
        if est_disponible is not None:
            queryset = queryset.filter(
                est_disponible=str(est_disponible).lower() in ["1", "true", "yes"]
            )

        est_coup_de_coeur = request.query_params.get("est_coup_de_coeur")
        if est_coup_de_coeur is not None:
            queryset = queryset.filter(
                est_coup_de_coeur=str(est_coup_de_coeur).lower() in ["1", "true", "yes"]
            )

        valide = request.query_params.get("valide")
        if valide is not None:
            queryset = queryset.filter(valide=str(valide).lower() in ["1", "true", "yes"])

        workflow_status = request.query_params.get("workflow_status")
        if workflow_status:
            queryset = queryset.filter(workflow_status=workflow_status)

        page = self.paginate_queryset(queryset)
        if page is not None:
            page = self._attach_reservation_count(page)
            serializer = self.get_serializer(
                page, many=True, context={"request": request}
            )
            return self.get_paginated_response(serializer.data)

        queryset = self._attach_reservation_count(queryset)
        serializer = self.get_serializer(
            queryset, many=True, context={"request": request}
        )
        return Response(serializer.data)

    @action(
        detail=False,
        methods=["get"],
        url_path="public-list",
        permission_classes=[permissions.AllowAny],
    )
    def public_list(self, request):
        queryset = filter_publicly_visible(self.get_queryset())

        type_vehicule = request.query_params.get("type_vehicule")
        if type_vehicule:
            queryset = queryset.filter(type_vehicule=type_vehicule)

        est_sponsorise = request.query_params.get("est_sponsorise")
        if est_sponsorise is not None:
            queryset = queryset.filter(
                est_sponsorise=str(est_sponsorise).lower() in ["1", "true", "yes"]
            )

        est_disponible = request.query_params.get("est_disponible")
        if est_disponible is not None:
            queryset = queryset.filter(
                est_disponible=str(est_disponible).lower() in ["1", "true", "yes"]
            )

        est_coup_de_coeur = request.query_params.get("est_coup_de_coeur")
        if est_coup_de_coeur is not None:
            queryset = queryset.filter(
                est_coup_de_coeur=str(est_coup_de_coeur).lower() in ["1", "true", "yes"]
            )

        page = self.paginate_queryset(queryset)
        if page is not None:
            page = self._attach_reservation_count(page)
            serializer = VehiculeCardSerializer(
                page, many=True, context={"request": request}
            )
            return self.get_paginated_response(serializer.data)

        queryset = self._attach_reservation_count(queryset)
        serializer = VehiculeCardSerializer(
            queryset, many=True, context={"request": request}
        )
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)

        vehicle_id = response.data.get("id")
        if vehicle_id:
            vehicle = Vehicule.objects.select_related("proprietaire").get(id=vehicle_id)
            staff_users = self._staff_users()

            notify_users(
                staff_users,
                notification_type=Notification.NotificationType.VEHICLE,
                title="Nouveau véhicule créé",
                body=f"Le prestataire {vehicle.proprietaire.full_name or vehicle.proprietaire.email} a créé le véhicule « {vehicle.titre} ».",
                vehicle=vehicle,
                action_url_builder=lambda user: build_vehicle_action_url(user, vehicle),
                extra_data={"event": "VEHICLE_CREATED"},
            )

        return response

    def perform_create(self, serializer):
        serializer.save(
            proprietaire=self.request.user,
            valide=False,
            workflow_status=Vehicule.WorkflowStatus.DRAFT,
            review_comment="",
            reviewed_by=None,
            reviewed_at=None,
            submitted_at=None,
            published_at=None,
            est_certifie=False,
            est_sponsorise=False,
            est_coup_de_coeur=False,
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, context={"request": request})
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not self._can_manage_vehicle(request.user, instance):
            return Response(
                {"detail": "Accès interdit."}, status=status.HTTP_403_FORBIDDEN
            )

        kwargs["partial"] = True
        response = super().update(request, *args, **kwargs)

        if not is_staff_user(request.user):
            instance.refresh_from_db()
            reset_vehicle_review_state(instance)

        return response

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not self._can_manage_vehicle(request.user, instance):
            return Response(
                {"detail": "Accès interdit."}, status=status.HTTP_403_FORBIDDEN
            )

        response = super().partial_update(request, *args, **kwargs)

        if not is_staff_user(request.user):
            instance.refresh_from_db()
            if any(
                k in request.data
                for k in [
                    "titre",
                    "description",
                    "conditions_particulieres",
                    "marque",
                    "modele",
                    "categorie",
                    "transmission",
                    "type_carburant",
                    "statut",
                    "annee",
                    "numero_immatriculation",
                    "numero_serie",
                ]
            ):
                reset_vehicle_review_state(instance)

        return response

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not self._can_manage_vehicle(request.user, instance):
            return Response(
                {"detail": "Accès interdit."}, status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)

    def _sync_vehicle_favorites_count(self, vehicle_id):
        total = VehiculeFavorite.objects.filter(vehicle_id=vehicle_id).count()
        Vehicule.objects.filter(id=vehicle_id).update(nombre_favoris=total)

    @action(
        detail=False,
        methods=["get"],
        url_path="favorites",
        permission_classes=[permissions.IsAuthenticated],
    )
    def favorites(self, request):
        favorite_vehicle_ids = list(
            VehiculeFavorite.objects.filter(user=request.user).values_list(
                "vehicle_id", flat=True
            )
        )

        qs = self.get_queryset().filter(id__in=favorite_vehicle_ids)

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = VehiculeCardSerializer(
                page, many=True, context={"request": request}
            )
            return self.get_paginated_response(serializer.data)

        serializer = VehiculeCardSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=["get"],
        url_path="favorites-ids",
        permission_classes=[permissions.IsAuthenticated],
    )
    def favorites_ids(self, request):
        favorite_vehicle_ids = list(
            VehiculeFavorite.objects.filter(user=request.user).values_list(
                "vehicle_id", flat=True
            )
        )
        return Response({"vehicle_ids": favorite_vehicle_ids}, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["post", "delete"],
        url_path="favorite",
        permission_classes=[permissions.IsAuthenticated],
    )
    def favorite(self, request, pk=None):
        vehicle = self.get_object()

        if request.method == "POST":
            _, created = VehiculeFavorite.objects.get_or_create(
                user=request.user,
                vehicle=vehicle,
            )
            self._sync_vehicle_favorites_count(vehicle.id)
            return Response(
                {
                    "is_favorite": True,
                    "created": created,
                    "message": "Véhicule ajouté aux favoris.",
                },
                status=status.HTTP_200_OK,
            )

        deleted_count, _ = VehiculeFavorite.objects.filter(
            user=request.user,
            vehicle=vehicle,
        ).delete()
        self._sync_vehicle_favorites_count(vehicle.id)
        return Response(
            {
                "is_favorite": False,
                "deleted": deleted_count > 0,
                "message": "Véhicule retiré des favoris.",
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=False,
        methods=["get"],
        url_path="review-queue",
        permission_classes=[permissions.IsAuthenticated],
    )
    def review_queue(self, request):
        if not is_staff_user(request.user):
            return Response(
                {"detail": "Accès interdit."}, status=status.HTTP_403_FORBIDDEN
            )

        queryset = self.get_queryset()

        workflow_status = request.query_params.get("workflow_status")
        if workflow_status:
            queryset = queryset.filter(workflow_status=workflow_status)

        valide = request.query_params.get("valide")
        if valide is not None:
            queryset = queryset.filter(valide=str(valide).lower() in ["1", "true", "yes"])

        page = self.paginate_queryset(queryset)
        if page is not None:
            page = self._attach_reservation_count(page)
            serializer = VehiculeCardSerializer(
                page, many=True, context={"request": request}
            )
            return self.get_paginated_response(serializer.data)

        queryset = self._attach_reservation_count(queryset)
        serializer = VehiculeCardSerializer(
            queryset, many=True, context={"request": request}
        )
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["post"],
        url_path="submit-for-review",
        permission_classes=[permissions.IsAuthenticated],
    )
    def submit_for_review(self, request, pk=None):
        vehicle = self.get_object()

        if vehicle.proprietaire_id != request.user.id and not is_staff_user(request.user):
            return Response(
                {"detail": "Accès interdit."}, status=status.HTTP_403_FORBIDDEN
            )

        latest_doc = vehicle.latest_documents
        if not latest_doc:
            return Response(
                {"detail": "Aucun document véhicule n'a été soumis."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not latest_doc.is_complete:
            return Response(
                {"detail": "Les documents requis ne sont pas encore complets."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()

        vehicle.valide = False
        vehicle.workflow_status = Vehicule.WorkflowStatus.PENDING_REVIEW
        vehicle.review_comment = ""
        vehicle.reviewed_by = None
        vehicle.reviewed_at = None
        vehicle.submitted_at = now
        vehicle.published_at = None
        vehicle.save(
            update_fields=[
                "valide",
                "workflow_status",
                "review_comment",
                "reviewed_by",
                "reviewed_at",
                "submitted_at",
                "published_at",
                "updated_at",
            ]
        )

        latest_doc.is_valide = False
        latest_doc.rejection_reason = ""
        latest_doc.reviewed_by = None
        latest_doc.reviewed_at = None
        latest_doc.submitted_at = now
        latest_doc.save(
            update_fields=[
                "is_valide",
                "rejection_reason",
                "reviewed_by",
                "reviewed_at",
                "submitted_at",
                "updated_at",
            ]
        )

        staff_users = self._staff_users()
        notify_users(
            staff_users,
            notification_type=Notification.NotificationType.VEHICLE_DOCUMENT,
            title="Documents véhicule soumis",
            body=f"Le véhicule « {vehicle.titre} » a été soumis pour validation avec ses documents.",
            vehicle=vehicle,
            vehicle_document=latest_doc,
            action_url_builder=lambda user: build_vehicle_action_url(user, vehicle),
            extra_data={"event": "VEHICLE_SUBMITTED_FOR_REVIEW"},
        )

        serializer = self.get_serializer(vehicle, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["post"],
        url_path="review",
        permission_classes=[permissions.IsAuthenticated],
    )
    def review(self, request, pk=None):
        vehicle = self.get_object()

        if not is_staff_user(request.user):
            return Response(
                {"detail": "Accès interdit."}, status=status.HTTP_403_FORBIDDEN
            )

        decision = str(request.data.get("decision", "")).strip().lower()
        comment = str(request.data.get("comment", "")).strip()

        latest_doc = vehicle.latest_documents
        if not latest_doc:
            return Response(
                {"detail": "Aucun document véhicule à valider."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not latest_doc.is_complete:
            return Response(
                {"detail": "Le dossier documentaire du véhicule est incomplet."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()

        if decision == "approve":
            vehicle.valide = True
            vehicle.workflow_status = Vehicule.WorkflowStatus.PUBLISHED
            vehicle.review_comment = comment
            vehicle.reviewed_by = request.user
            vehicle.reviewed_at = now
            vehicle.published_at = now
            vehicle.save(
                update_fields=[
                    "valide",
                    "workflow_status",
                    "review_comment",
                    "reviewed_by",
                    "reviewed_at",
                    "published_at",
                    "updated_at",
                ]
            )

            latest_doc.is_valide = True
            latest_doc.rejection_reason = ""
            latest_doc.reviewed_by = request.user
            latest_doc.reviewed_at = now
            latest_doc.save(
                update_fields=[
                    "is_valide",
                    "rejection_reason",
                    "reviewed_by",
                    "reviewed_at",
                    "updated_at",
                ]
            )

            notify_users(
                [vehicle.proprietaire],
                notification_type=Notification.NotificationType.VEHICLE,
                title="Véhicule validé",
                body=f"Votre véhicule « {vehicle.titre} » a été validé et publié.",
                vehicle=vehicle,
                vehicle_document=latest_doc,
                action_url_builder=lambda user: build_vehicle_action_url(user, vehicle),
                extra_data={"event": "VEHICLE_APPROVED"},
            )

        elif decision == "reject":
            if not comment:
                return Response(
                    {"detail": "Le motif de rejet est obligatoire."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            vehicle.valide = False
            vehicle.workflow_status = Vehicule.WorkflowStatus.REJECTED
            vehicle.review_comment = comment
            vehicle.reviewed_by = request.user
            vehicle.reviewed_at = now
            vehicle.published_at = None
            vehicle.save(
                update_fields=[
                    "valide",
                    "workflow_status",
                    "review_comment",
                    "reviewed_by",
                    "reviewed_at",
                    "published_at",
                    "updated_at",
                ]
            )

            latest_doc.is_valide = False
            latest_doc.rejection_reason = comment
            latest_doc.reviewed_by = request.user
            latest_doc.reviewed_at = now
            latest_doc.save(
                update_fields=[
                    "is_valide",
                    "rejection_reason",
                    "reviewed_by",
                    "reviewed_at",
                    "updated_at",
                ]
            )

            notify_users(
                [vehicle.proprietaire],
                notification_type=Notification.NotificationType.VEHICLE_DOCUMENT,
                title="Véhicule rejeté",
                body=f"Le véhicule « {vehicle.titre} » a été rejeté. Motif : {comment}",
                vehicle=vehicle,
                vehicle_document=latest_doc,
                action_url_builder=lambda user: build_vehicle_action_url(user, vehicle),
                extra_data={
                    "event": "VEHICLE_REJECTED",
                    "review_comment": comment,
                },
            )

        else:
            return Response(
                {"detail": "Décision invalide. Utilisez 'approve' ou 'reject'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(vehicle, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="Assigne un chauffeur au véhicule",
        request_body=serializers.Serializer,
        responses={200: "Driver assigned successfully", 404: "Driver not found"},
    )
    @action(detail=True, methods=["post"])
    def assign_driver(self, request, pk=None):
        vehicule = self.get_object()

        if not self._can_manage_vehicle(request.user, vehicule):
            return Response({"error": "Accès interdit"}, status=status.HTTP_403_FORBIDDEN)

        driver_id = request.data.get("driver_id")

        if not driver_id:
            return Response(
                {"error": "driver_id est requis"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            driver = Driver.objects.get(id=driver_id)
        except Driver.DoesNotExist:
            return Response(
                {"error": "Chauffeur introuvable"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not is_staff_user(request.user) and driver.owner != request.user:
            return Response(
                {"error": "Vous n'avez pas la permission d'assigner ce chauffeur"},
                status=status.HTTP_403_FORBIDDEN,
            )

        vehicule.driver = driver
        vehicule.save(update_fields=["driver"])

        return Response({"message": f"Chauffeur {driver.full_name} assigné avec succès"})

    @action(detail=True, methods=["post"])
    def remove_driver(self, request, pk=None):
        vehicule = self.get_object()

        if not self._can_manage_vehicle(request.user, vehicule):
            return Response({"error": "Accès interdit"}, status=status.HTTP_403_FORBIDDEN)

        if vehicule.driver:
            vehicule.driver = None
            vehicule.save(update_fields=["driver"])
            return Response({"message": "Chauffeur retiré avec succès"})

        return Response({"message": "Aucun chauffeur assigné à ce véhicule"})

    @action(
        detail=True,
        methods=["get", "put", "patch"],
        url_path="condition-report",
        permission_classes=[permissions.IsAuthenticated],
    )
    def condition_report(self, request, pk=None):
        vehicle = self.get_object()
        user = request.user
        user_role = getattr(user, "role", None)

        is_owner_or_staff = (
            vehicle.proprietaire_id == user.id
            or user_role in ["ADMIN", "SUPPORT"]
            or user.is_staff
        )
        has_client_reservation = False

        if user_role == "CLIENT":
            has_client_reservation = Reservation.objects.filter(
                vehicle=vehicle,
                client=user,
            ).exists()

        if request.method == "GET":
            if not is_owner_or_staff and not has_client_reservation:
                return Response(
                    {"detail": "Vous n'avez pas la permission de consulter ce rapport."},
                    status=status.HTTP_403_FORBIDDEN,
                )
        elif not is_owner_or_staff:
            return Response(
                {"detail": "Vous n'avez pas la permission de modifier ce rapport."},
                status=status.HTTP_403_FORBIDDEN,
            )

        report, _ = VehicleConditionReport.objects.get_or_create(
            vehicle=vehicle,
            defaults={"created_by": user},
        )

        if request.method == "GET":
            serializer = VehicleConditionReportSerializer(
                report,
                context={"request": request},
            )
            return Response(serializer.data, status=status.HTTP_200_OK)

        serializer = VehicleConditionReportSerializer(
            report,
            data=request.data,
            partial=(request.method == "PATCH"),
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(created_by=report.created_by or user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class VehicleEquipmentApiViewset(viewsets.ModelViewSet):
    queryset = VehicleEquipments.objects.all().order_by("-created_at")
    serializer_class = VehicleEquipmentsSerializer


class IncludedEquipmentApiViewset(viewsets.ModelViewSet):
    queryset = IncludedEquipment.objects.all().order_by("-created_at")
    serializer_class = IncludedEquipmentSerializer


class VehiclePhotoViewSet(viewsets.ModelViewSet):
    queryset = VehiclePhoto.objects.all().order_by("order")
    serializer_class = VehiclePhotoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def _can_manage_photo(self, user, photo):
        return is_staff_user(user) or photo.vehicle.proprietaire_id == user.id

    def create(self, request, *args, **kwargs):
        files = request.FILES.getlist("image")
        vehicle_id = request.data.get("vehicle")
        vehicle = get_object_or_404(Vehicule, id=vehicle_id)

        if not (
            is_staff_user(request.user) or vehicle.proprietaire_id == request.user.id
        ):
            return Response(
                {"detail": "Accès interdit."}, status=status.HTTP_403_FORBIDDEN
            )

        if len(files) > 1:
            photos = []

            for index, file in enumerate(files):
                photo = VehiclePhoto.objects.create(
                    vehicle_id=vehicle_id,
                    image=file,
                    caption=request.data.get("caption", ""),
                    order=request.data.get("order", index),
                )
                photos.append(photo)

            serializer = self.get_serializer(
                photos, many=True, context={"request": request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return super().create(request, *args, **kwargs)

    def perform_update(self, serializer):
        instance = serializer.instance
        if not self._can_manage_photo(self.request.user, instance):
            raise serializers.ValidationError("Accès interdit.")
        instance = serializer.save()
        if instance.is_primary:
            VehiclePhoto.objects.filter(vehicle=instance.vehicle).exclude(
                id=instance.id
            ).update(is_primary=False)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not self._can_manage_photo(request.user, instance):
            return Response(
                {"detail": "Accès interdit."}, status=status.HTTP_403_FORBIDDEN
            )

        if instance.image:
            delete_file(instance.image.url)
        return super().destroy(request, *args, **kwargs)


class VehiculeSearchApiViewSet(viewsets.ModelViewSet):
    queryset = (
        Vehicule.objects.all()
        .select_related(
            "proprietaire",
            "marque",
            "modele",
            "categorie",
            "transmission",
            "type_carburant",
            "statut",
        )
        .prefetch_related(
            "photos",
            "equipements",
            "included_equipments",
            "availabilities",
            "pricing_grid",
            "documents",
        )
        .order_by("-created_at")
    )
    serializer_class = VehiculeSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return filter_publicly_visible(super().get_queryset())

    @action(detail=False, methods=["get"], url_path="sponsored")
    def sponsored(self, request):
        qs = (
            self.get_queryset()
            .filter(est_sponsorise=True)
            .order_by(
                "-nombre_favoris",
                "-note_moyenne",
                "-valid_reservations_count",
                "-published_at",
            )
        )

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = VehiculeSearchSerializer(
                page, many=True, context={"request": request}
            )
            return self.get_paginated_response(serializer.data)

        serializer = VehiculeSearchSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="popular")
    def popular(self, request):
        qs = (
            self.get_queryset()
            .filter(valid_reservations_count__gte=POPULAR_MIN_RESERVATIONS)
            .order_by(
                "-valid_reservations_count",
                "-note_moyenne",
                "-nombre_favoris",
                "-published_at",
            )
        )

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = VehiculeSearchSerializer(
                page, many=True, context={"request": request}
            )
            return self.get_paginated_response(serializer.data)

        serializer = VehiculeSearchSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="coup-de-coeur")
    def coup_de_coeur(self, request):
        min_note = float(request.query_params.get("min_note", 4))
        min_favoris = int(request.query_params.get("min_favoris", 5))

        coups_de_coeur_qs = (
            self.get_queryset()
            .filter(est_coup_de_coeur=True)
            .order_by(
                "-note_moyenne",
                "-nombre_favoris",
                "-valid_reservations_count",
                "-published_at",
            )
        )

        qs = coups_de_coeur_qs
        if not coups_de_coeur_qs.exists():
            qs = (
                self.get_queryset()
                .filter(
                    est_certifie=True,
                    note_moyenne__gte=min_note,
                    nombre_favoris__gte=min_favoris,
                )
                .order_by(
                    "-note_moyenne",
                    "-nombre_favoris",
                    "-valid_reservations_count",
                    "-published_at",
                )
            )

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = VehiculeSearchSerializer(
                page, many=True, context={"request": request}
            )
            return self.get_paginated_response(serializer.data)

        serializer = VehiculeSearchSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="most-booked")
    def most_booked(self, request):
        qs = (
            self.get_queryset()
            .filter(valid_reservations_count__gte=POPULAR_MIN_RESERVATIONS)
            .order_by(
                "-valid_reservations_count",
                "-note_moyenne",
                "-nombre_favoris",
                "-published_at",
            )
        )

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = VehiculeSearchSerializer(
                page, many=True, context={"request": request}
            )
            return self.get_paginated_response(serializer.data)

        serializer = VehiculeSearchSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="search")
    def search(self, request):
        qs = self.get_queryset()

        marque_id = request.query_params.get("marque")
        modele_id = request.query_params.get("modele")
        categorie_id = request.query_params.get("categorie")
        ville = request.query_params.get("ville")
        min_price = request.query_params.get("min_price")
        max_price = request.query_params.get("max_price")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        type_vehicule = request.query_params.get("type_vehicule")

        if marque_id:
            try:
                uuid.UUID(str(marque_id))
                qs = qs.filter(marque_id=marque_id)
            except ValueError:
                qs = qs.filter(marque__nom__icontains=marque_id)

        if modele_id:
            try:
                uuid.UUID(str(modele_id))
                qs = qs.filter(modele_id=modele_id)
            except ValueError:
                qs = qs.filter(modele__label__icontains=modele_id)

        if categorie_id:
            try:
                uuid.UUID(str(categorie_id))
                qs = qs.filter(categorie_id=categorie_id)
            except ValueError:
                qs = qs.filter(categorie__nom__icontains=categorie_id)

        if type_vehicule:
            qs = qs.filter(type_vehicule=type_vehicule)

        if ville:
            qs = qs.filter(ville__icontains=ville)

        if min_price:
            qs = qs.filter(
                pricing_grid__zone_type="URBAIN",
                pricing_grid__prix_jour__gte=min_price,
            )

        if max_price:
            qs = qs.filter(
                pricing_grid__zone_type="URBAIN",
                pricing_grid__prix_jour__lte=max_price,
            )

        if start_date and end_date:
            start_dt = parse_datetime(start_date)
            end_dt = parse_datetime(end_date)

            if start_dt and end_dt and start_dt < end_dt:
                qs = qs.exclude(
                    reservations__status__in=[
                        Reservation.Status.PENDING,
                        Reservation.Status.CONFIRMED,
                        Reservation.Status.IN_PROGRESS,
                    ],
                    reservations__start_datetime__lt=end_dt,
                    reservations__end_datetime__gt=start_dt,
                ).exclude(
                    availabilities__type__in=[
                        VehicleAvailability.AvailabilityType.BLOCKED,
                        VehicleAvailability.AvailabilityType.RESERVED,
                        VehicleAvailability.AvailabilityType.MAINTENANCE,
                    ],
                    availabilities__start_date__lte=end_dt.date(),
                    availabilities__end_date__gte=start_dt.date(),
                )

        qs = qs.distinct().order_by("-published_at", "-created_at")

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = VehiculeSearchSerializer(
                page, many=True, context={"request": request}
            )
            return self.get_paginated_response(serializer.data)

        serializer = VehiculeSearchSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
def getVehculeClient(request, user_id):
    if not request.user.is_authenticated:
        return Response(
            {"detail": "Authentification requise."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    user = get_object_or_404(User, id=user_id)

    if not is_staff_user(request.user) and request.user.id != user.id:
        return Response(
            {"detail": "Accès interdit."}, status=status.HTTP_403_FORBIDDEN
        )

    clients = User.objects.filter(reservations__vehicle__proprietaire=user).distinct()

    serializer = UserProfileSerializer(clients, many=True)
    return Response(serializer.data)


@api_view(["GET"])
def getAllMyVehicles(request, user_id):
    if not request.user.is_authenticated:
        return Response(
            {"detail": "Authentification requise."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    user = get_object_or_404(User, id=user_id)

    if not is_staff_user(request.user) and request.user.id != user.id:
        return Response(
            {"detail": "Accès interdit."}, status=status.HTTP_403_FORBIDDEN
        )

    vehicule_data = (
        Vehicule.objects.filter(proprietaire=user)
        .annotate(
            _reservation_count=Count(
                "reservations",
                filter=Q(
                    reservations__status__in=PUBLIC_COUNTED_RESERVATION_STATUSES
                ),
                distinct=True,
            )
        )
        .select_related(
            "marque",
            "modele",
            "transmission",
            "type_carburant",
            "reviewed_by",
        )
        .prefetch_related(
            "photos",
            "pricing_grid",
            "driver",
            "documents",
        )
        .order_by("-created_at")
    )

    for vehicle in vehicule_data:
        computed = getattr(vehicle, "_reservation_count", None)
        if computed is not None:
            vehicle.nombre_locations = int(computed)

    serializer = VehiculeCardSerializer(
        vehicule_data,
        many=True,
        context={"request": request},
    )
    return Response(serializer.data)


@api_view(["GET"])
def getVehiculeByCategory(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    vehicule_data = filter_publicly_visible(
        Vehicule.objects.filter(categorie=category)
        .select_related(
            "marque",
            "modele",
            "categorie",
            "transmission",
            "type_carburant",
            "statut",
            "proprietaire",
        )
        .prefetch_related(
            "equipements",
            "included_equipments",
            "photos",
            "availabilities",
            "pricing_grid",
            "documents",
        )
        .order_by("-created_at")
    )

    serializer = VehiculeCardSerializer(
        vehicule_data,
        many=True,
        context={"request": request},
    )
    return Response(serializer.data)


class VehicleAvailabilityViewSet(viewsets.ModelViewSet):
    queryset = VehicleAvailability.objects.all()
    serializer_class = VehicleAvailabilitySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        vehicle_id = self.request.query_params.get("vehicle")
        qs = super().get_queryset()

        if not is_staff_user(self.request.user):
            qs = qs.filter(vehicle__proprietaire=self.request.user)

        if vehicle_id:
            qs = qs.filter(vehicle_id=vehicle_id)

        return qs

    def perform_create(self, serializer):
        vehicle = serializer.validated_data["vehicle"]
        if not (
            is_staff_user(self.request.user)
            or vehicle.proprietaire_id == self.request.user.id
        ):
            raise serializers.ValidationError("Accès interdit.")
        serializer.save()

    def perform_update(self, serializer):
        vehicle = serializer.instance.vehicle
        if not (
            is_staff_user(self.request.user)
            or vehicle.proprietaire_id == self.request.user.id
        ):
            raise serializers.ValidationError("Accès interdit.")
        serializer.save()


class VehicleDocumentsViewSet(viewsets.ModelViewSet):
    queryset = VehicleDocuments.objects.all().select_related("vehicle", "reviewed_by")
    serializer_class = VehicleDocumentsSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        vehicle_id = self.request.query_params.get("vehicle")

        if not is_staff_user(self.request.user):
            qs = qs.filter(vehicle__proprietaire=self.request.user)

        if vehicle_id:
            qs = qs.filter(vehicle=vehicle_id)

        return qs.order_by("-updated_at")

    def create(self, request, *args, **kwargs):
        vehicle_id = request.data.get("vehicle")
        vehicle = get_object_or_404(Vehicule, id=vehicle_id)

        if not (
            is_staff_user(request.user) or vehicle.proprietaire_id == request.user.id
        ):
            return Response(
                {"detail": "Accès interdit."}, status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        if is_staff_user(request.user):
            document = serializer.save()
        else:
            document = serializer.save(
                is_valide=False,
                rejection_reason="",
                reviewed_by=None,
                reviewed_at=None,
                submitted_at=None,
            )
            reset_vehicle_review_state(vehicle)

        headers = self.get_success_headers(serializer.data)
        output = self.get_serializer(document, context={"request": request}).data
        return Response(output, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        instance = self.get_object()

        if not (
            is_staff_user(request.user)
            or instance.vehicle.proprietaire_id == request.user.id
        ):
            return Response(
                {"detail": "Accès interdit."}, status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        if is_staff_user(request.user):
            document = serializer.save()
        else:
            document = serializer.save(
                is_valide=False,
                rejection_reason="",
                reviewed_by=None,
                reviewed_at=None,
                submitted_at=None,
            )
            reset_vehicle_review_state(instance.vehicle)

        return Response(
            self.get_serializer(document, context={"request": request}).data
        )

    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    @action(
        detail=True,
        methods=["post"],
        url_path="review",
        permission_classes=[permissions.IsAuthenticated],
    )
    def review(self, request, pk=None):
        document = self.get_object()

        if not is_staff_user(request.user):
            return Response(
                {"detail": "Accès interdit."}, status=status.HTTP_403_FORBIDDEN
            )

        action_value = str(request.data.get("action", "")).strip().lower()
        rejection_reason = str(request.data.get("rejection_reason", "")).strip()
        now = timezone.now()

        if action_value == "approve":
            if not document.is_complete:
                return Response(
                    {"detail": "Les documents requis ne sont pas encore complets."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            document.is_valide = True
            document.rejection_reason = ""
            document.reviewed_by = request.user
            document.reviewed_at = now
            if not document.submitted_at:
                document.submitted_at = now
            document.save(
                update_fields=[
                    "is_valide",
                    "rejection_reason",
                    "reviewed_by",
                    "reviewed_at",
                    "submitted_at",
                    "updated_at",
                ]
            )

            notify_users(
                [document.vehicle.proprietaire],
                notification_type=Notification.NotificationType.VEHICLE_DOCUMENT,
                title="Documents validés",
                body=f"Les documents du véhicule « {document.vehicle.titre} » ont été validés.",
                vehicle=document.vehicle,
                vehicle_document=document,
                action_url_builder=lambda user: build_vehicle_action_url(
                    user, document.vehicle
                ),
                extra_data={"event": "VEHICLE_DOCUMENTS_APPROVED"},
            )

        elif action_value == "reject":
            if not rejection_reason:
                return Response(
                    {"detail": "Le motif de rejet est obligatoire."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            document.is_valide = False
            document.rejection_reason = rejection_reason
            document.reviewed_by = request.user
            document.reviewed_at = now
            if not document.submitted_at:
                document.submitted_at = now
            document.save(
                update_fields=[
                    "is_valide",
                    "rejection_reason",
                    "reviewed_by",
                    "reviewed_at",
                    "submitted_at",
                    "updated_at",
                ]
            )

            vehicle = document.vehicle
            vehicle.valide = False
            vehicle.workflow_status = Vehicule.WorkflowStatus.REJECTED
            vehicle.review_comment = rejection_reason
            vehicle.reviewed_by = request.user
            vehicle.reviewed_at = now
            vehicle.published_at = None
            vehicle.save(
                update_fields=[
                    "valide",
                    "workflow_status",
                    "review_comment",
                    "reviewed_by",
                    "reviewed_at",
                    "published_at",
                    "updated_at",
                ]
            )

            notify_users(
                [vehicle.proprietaire],
                notification_type=Notification.NotificationType.VEHICLE_DOCUMENT,
                title="Documents rejetés",
                body=f"Les documents du véhicule « {vehicle.titre} » ont été rejetés. Motif : {rejection_reason}",
                vehicle=vehicle,
                vehicle_document=document,
                action_url_builder=lambda user: build_vehicle_action_url(user, vehicle),
                extra_data={
                    "event": "VEHICLE_DOCUMENTS_REJECTED",
                    "rejection_reason": rejection_reason,
                },
            )
        else:
            return Response(
                {"detail": "Action invalide. Utilisez 'approve' ou 'reject'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(document, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class VehiclePhotoUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, vehicle_id):
        vehicle = get_object_or_404(Vehicule, id=vehicle_id)

        if not (
            is_staff_user(request.user) or vehicle.proprietaire_id == request.user.id
        ):
            return Response(
                {"detail": "Accès interdit."}, status=status.HTTP_403_FORBIDDEN
            )

        serializer = VehiclePhotoUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        photos = serializer.validated_data["photos"]

        if vehicle.photos.count() + len(photos) > 5:
            return Response(
                {"detail": "Maximum 5 photos par véhicule"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            base_order = vehicle.photos.count()
            for idx, photo in enumerate(photos):
                VehiclePhoto.objects.create(
                    vehicle=vehicle,
                    image=photo,
                    order=base_order + idx,
                )

        return Response({"success": True}, status=status.HTTP_201_CREATED)


class VehiclePhotoDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, photo_id):
        photo = get_object_or_404(VehiclePhoto, id=photo_id)

        if not (
            is_staff_user(request.user) or photo.vehicle.proprietaire_id == request.user.id
        ):
            return Response(
                {"detail": "Accès interdit."}, status=status.HTTP_403_FORBIDDEN
            )

        if photo.image:
            try:
                delete_file(photo.image.url)
            except Exception:
                pass

        photo.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
