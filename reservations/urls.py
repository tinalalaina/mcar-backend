from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

app_name = "bookings"

router = DefaultRouter()
router.register(r"reservations", views.ReservationViewSet, basename="reservation")
router.register(
    r"reservation-payment",
    views.ReservationPaymentViewSet,
    basename="reservation-payment",
)
router.register(
    r"reservation-service",
    views.ReservationServiceViewSet,
    basename="reservation-service",
)

urlpatterns = [
    path("", include(router.urls)),
    path("loyalty/overview/", views.LoyaltyOverviewAPIView.as_view(), name="loyalty-overview"),

    # pricing
    path(
        "pricing-config/",
        views.ReservationPricingConfigAPIView.as_view(),
        name="reservation-pricing-config",
    ),

    # reservations filters
    path(
        "user/<uuid:user_id>/reservations/",
        views.UserReservationsAPIView.as_view(),
        name="user-reservations",
    ),
    path(
        "vehicle/<uuid:vehicle_id>/reservations/",
        views.VehicleReservationsAPIView.as_view(),
        name="vehicle-reservations",
    ),
    path(
        "owner/<uuid:owner_id>/reservations/",
        views.OwnerVehicleReservationsAPIView.as_view(),
        name="owner-vehicle-reservations",
    ),
    path(
        "status/<str:status>/reservations/",
        views.StatusReservationsAPIView.as_view(),
        name="status-reservations",
    ),
    path(
        "active/reservations/",
        views.ActiveReservationsAPIView.as_view(),
        name="active-reservations",
    ),
    path(
        "completed/reservations/",
        views.CompletedReservationsAPIView.as_view(),
        name="completed-reservations",
    ),
    path(
        "date-range/<str:start_date>/<str:end_date>/reservations/",
        views.DateRangeReservationsAPIView.as_view(),
        name="date-range-reservations",
    ),
    path(
        "total-count/reservations/",
        views.TotalReservationsCountAPIView.as_view(),
        name="total-reservations-count",
    ),
    path(
        "total-amount/reservations/",
        views.TotalReservationsAmountAPIView.as_view(),
        name="total-reservations-amount",
    ),
    path(
        "with-chauffeur/reservations/",
        views.ChauffeurReservationsAPIView.as_view(),
        name="with-chauffeur-reservations",
    ),
    path(
        "without-chauffeur/reservations/",
        views.WithoutChauffeurReservationsAPIView.as_view(),
        name="without-chauffeur-reservations",
    ),
    path(
        "pickup-location/<str:pickup_location>/reservations/",
        views.PickupLocationReservationsAPIView.as_view(),
        name="pickup-location-reservations",
    ),
    path(
        "dropoff-location/<str:dropoff_location>/reservations/",
        views.DropoffLocationReservationsAPIView.as_view(),
        name="dropoff-location-reservations",
    ),
    path(
        "min-total-amount/<str:min_amount>/reservations/",
        views.MinTotalAmountReservationsAPIView.as_view(),
        name="min-total-amount-reservations",
    ),
    path(
        "max-total-amount/<str:max_amount>/reservations/",
        views.MaxTotalAmountReservationsAPIView.as_view(),
        name="max-total-amount-reservations",
    ),
    path(
        "min-total-days/<int:min_days>/reservations/",
        views.MinTotalDaysReservationsAPIView.as_view(),
        name="min-total-days-reservations",
    ),

    # reservation services
    path(
        "reservation/<uuid:reservation_id>/services/",
        views.ReservationServiceByReservationAPIView.as_view(),
        name="reservation-service-by-reservation",
    ),
    path(
        "service-type/<str:service_type>/services/",
        views.ReservationServiceByTypeAPIView.as_view(),
        name="reservation-service-by-type",
    ),
    path(
        "service-name/<str:service_name>/services/",
        views.ReservationServiceByNameAPIView.as_view(),
        name="reservation-service-by-name",
    ),
    path(
        "service-price-range/<str:min_price>/<str:max_price>/services/",
        views.ReservationServiceByPriceRangeAPIView.as_view(),
        name="reservation-service-by-price-range",
    ),
    path(
        "min-quantity/<int:min_quantity>/services/",
        views.ReservationServiceByMinQuantityAPIView.as_view(),
        name="reservation-service-by-min-quantity",
    ),
    path(
        "max-quantity/<int:max_quantity>/services/",
        views.ReservationServiceByMaxQuantityAPIView.as_view(),
        name="reservation-service-by-max-quantity",
    ),

    # statistics
    path(
        "statistics/",
        views.ReservationStatisticsAPIView.as_view(),
        name="reservation-statistics",
    ),
    path(
        "daily-income/",
        views.DailyIncomeAPIView.as_view(),
        name="reservation-daily-income",
    ),
    path("stats/day/", views.ReservationStatsViewSet.as_view({"get": "day"})),
    path("stats/week/", views.ReservationStatsViewSet.as_view({"get": "week"})),
    path("stats/month/", views.ReservationStatsViewSet.as_view({"get": "month"})),

    # payment pages / api
    path(
        "<uuid:reservation_id>/and/<uuid:payment_id>/payment/",
        views.reservation_payment_page,
        name="reservation_payment_page",
    ),
    path(
        "payment/submit/",
        views.submit_reservation_payment,
        name="submit_payment",
    ),
    path(
        "send-link-payment/",
        views.send_link_payment,
        name="api_send_link_payment",
    ),
]