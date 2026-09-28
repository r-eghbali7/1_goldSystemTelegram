from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.utils.translation import gettext_lazy as _
from .models import User


# ۱. فرم اختصاصی برای ویرایش کاربر (مدیریت هشینگ رمز عبور)
class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = ('phone_number', 'email', 'first_name', 'last_name', 'chat_id')

# ۲. فرم اختصاصی برای ساخت کاربر جدید در پنل ادمین
class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('phone_number',)


# ۳. ثبت مدل در ادمین با تنظیمات پیشرفته
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm

    # فیلدهای نمایشی در لیست کل کاربران
    list_display = (
        'phone_number', 
        'first_name', 
        'last_name', 
        'is_verified', 
        'is_staff', 
        'is_active', 
        'date_joined'
    )
    
    # فیلترهای سایدبار سمت راست
    list_filter = (
        'is_verified', 
        'is_staff', 
        'is_superuser', 
        'is_active', 
        'date_joined'
    )
    
    # فیلدهای قابل جستجو (بسیار مهم برای پیدا کردن سریع مشتریان)
    search_fields = ('phone_number', 'chat_id', 'first_name', 'last_name')
    
    # مرتب‌سازی پیش‌فرض (جدیدترین کاربران در ابتدا)
    ordering = ('-date_joined',)
    
    # فیلدهایی که فقط خواندنی هستند و ادمین نباید آن‌ها را تغییر دهد
    readonly_fields = ('id', 'last_login', 'date_joined')

    # گروه‌بندی حرفه‌ای فیلدها در صفحه ویرایش جزئیات کاربر
    fieldsets = (
        (_('اطلاعات ورود'), {'fields': ('phone_number', 'password')}),
        (_('اطلاعات شخصی'), {'fields': ('first_name', 'last_name', 'email', 'chat_id')}),
        (_('دسترسی‌ها و وضعیت'), {
            'fields': (
                'is_verified', 
                'is_active', 
                'is_staff', 
                'is_superuser', 
                'groups', 
                'user_permissions'
            )
        }),
        (_('تاریخ‌ها'), {'fields': ('last_login', 'date_joined')}),
    )

    # فیلدهای نمایشی در صفحه "افزودن کاربر جدید"
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'password', 'password_2', 'is_verified', 'is_staff', 'is_active'),
        }),
    )
    
    # برای جلوگیری از خطای نبود username در UserAdmin اصلی
    filter_horizontal = ('groups', 'user_permissions',)