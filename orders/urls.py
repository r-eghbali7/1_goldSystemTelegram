from django.urls import path
from .views import CheckoutAPIView, zarinpal_callback_view

app_name = 'orders'

urlpatterns = [
    # ساخت فاکتور و دریافت لینک پرداخت
    path('checkout/', CheckoutAPIView.as_view(), name='checkout'),
    
    # آدرس بازگشت از زرین‌پال (همان CALLBACK_URL تنظیم شده در ویو زرین‌پال)
path('payment/callback/', zarinpal_callback_view, name='zarinpal-callback'),
]