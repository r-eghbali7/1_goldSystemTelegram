from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LiveRatesAPIView, ProductViewSet

app_name = 'products'

router = DefaultRouter()
router.register(r'', ProductViewSet, basename='product')

urlpatterns = [
    path('rates/', LiveRatesAPIView.as_view(), name='live-rates'),
    path('', include(router.urls)),
]