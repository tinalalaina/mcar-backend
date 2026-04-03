from django.urls import path, include
from . import views



from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'notifications', views.NotificationViewSet, basename='notification')
router.register(r'ticket-notifications', views.TicketNotificationViewSet, basename='ticket-notification')

urlpatterns = [
    path('', include(router.urls)),
]
