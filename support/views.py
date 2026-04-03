from drf_yasg.utils import swagger_auto_schema
from rest_framework import decorators, permissions, response, status, viewsets
from rest_framework.exceptions import PermissionDenied

from .models import IncidentReport, SupportTicket, TicketMessage
from .serializers import (
    IncidentReportSerializer,
    SupportTicketCreateSerializer,
    SupportTicketDetailSerializer,
    SupportTicketListSerializer,
    SupportTicketStaffUpdateSerializer,
    TicketMessageSerializer,
)


def is_support_staff(user) -> bool:
    return bool(
        user
        and user.is_authenticated
        and (
            getattr(user, "role", None) in ["ADMIN", "SUPPORT"]
            or getattr(user, "is_staff", False)
        )
    )


class IsOwnerOrStaff(permissions.BasePermission):
    """
    - admin/support/staff : accès total aux tickets
    - utilisateur normal : accès uniquement à ses tickets
    """

    def has_object_permission(self, request, view, obj):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if is_support_staff(user):
            return True

        return obj.user_id == user.id


class SupportTicketViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrStaff]
    queryset = (
        SupportTicket.objects.select_related(
            "user",
            "assigned_admin",
            "reservation",
            "vehicule",
        )
        .prefetch_related("messages__sender")
        .order_by("-last_activity_at", "-created_at")
    )

    def get_serializer_class(self):
        if self.action == "list":
            return SupportTicketListSerializer
        if self.action == "retrieve":
            return SupportTicketDetailSerializer
        if self.action == "create":
            return SupportTicketCreateSerializer
        if self.action in ["update", "partial_update"]:
            return SupportTicketStaffUpdateSerializer
        return SupportTicketDetailSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset.none()

        user = self.request.user
        qs = self.queryset

        if not user.is_authenticated:
            return qs.none()

        if not is_support_staff(user):
            qs = qs.filter(user=user)
        else:
            scope = self.request.query_params.get("scope")
            status_param = self.request.query_params.get("status")
            priority_param = self.request.query_params.get("priority")
            ticket_type_param = self.request.query_params.get("ticket_type")
            assigned_admin_param = self.request.query_params.get("assigned_admin")
            reservation_param = self.request.query_params.get("reservation")
            vehicule_param = self.request.query_params.get("vehicule")

            if scope == "mine":
                qs = qs.filter(user=user)
            elif scope == "assigned_to_me":
                qs = qs.filter(assigned_admin=user)

            if status_param:
                qs = qs.filter(status=status_param)

            if priority_param:
                qs = qs.filter(priority=priority_param)

            if ticket_type_param:
                qs = qs.filter(ticket_type=ticket_type_param)

            if assigned_admin_param:
                if assigned_admin_param == "me":
                    qs = qs.filter(assigned_admin=user)
                else:
                    qs = qs.filter(assigned_admin_id=assigned_admin_param)

            if reservation_param:
                qs = qs.filter(reservation_id=reservation_param)

            if vehicule_param:
                qs = qs.filter(vehicule_id=vehicule_param)

        return qs.order_by("-last_activity_at", "-created_at")

    def _ensure_staff_write(self, request):
        if not is_support_staff(request.user):
            raise PermissionDenied("Seul le support peut modifier ou supprimer un ticket.")

    @swagger_auto_schema(operation_summary="Lister les tickets accessibles")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(operation_summary="Obtenir le détail d'un ticket")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(operation_summary="Créer un ticket")
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ticket = serializer.save(
            user=request.user,
            status=SupportTicket.Status.OPEN,
        )

        output = SupportTicketDetailSerializer(
            ticket,
            context=self.get_serializer_context(),
        )
        headers = self.get_success_headers(output.data)
        return response.Response(
            output.data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    @swagger_auto_schema(operation_summary="Mettre à jour un ticket (support uniquement)")
    def update(self, request, *args, **kwargs):
        self._ensure_staff_write(request)
        return self._update_ticket(request, partial=False, *args, **kwargs)

    @swagger_auto_schema(operation_summary="Mettre à jour partiellement un ticket (support uniquement)")
    def partial_update(self, request, *args, **kwargs):
        self._ensure_staff_write(request)
        return self._update_ticket(request, partial=True, *args, **kwargs)

    def _update_ticket(self, request, *args, partial=False, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        output = SupportTicketDetailSerializer(
            instance,
            context=self.get_serializer_context(),
        )
        return response.Response(output.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(operation_summary="Supprimer un ticket (support uniquement)")
    def destroy(self, request, *args, **kwargs):
        self._ensure_staff_write(request)
        return super().destroy(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Marquer un ticket comme résolu",
        operation_description="Passe le ticket en statut RESOLVED.",
    )
    @decorators.action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        self._ensure_staff_write(request)

        ticket = self.get_object()
        ticket.status = SupportTicket.Status.RESOLVED
        ticket.save(update_fields=["status", "updated_at"])

        output = SupportTicketDetailSerializer(
            ticket,
            context=self.get_serializer_context(),
        )
        return response.Response(output.data, status=status.HTTP_200_OK)


class TicketMessageViewSet(viewsets.ModelViewSet):
    """
    Messages de ticket :
    - GET/POST autorisés
    - pas de PATCH/DELETE pour garder l'historique propre
    """
    serializer_class = TicketMessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        qs = TicketMessage.objects.select_related("ticket", "sender")

        ticket_id = self.request.query_params.get("ticket")
        if ticket_id:
            qs = qs.filter(ticket_id=ticket_id)

        if not user.is_authenticated:
            return qs.none()

        if is_support_staff(user):
            include_internal = self.request.query_params.get("include_internal")
            if include_internal in ["0", "false", "False"]:
                qs = qs.filter(is_internal=False)
            return qs.order_by("created_at")

        return qs.filter(ticket__user=user, is_internal=False).order_by("created_at")

    @swagger_auto_schema(operation_summary="Lister les messages accessibles")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(operation_summary="Obtenir le détail d'un message accessible")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(operation_summary="Créer un nouveau message de ticket")
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        user = self.request.user
        ticket = serializer.validated_data["ticket"]
        requested_internal = serializer.validated_data.get("is_internal", False)

        if not is_support_staff(user) and ticket.user_id != user.id:
            raise PermissionDenied("Vous ne pouvez pas répondre à ce ticket.")

        if requested_internal and not is_support_staff(user):
            raise PermissionDenied("Seul le support peut créer une note interne.")

        serializer.save(
            sender=user,
            is_internal=requested_internal if is_support_staff(user) else False,
        )


class IncidentReportViewSet(viewsets.ModelViewSet):
    queryset = IncidentReport.objects.select_related(
        "reservation",
        "reported_by",
        "handled_by",
    )
    serializer_class = IncidentReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(reported_by=self.request.user)

    @decorators.action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        incident = self.get_object()
        incident.mark_resolved(user=request.user)
        return response.Response(self.get_serializer(incident).data)