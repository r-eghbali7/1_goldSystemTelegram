import uuid
from django.db import models
from django.contrib.auth import get_user_model
from products.models import Product
from stores.models import Store

User = get_user_model()

class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'در انتظار پرداخت'),
        ('paid', 'پرداخت شده موفق'),
        ('failed', 'پرداخت ناموفق'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='orders', verbose_name="خریدار")
    store = models.ForeignKey(Store, on_delete=models.PROTECT, related_name='orders', verbose_name="فروشگاه")    
    total_amount = models.DecimalField(max_digits=15, decimal_places=0, verbose_name="مبلغ کل فاکتور (تومان)")
    
    # فیلدهای مربوط به درگاه پرداخت
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending', verbose_name="وضعیت تراکنش")
    authority = models.CharField(max_length=100, null=True, blank=True, verbose_name="کد ارجاع زرین‌پال")
    ref_id = models.CharField(max_length=100, null=True, blank=True, verbose_name="شماره پیگیری (RefID)")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت سفارش")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"فاکتور {self.id} - {self.status}"

class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT) # در صورت حذف محصول، فاکتور از بین نمی‌رود
    
    # ثبت مقادیر پرداخت شده به عنوان یک اسنپ‌شات غیرقابل تغییر
    purchased_price = models.DecimalField(max_digits=15, decimal_places=0, verbose_name="قیمت نهایی پرداخت شده")
    gold_weight = models.FloatField(verbose_name="وزن طلای خریداری شده (گرم)")