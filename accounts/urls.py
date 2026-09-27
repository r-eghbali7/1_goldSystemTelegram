from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import TelegramDirectLoginView

app_name = 'accounts'

urlpatterns = [
    # لاگین مستقیم با شماره تلفن ارسالی از ربات
    path('telegram-login/', TelegramDirectLoginView.as_view(), name='telegram-login'),
    
    # ریفرش کردن توکن‌ها در صورت انقضا
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]