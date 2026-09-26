from django.urls import path
from .views import CartAPIView

app_name = 'carts'

urlpatterns = [
    # دریافت سبد خرید کاربر یا افزودن آیتم جدید با متد GET و POST
    path('', CartAPIView.as_view(), name='cart-detail'),
]