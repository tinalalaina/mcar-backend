from rest_framework import serializers


class LoyaltyHistoryItemSerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField()
    date = serializers.DateTimeField()
    points = serializers.IntegerField()
    status = serializers.ChoiceField(choices=["earned", "redeemed", "pending"])
    description = serializers.CharField()
    source = serializers.CharField()


class LoyaltyTierSerializer(serializers.Serializer):
    name = serializers.CharField()
    min_points = serializers.IntegerField()
    max_points = serializers.IntegerField(allow_null=True)
    threshold_label = serializers.CharField()
    perks = serializers.ListField(child=serializers.CharField())
    active = serializers.BooleanField()


class LoyaltyDashboardSerializer(serializers.Serializer):
    title = serializers.CharField()
    subtitle = serializers.CharField()
    points = serializers.IntegerField()
    next_tier_label = serializers.CharField(allow_blank=True)
    points_to_next_tier = serializers.IntegerField()
    progress = serializers.FloatField()
    member_since = serializers.CharField()
    discount_label = serializers.CharField()
    current_tier = serializers.CharField()
    profile_completed = serializers.BooleanField()
    stats = serializers.ListField(child=serializers.DictField())
    history = LoyaltyHistoryItemSerializer(many=True)
    tiers = LoyaltyTierSerializer(many=True)
    earning_rules = serializers.ListField(child=serializers.DictField())
