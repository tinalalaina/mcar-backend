from rest_framework import serializers
from .models import ModePayment


class ModePaymentSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ModePayment
        fields = "__all__"
        extra_kwargs = {
            "image": {"required": False},
        }

    def get_image_url(self, obj):
        request = self.context.get("request")
        if obj.image and hasattr(obj.image, "url"):
            url = obj.image.url
            return request.build_absolute_uri(url) if request else url
        return None
