import uuid
from django.db import models
from django.core.validators import MinValueValidator

class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, verbose_name="نام دسته‌بندی")
    
    def __str__(self):
        return self.name

class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    title = models.CharField(max_length=200, verbose_name="عنوان محصول")
    description = models.TextField(verbose_name="توضیحات")
    
    # استفاده از MinValueValidator برای جلوگیری از ثبت قیمت و وزن منفی
    price = models.DecimalField(
        max_digits=12, decimal_places=0, validators=[MinValueValidator(0)], verbose_name="قیمت (تومان)"
    )
    weight = models.FloatField(validators=[MinValueValidator(0.0)], help_text="وزن به گرم", verbose_name="وزن")
    
    image = models.ImageField(upload_to='products/', verbose_name="تصویر محصول")
    is_active = models.BooleanField(default=True, verbose_name="موجود در فروشگاه")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title