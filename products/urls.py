from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet

app_name = 'products'

router = DefaultRouter()
# ثبت ویوست محصولات (بدون نیاز به نوشتن دستی مسیرها)
router.register(r'', ProductViewSet, basename='product')

urlpatterns = [
    path('', include(router.urls)),
]