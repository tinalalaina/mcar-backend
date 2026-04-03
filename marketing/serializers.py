# serializers.py
from rest_framework import serializers

from gasycar.utils import delete_file
from .models import MarketingHeros

# serialisers
class MarketingHeroSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketingHeros
        fields = "__all__"

    def update(self, instance, validated_data):
        if "image" in validated_data and instance.image:
            delete_file(instance.image.url)
        return super().update(instance, validated_data)
        
