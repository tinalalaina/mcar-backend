from rest_framework import viewsets, permissions
from rest_framework.parsers import FormParser, MultiPartParser, JSONParser
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Prestataire
from .serializers import PrestataireSerializer


class PrestataireViewSet(viewsets.ModelViewSet):
    queryset = Prestataire.objects.select_related("user", "validated_by")
    serializer_class = PrestataireSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @swagger_auto_schema(
        operation_summary="Lister tous les prestataires",
        operation_description="Retourne la liste de tous les prestataires, avec leurs informations légales et statut.",
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Obtenir un prestataire",
        operation_description="Retourne les détails d'un prestataire spécifique.",
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Créer un compte prestataire",
        operation_description=(
            "Lors de l’inscription, le prestataire est automatiquement lié à l'utilisateur connecté "
            "et mis en statut 'PENDING_VERIFICATION'."
        ),
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        prestataire = serializer.save(user=self.request.user)

        if not prestataire.user.is_company:
            prestataire.user.is_company = True
            prestataire.user.save(update_fields=["is_company"])

    @swagger_auto_schema(
        operation_summary="Mettre à jour un prestataire",
        operation_description=(
            "Permet la mise à jour des informations d'un prestataire. "
            "Si un ADMIN ou SUPPORT modifie le statut, la validation est enregistrée."
        ),
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Mise à jour partielle d'un prestataire",
        operation_description=(
            "Similaire à update, mais permet d'envoyer uniquement les champs modifiés. "
            "Si le statut est changé par ADMIN/SUPPORT, le prestataire est marqué comme validé."
        ),
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    def perform_update(self, serializer):
        prestataire = serializer.save()

        if not prestataire.user.is_company:
            prestataire.user.is_company = True
            prestataire.user.save(update_fields=["is_company"])

        if "status" in serializer.validated_data:
            if getattr(self.request.user, "role", None) in ["ADMIN", "SUPPORT"]:
                prestataire.validated_by = self.request.user
                prestataire.save(update_fields=["validated_by"])

    @swagger_auto_schema(
        operation_summary="Supprimer un prestataire",
        operation_description="Supprime définitivement un prestataire.",
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @swagger_auto_schema(
        method="get",
        operation_summary="Obtenir mon profil prestataire",
        operation_description="Retourne le profil prestataire de l'utilisateur connecté.",
        responses={200: PrestataireSerializer()},
    )
    @swagger_auto_schema(
        methods=["put", "patch"],
        operation_summary="Mettre à jour mon profil prestataire",
        operation_description="Met à jour les informations du prestataire lié à l'utilisateur connecté.",
        responses={200: PrestataireSerializer()},
    )
    @action(detail=False, methods=["get", "patch", "put"], url_path="me")
    def me(self, request):
        try:
            prestataire = Prestataire.objects.get(user=request.user)
        except Prestataire.DoesNotExist:
            return Response({"detail": "Aucun profil prestataire trouvé."}, status=404)

        if request.method == "GET":
            serializer = self.get_serializer(prestataire)
            return Response(serializer.data)

        serializer = self.get_serializer(
            prestataire,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)