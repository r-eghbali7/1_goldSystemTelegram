import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator

# اعتبارسنجی دقیق فرمت موبایل ایران
phone_regex = RegexValidator(
    regex=r'^09\d{9}$', 
    message="شماره موبایل باید با 09 شروع شده و 11 رقم باشد."
)

class CustomUserManager(BaseUserManager):
    """
    مدیر اختصاصی برای ایجاد کاربر و سوپریوزر بر اساس شماره موبایل
    """
    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError('شماره موبایل باید وارد شود')
        
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('سوپریوزر باید is_staff=True باشد.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('سوپریوزر باید is_superuser=True باشد.')

        return self.create_user(phone_number, password, **extra_fields)

class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = None
    phone_number = models.CharField(validators=[phone_regex], max_length=11, unique=True, verbose_name="شماره موبایل")
    chat_id = models.CharField(max_length=100, unique=True, null=True, blank=True, verbose_name="آیدی تلگرام")
    telegram_chat_id = models.CharField(max_length=100, unique=True, null=True, blank=True, verbose_name="آیدی تلگرام")
    bale_chat_id = models.CharField(max_length=100, unique=True, null=True, blank=True, verbose_name="آیدی بله")
    is_verified = models.BooleanField(default=False, verbose_name="احراز هویت شده")

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = []

    # مشخص کردن مدیر اختصاصی
    objects = CustomUserManager()

    def __str__(self):
        return self.phone_number