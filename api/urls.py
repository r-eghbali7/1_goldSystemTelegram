from django.urls import path, include

app_name = 'api'

urlpatterns = [
    path('accounts/', include('accounts.urls')),
    path('products/', include('products.urls')),
    path('carts/', include('carts.urls')),
    path('orders/', include('orders.urls')),
]