from django.urls import path

from .views import LoyaltyDashboardAPIView

urlpatterns = [
    path("loyalty/me/", LoyaltyDashboardAPIView.as_view(), name="loyalty-dashboard"),
]
