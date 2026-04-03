from rest_framework.routers import DefaultRouter
from django.urls import path, include
from . import views
from .views import VehiclePhotoUploadView, VehiclePhotoDeleteView

router = DefaultRouter()
router.register(r"marque", views.MarqueViewSet, basename="marque")
router.register(r"category", views.CategoryViewSet, basename="category")
router.register(r"transmission", views.TransmissionViewSet, basename="transmission")
router.register(r"fueltype", views.FuelTypeViewSet, basename="fueltype")
router.register(r"status", views.StatusViewSet, basename="status")
router.register(r"modelevehicule", views.ModeleVehiculeViewSet, basename="modelevehicule")
router.register(r"vehicule", views.VehiculeApiViewSet, basename="VehiculeApi")
router.register(r"equipements", views.VehicleEquipmentApiViewset, basename="VehicleEquipment")
router.register(r"equipements-inclus", views.IncludedEquipmentApiViewset, basename="IncludedEquipment")
router.register(r"vehicle-photos", views.VehiclePhotoViewSet, basename="VehiclePhoto")
router.register(r"vehicule-search", views.VehiculeSearchApiViewSet, basename="search")
router.register(r"vehicle-availability", views.VehicleAvailabilityViewSet, basename="vehicle-availability")
router.register(r"vehicle-documents", views.VehicleDocumentsViewSet, basename="vehicle-documents")

urlpatterns = [
    path("", include(router.urls)),
    path("clients/<str:user_id>/", views.getVehculeClient),
    path("owners/<str:user_id>/", views.getAllMyVehicles),
    path("category-all-vehicules/<str:category_id>/", views.getVehiculeByCategory),
    path(
        "vehicule/<uuid:vehicle_id>/photos/",
        VehiclePhotoUploadView.as_view(),
        name="vehicle-photo-upload",
    ),
    path(
        "vehicle-photo/<uuid:photo_id>/",
        VehiclePhotoDeleteView.as_view(),
        name="vehicle-photo-delete",
    ),
]
