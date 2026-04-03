from rest_framework.routers import DefaultRouter
from django.urls import path, include
from modepayment import views

router = DefaultRouter()
router.register("mode-payments", views.ModePaymentViewSet, basename="mode-payment")

urlpatterns = [
    path("", include(router.urls)),
]