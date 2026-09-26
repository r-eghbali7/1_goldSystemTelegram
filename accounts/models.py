import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator

# اعتبارسنجی دقیق فرمت موبایل ایران
phone_regex = RegexValidator(
    regex=r'^09\d{9}$', 
    message="شماره موبایل باید با 09 شروع شده و 11 رقم باشد."
)

class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = None
    phone_number = models.CharField(validators=[phone_regex], max_length=11, unique=True, verbose_name="شماره موبایل")
    chat_id = models.CharField(max_length=100, unique=True, null=True, blank=True, verbose_name="آیدی تلگرام")
    is_verified = models.BooleanField(default=False, verbose_name="احراز هویت شده")

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.phone_number
