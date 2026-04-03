from rest_framework import viewsets, permissions, filters
from drf_yasg.utils import swagger_auto_schema

from .models import Driver
from .serializers import DriverReadSerializer, DriverWriteSerializer


class DriverViewSet(viewsets.ModelViewSet):
    """
    Gestion des chauffeurs avec optimisation SQL.
    """
    queryset = Driver.objects.select_related("user", "owner")

    def get_queryset(self):
        user = self.request.user
        if getattr(self, "swagger_fake_view", False) or not user.is_authenticated:
            return Driver.objects.none()

        queryset = super().get_queryset()
        
        # Admin filtering
        source = self.request.query_params.get('source')
        if source == 'admin_pool' and (user.is_staff or getattr(user, "role", None) == 'ADMIN'):
            return queryset.filter(owner__isnull=True) | queryset.filter(owner__is_superuser=True)

        if user.is_staff or getattr(user, "role", None) == 'ADMIN':
            return queryset
        
        # Prestataire voit uniquement ses chauffeurs
        if getattr(user, "role", None) == 'PRESTATAIRE':
            return queryset.filter(owner=user)
        
        return queryset.none()
    
    def perform_create(self, serializer):
        # Auto-assign owner
        serializer.save(owner=self.request.user)

    permission_classes = [permissions.IsAuthenticated]

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["first_name", "last_name", "phone_number", "user__email"]
    ordering_fields = ["created_at", "last_name", "experience_years"]

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return DriverReadSerializer
        return DriverWriteSerializer

    @swagger_auto_schema(operation_summary="Lister tous les chauffeurs")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(operation_summary="Créer un chauffeur")
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(operation_summary="Détails d’un chauffeur")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(operation_summary="Modifier un chauffeur")
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(operation_summary="Modifier partiellement un chauffeur")
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(operation_summary="Supprimer un chauffeur")
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
