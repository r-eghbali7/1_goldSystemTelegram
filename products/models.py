import uuid
from django.db import models
from django.core.validators import MinValueValidator
from django.core.validators import MinValueValidator, MaxValueValidator

from core.models import TenantModel


PRODUCT_TYPES = (
    ('ornamental', 'طلای زینتی'),
    ('parsian', 'سکه پارسیان'),
)

class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, verbose_name="نام دسته‌بندی")
    
    def __str__(self):
        return self.name

class Product(TenantModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPES, default='ornamental', verbose_name="نوع محاسبه")
    title = models.CharField(max_length=200, verbose_name="عنوان محصول")
    description = models.TextField(verbose_name="توضیحات")
    
    weight = models.FloatField(validators=[MinValueValidator(0.0)], help_text="وزن به گرم", verbose_name="وزن")
    wage_percent = models.FloatField(default=0.0, validators=[MinValueValidator(0.0)], verbose_name="درصد اجرت")
    profit_percent = models.FloatField(
        default=7.0, 
        validators=[MinValueValidator(0.0), MaxValueValidator(7.0)], 
        help_text="حداکثر ۷ درصد",
        verbose_name="درصد سود"
    )
    tax_percent = models.FloatField(
        default=10.0, 
        validators=[MinValueValidator(0.0), MaxValueValidator(10.0)], 
        help_text="حداکثر ۱۰ درصد",
        verbose_name="درصد مالیات"
    )
    constant_fee = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name="مقدار ثابت (سکه پارسیان)")
    
    image = models.ImageField(upload_to='products/', verbose_name="تصویر محصول")
    is_active = models.BooleanField(default=True, verbose_name="موجود در فروشگاه")
    created_at = models.DateTimeField(auto_now_add=True)

    def calculate_live_price(self, live_18k_price):
        """محاسبه قیمت نهایی بر اساس فرمول‌های استاندارد بازار"""
        raw_gold_value = float(self.weight) * float(live_18k_price)
        
        if self.product_type == 'ornamental':
            # ۱. اجرت ساخت
            wage_amount = raw_gold_value * (self.wage_percent / 100)
            
            # ۲. سود فروش (محاسبه روی اصل طلا + اجرت)
            profit_amount = (raw_gold_value + wage_amount) * (self.profit_percent / 100)
            
            # ۳. مالیات (محاسبه روی سود + اجرت)
            tax_amount = (profit_amount + wage_amount) * (self.tax_percent / 100)
            
            # ۴. قیمت نهایی
            final_price = raw_gold_value + wage_amount + profit_amount + tax_amount
            return int(final_price)
            
        elif self.product_type == 'parsian':
            profit_amount = raw_gold_value * (self.profit_percent / 100)
            final_price = raw_gold_value + profit_amount + float(self.constant_fee)
            return int(final_price)
            
        return int(raw_gold_value)
    
    def __str__(self):
        return self.title


# products/models.py

class DailyGoldPrice(models.Model):
    date = models.DateField(unique=True, verbose_name="تاریخ")
    
    # قیمت طلا
    price = models.DecimalField(max_digits=12, decimal_places=0, verbose_name="قیمت پایانی طلا ۱۸ عیار")
    
    # قیمت‌های سکه (با مقدار پیش‌فرض صفر برای جلوگیری از خطای دیتابیس‌های قبلی)
    coin_old_price = models.DecimalField(max_digits=15, decimal_places=0, default=0, verbose_name="سکه طرح قدیم")
    coin_new_price = models.DecimalField(max_digits=15, decimal_places=0, default=0, verbose_name="سکه امامی")
    coin_half_price = models.DecimalField(max_digits=15, decimal_places=0, default=0, verbose_name="نیم سکه")
    coin_quarter_price = models.DecimalField(max_digits=15, decimal_places=0, default=0, verbose_name="ربع سکه")
    coin_gram_price = models.DecimalField(max_digits=15, decimal_places=0, default=0, verbose_name="سکه گرمی")
    
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.date}: طلا {self.price:,} | امامی {self.coin_new_price:,}"