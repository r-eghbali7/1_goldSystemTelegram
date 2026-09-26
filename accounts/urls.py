from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import VerifyOTPAndLoginView, SendOTPView

app_name = 'accounts'

urlpatterns = [
    # مرحله اول: درخواست ارسال پیامک
    path('send-otp/', SendOTPView.as_view(), name='send-otp'), 
    
    # مرحله دوم: بررسی کد و دریافت توکن JWT
    path('verify-otp/', VerifyOTPAndLoginView.as_view(), name='verify-otp'),
    
    # ریفرش کردن توکن‌ها در صورت انقضای Access Token
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]