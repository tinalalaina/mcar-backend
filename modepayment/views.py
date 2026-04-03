from rest_framework import viewsets
from .models import ModePayment
from .serializers import ModePaymentSerializer
from gasycar.utils import delete_file


class ModePaymentViewSet(viewsets.ModelViewSet):
    queryset = ModePayment.objects.all()
    serializer_class = ModePaymentSerializer

    def perform_update(self, serializer):
        instance = self.get_object()
        old_image = instance.image.path if instance.image else None

        updated_instance = serializer.save()

        if old_image and updated_instance.image and updated_instance.image.path != old_image:
            delete_file(old_image)

        return updated_instance

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.image:
            delete_file(instance.image.path)

        return super().destroy(request, *args, **kwargs)