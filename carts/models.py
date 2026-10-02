import uuid
from datetime import timedelta
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from core.models import TenantModel
from products.models import Product

User = get_user_model()

def get_default_cart_expiration():
    # سبد خرید به صورت پیش‌فرض ۳۰ دقیقه اعتبار دارد
    return timezone.now() + timedelta(minutes=30)

class Cart(TenantModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='carts', verbose_name="کاربر")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین بروزرسانی")
    expires_at = models.DateTimeField(default=get_default_cart_expiration, verbose_name="زمان انقضا")
    is_paid = models.BooleanField(default=False, verbose_name="پرداخت شده")

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at and not self.is_paid

    @property
    def total_cart_price(self):
        if self.is_expired:
            return 0
        return sum(item.final_item_price for item in self.items.all())

    def refresh_expiration(self):
        self.expires_at = get_default_cart_expiration()
        self.save()

    def __str__(self):
        return f"سبد {self.id} - کاربر {self.user.phone_number}"


class CartItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items', verbose_name="سبد خرید")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="محصول")
    
    daily_gold_price = models.DecimalField(
        max_digits=12, decimal_places=0, validators=[MinValueValidator(0)], 
        verbose_name="قیمت روز طلا 18 عیار (زمان ثبت)"
    )
    
    # فیلد wage باید به wage_percent تغییر کرده باشد
    wage_percent = models.FloatField(default=0.0, validators=[MinValueValidator(0.0)], verbose_name="درصد اجرت")
    profit_percent = models.FloatField(default=7.0, validators=[MinValueValidator(0.0)], verbose_name="درصد سود")
    tax_percent = models.FloatField(default=10.0, validators=[MinValueValidator(0.0)], verbose_name="درصد مالیات")
    constant_fee = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name="مبلغ ثابت (سکه)")

    @property
    def product_type(self):
        return self.product.product_type

    @property
    def raw_gold_value(self):
        return float(self.product.weight) * float(self.daily_gold_price)

    # 👈 این پراپرتی احتمالاً در فایل شما جا افتاده است
    @property
    def wage_amount(self):
        if self.product_type == 'ornamental':
            return self.raw_gold_value * (self.wage_percent / 100)
        return 0.0

    @property
    def profit_value(self):
        if self.product_type == 'ornamental':
            return (self.raw_gold_value + self.wage_amount) * (self.profit_percent / 100)
        elif self.product_type == 'parsian':
            return self.raw_gold_value * (self.profit_percent / 100)
        return 0.0

    @property
    def tax_value(self):
        if self.product_type == 'ornamental':
            return (self.profit_value + self.wage_amount) * (self.tax_percent / 100)
        return 0.0

    @property
    def final_item_price(self):
        raw_val = self.raw_gold_value
        
        if self.product_type == 'ornamental':
            return int(raw_val + self.wage_amount + self.profit_value + self.tax_value)
            
        elif self.product_type == 'parsian':
            return int(raw_val + self.profit_value + float(self.constant_fee))
            
        return int(raw_val)

    def __str__(self):
        return f"{self.product.title} در سبد {self.cart.id}"


