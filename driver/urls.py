from rest_framework.routers import DefaultRouter
from driver.views import DriverViewSet

router = DefaultRouter()
router.register("drivers", DriverViewSet, basename="drivers")

urlpatterns = router.urls
