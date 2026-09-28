# api/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.views import TelegramWebhookView
from api.seller_views import DashboardProductViewSet, DashboardOrderViewSet

app_name = 'api'

# 👈 تعریف روتر داشبورد فروشندگان
seller_router = DefaultRouter()
seller_router.register(r'products', DashboardProductViewSet, basename='seller-products')
seller_router.register(r'orders', DashboardOrderViewSet, basename='seller-orders')

urlpatterns = [
    path('accounts/', include('accounts.urls')),
    path('products/', include('products.urls')),
    path('carts/', include('carts.urls')),
    path('orders/', include('orders.urls')),
    path('webhook/<str:bot_token>/', TelegramWebhookView.as_view(), name='telegram-webhook'),
    path('seller/', include(seller_router.urls)), # 👈 اصلاح این خط
]