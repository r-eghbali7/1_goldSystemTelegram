# stores/models.py
import uuid
from django.db import models
from accounts.models import User


PLATFORM_CHOICES = (
    ('telegram', 'تلگرام'),
    ('bale', 'بله'),
)

class Store(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='stores', verbose_name="صاحب فروشگاه")
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, default='telegram', verbose_name="پلتفرم")
    telegram_bot_token = models.CharField(max_length=100, unique=True, null=True, blank=True, verbose_name="توکن تلگرام")
    bale_bot_token = models.CharField(max_length=100, unique=True, null=True, blank=True, verbose_name="توکن بله")
    bot_username = models.CharField(max_length=100, null=True, blank=True, verbose_name="یوزرنیم ربات")
    channel_id = models.CharField(max_length=100, null=True, blank=True, verbose_name="آیدی کانال")
    admin_chat_id = models.CharField(max_length=100, null=True, blank=True, verbose_name="چت آیدی ادمین برای پشتیبانی")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    zarinpal_merchant_id = models.CharField(max_length=36, blank=True, null=True, verbose_name="مرچنت آیدی زرین‌پال")
    
    def __str__(self):
        return self.bot_username or str(self.id)



class StoreCustomer(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='customers', verbose_name="فروشگاه")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='store_profiles', verbose_name="مشتری")
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ عضویت در ربات")
    
    # فیلدهای اختصاصی کاربر در این فروشگاه خاص (اختیاری)
    total_spent = models.DecimalField(max_digits=15, decimal_places=0, default=0, verbose_name="مجموع خرید از این فروشگاه")
    is_blocked = models.BooleanField(default=False, verbose_name="بلاک شده توسط این فروشگاه")

    class Meta:
        # جلوگیری از ثبت تکراری یک کاربر در یک فروشگاه
        unique_together = ('store', 'user') 

    def __str__(self):
        return f"{self.user.phone_number} در {self.store.bot_username}"