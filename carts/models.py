import uuid
from datetime import timedelta
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from products.models import Product

User = get_user_model()

def get_default_cart_expiration():
    # سبد خرید به صورت پیش‌فرض ۳۰ دقیقه اعتبار دارد
    return timezone.now() + timedelta(minutes=30)

class Cart(models.fields.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='carts', verbose_name="کاربر")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین بروزرسانی")
    expires_at = models.DateTimeField(default=get_default_cart_expiration, verbose_name="زمان انقضا")
    is_paid = models.BooleanField(default=False, verbose_name="پرداخت شده")

    @property
    def is_expired(self):
        """بررسی اینکه آیا زمان سبد خرید به پایان رسیده است یا خیر"""
        return timezone.now() > self.expires_at and not self.is_paid

    @property
    def total_cart_price(self):
        """محاسبه قیمت کل تمام آیتم‌های سبد خرید"""
        if self.is_expired:
            return 0
        return sum(item.final_item_price for item in self.items.all())

    def refresh_expiration(self):
        """تمدید زمان سبد خرید در صورت فعالیت جدید کاربر"""
        self.expires_at = get_default_cart_expiration()
        self.save()

    def __str__(self):
        return f"سبد {self.id} - کاربر {self.user.phone_number}"

class CartItem(models.fields.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items', verbose_name="سبد خرید")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="محصول")
    
    # مقادیری که در زمان افزودن به سبد، ثبت (Snapshot) می‌شوند تا با تغییرات آینده بازار خراب نشوند
    daily_gold_price = models.DecimalField(
        max_digits=12, decimal_places=0, validators=[MinValueValidator(0)], 
        verbose_name="قیمت روز طلا (هر گرم) زمان ثبت"
    )
    wage_percent = models.FloatField(default=0.0, validators=[MinValueValidator(0.0)], verbose_name="درصد اجرت ساخت")
    profit_percent = models.FloatField(default=7.0, validators=[MinValueValidator(0.0)], verbose_name="درصد سود طلافروش")
    tax_percent = models.FloatField(default=9.0, validators=[MinValueValidator(0.0)], verbose_name="درصد مالیات")

    @property
    def raw_gold_value(self):
        """ارزش طلای خام: وزن محصول × قیمت روز طلا"""
        return float(self.product.weight) * float(self.daily_gold_price)

    @property
    def wage_value(self):
        """مبلغ اجرت ساخت"""
        return self.raw_gold_value * (self.wage_percent / 100)

    @property
    def profit_value(self):
        """مبلغ سود فروشنده (معمولاً از جمع طلای خام و اجرت محاسبه می‌شود)"""
        return (self.raw_gold_value + self.wage_value) * (self.profit_percent / 100)

    @property
    def tax_value(self):
        """مبلغ مالیات (طبق قانون ایران، مالیات ۹ درصد فقط به اجرت و سود تعلق می‌گیرد، نه کل طلای خام)"""
        return (self.wage_value + self.profit_value) * (self.tax_percent / 100)

    @property
    def final_item_price(self):
        """قیمت نهایی این آیتم برای پرداخت"""
        total = self.raw_gold_value + self.wage_value + self.profit_value + self.tax_value
        return round(total)

    def __str__(self):
        return f"{self.product.title} در سبد {self.cart.id}"