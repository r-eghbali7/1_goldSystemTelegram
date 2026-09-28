from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from core.tenant import set_current_store
from stores.models import Store

class SellerBaseViewSet(viewsets.ModelViewSet):
    """
    کلاس پایه برای تمام APIهای داشبورد فروشندگان.
    دسترسی‌ها را چک می‌کند و کانتکست فروشگاه را ست می‌کند.
    """
    permission_classes = [IsAuthenticated]

    def initial(self, request, *args, **kwargs):
        # اجرای احراز هویت پیش‌فرض DRF (بررسی توکن JWT)
        super().initial(request, *args, **kwargs)
        
        # پیدا کردن فروشگاهی که متعلق به این کاربر است
        try:
            # فرض بر این است که هر کاربر فعلاً یک فروشگاه دارد
            store = Store.objects.get(owner=request.user)
            
            # 👈 جادوی Multi-Tenancy: تنظیم آیدی فروشگاه برای این ریکوئست
            set_current_store(store.id)
            
        except Store.DoesNotExist:
            raise PermissionDenied("شما هیچ فروشگاهی برای مدیریت ندارید.")


from products.models import Product
from orders.models import Order
from api.serializers import ProductSerializer
# فرض می‌کنیم OrderSerializer را ساخته‌اید
# from api.serializers import OrderSerializer 

class DashboardProductViewSet(SellerBaseViewSet):
    serializer_class = ProductSerializer
    
    # 👈 TenantManager به طور خودکار فقط محصولات این فروشگاه را برمی‌گرداند
    queryset = Product.objects.all().order_by('-created_at')


class DashboardOrderViewSet(SellerBaseViewSet):
    # serializer_class = OrderSerializer
    
    # 👈 فقط سفارشات مربوط به فروشگاه همین شخص لیست می‌شود
    queryset = Order.objects.all().order_by('-created_at')