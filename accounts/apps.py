from django.apps import AppConfig

class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'
    verbose_name = 'مدیریت کاربران و احراز هویت' # نام نمایشی در پنل ادمین جنگو

    def ready(self):
        # ایمپورت کردن فایل سیگنال‌ها پس از لود شدن کامل اپلیکیشن
        import accounts.signals