from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"support-tickets", views.SupportTicketViewSet, basename="support-ticket")
router.register(r"tickets-message", views.TicketMessageViewSet, basename="ticket-message")

urlpatterns = [
    path("", include(router.urls)),
]