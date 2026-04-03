#  import drf
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import viewsets
from drf_yasg.utils import swagger_auto_schema

# models
from .models import MarketingHeros
from gasycar.utils import delete_file

# serializers
from .serializers import MarketingHeroSerializer


# CRUD ViewSets with Swagger Documentation
class MarketingHeroViewSet(viewsets.ModelViewSet):
    queryset = MarketingHeros.objects.all().order_by("-created_at")
    serializer_class = MarketingHeroSerializer

    # Similar CRUD methods with swagger_auto_schema can be added here
    @swagger_auto_schema(responses={200: MarketingHeroSerializer(many=True)})
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(responses={200: MarketingHeroSerializer()})
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        request_body=MarketingHeroSerializer, responses={201: MarketingHeroSerializer()}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        request_body=MarketingHeroSerializer, responses={200: MarketingHeroSerializer()}
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(responses={204: "No Content"})
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.image:
            delete_file(instance.image.url)
        return super().destroy(request, *args, **kwargs)
