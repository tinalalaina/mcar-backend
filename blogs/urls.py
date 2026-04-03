
from rest_framework.routers import DefaultRouter
from .views import BlogPostViewSet
from django.urls import path,include

router = DefaultRouter()
router.register("blog-posts", BlogPostViewSet, basename="blog-post")


urlpatterns = [

    path('', include(router.urls)),
]