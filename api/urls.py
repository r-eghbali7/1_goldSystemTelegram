from django.urls import path, include

from api.views import TelegramWebhookView

app_name = 'api'

urlpatterns = [
    path('accounts/', include('accounts.urls')),
    path('products/', include('products.urls')),
    path('carts/', include('carts.urls')),
    path('orders/', include('orders.urls')),
    path('webhook/<str:bot_token>/', TelegramWebhookView.as_view(), name='telegram-webhook'),
]