from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions

schema_view = get_schema_view(
   openapi.Info(
      title="GasyCar API",
      default_version='v1',
      description="Test description",
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email="contact@snippets.local"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
   
    path('admin/', admin.site.urls),
    path('api/users/', include('users.urls')),
    path('api/', include('notification.urls')),
    path('api/vehicule/', include('vehicule.urls')),  
   path('api/marketing/', include('marketing.urls')),
   # reservations
   path('api/bookings/', include('reservations.urls')),
   path('api/support/', include('support.urls')),
   path('api/reviews/', include('reviews.urls')),
   path('api/', include('blogs.urls')),
   path('api/modepayment/', include('modepayment.urls')),
   path('api/', include('prestataire.urls')),
   path('api/driver/', include('driver.urls')),
   path('api/smsapp/', include('smsapp.urls')),
   path('api/', include('loyalty.urls')),
   
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
