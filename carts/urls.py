from django.urls import path
from .views import CartAPIView

app_name = 'carts'

urlpatterns = [
    # آدرس خالی ('') معادل همان /api/v1/carts/ است که از فایل اصلی ارجاع داده شده است
    path('', CartAPIView.as_view(), name='cart-api'),
]