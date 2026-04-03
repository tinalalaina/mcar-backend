from rest_framework.routers import DefaultRouter
from prestataire.views import PrestataireViewSet

router = DefaultRouter()
router.register("prestataires", PrestataireViewSet, basename="prestataire")

urlpatterns = router.urls
