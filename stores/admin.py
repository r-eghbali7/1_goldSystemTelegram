from django.contrib import admin, messages
from django.db.models import Count
from .models import Store, StoreCustomer
from .services import setup_store_webhooks  # 👈 سرویس تنظیم وب‌هوک را ایمپورت کنید

@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ('get_store_name', 'owner', 'get_customers_count', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    
    # فیلدهای جستجو اصلاح شدند
    search_fields = ('telegram_bot_username', 'bale_bot_username', 'telegram_bot_token', 'bale_bot_token', 'owner__phone_number')    
    list_editable = ('is_active',)
    autocomplete_fields = ('owner',)
    readonly_fields = ('id', 'created_at')

    fieldsets = (
        ('اطلاعات پایه و مالکیت', {
            'fields': ('id', 'owner', 'is_active')
        }),
        ('تنظیمات پیام‌رسان‌ها (تلگرام و بله)', {
            # تغییر به نام‌های جدید
            'fields': (
                'telegram_bot_token', 'telegram_bot_username', 'channel_id_telegram', 'admin_chat_id_telegram',
                'bale_bot_token', 'bale_bot_username', 'channel_id_bale', 'admin_chat_id_bale'
            ),
        }),
        ('تنظیمات درگاه پرداخت', {
            'fields': ('zarinpal_merchant_id',)
        }),
        ('تاریخ‌ها', {
            'fields': ('created_at',)
        }),
    )

    actions = ['setup_telegram_webhook']

    @admin.display(description='نام ربات')
    def get_store_name(self, obj):
        return obj.telegram_bot_username or obj.bale_bot_username or "بدون نام"
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(customers_count=Count('customers'))

    @admin.display(description='تعداد مشتریان', ordering='customers_count')
    def get_customers_count(self, obj):
        return obj.customers_count

    @admin.action(description='تنظیم وب‌هوک (Webhook) تلگرام/بله برای ربات‌های انتخاب شده')
    def setup_telegram_webhook(self, request, queryset):
        success_count = 0
        for store in queryset:
            # بررسی وجود حداقل یک توکن
            if not store.telegram_bot_token and not store.bale_bot_token:
                self.message_user(request, f"فروشگاه {store.id} هیچ توکنی ندارد.", level=messages.WARNING)
                continue
                
            try:
                # فراخوانی صحیح سرویس با یک آرگومان (ارسال خودِ شیء store)
                results = setup_store_webhooks(store)                
                for res in results:
                    self.message_user(request, res, level=messages.SUCCESS)
                success_count += 1
            except Exception as e:
                self.message_user(
                    request, 
                    f"خطای ارتباط با سرور برای ربات {store.bot_username or store.id}: {str(e)}", 
                    level=messages.ERROR
                )

@admin.register(StoreCustomer)
class StoreCustomerAdmin(admin.ModelAdmin):
    list_display = ('user', 'store', 'get_formatted_total_spent', 'is_blocked', 'joined_at')
    list_filter = ('is_blocked', 'store', 'joined_at')
    
    search_fields = (
            'user__phone_number', 
            'user__first_name', 
            'user__last_name', 
            'store__telegram_bot_username', # تغییر یافت
            'store__bale_bot_username'      # اضافه شد
        )
    
    autocomplete_fields = ('store', 'user')
    list_editable = ('is_blocked',)
    readonly_fields = ('joined_at',)
    
    # بهینه‌سازی کوئری‌های جوین شده
    list_select_related = ('user', 'store')

    fieldsets = (
        ('ارتباط کاربر و فروشگاه', {
            'fields': ('store', 'user', 'is_blocked')
        }),
        ('آمار مالی', {
            'fields': ('total_spent',)
        }),
        ('تاریخ‌ها', {
            'fields': ('joined_at',)
        }),
    )

    @admin.display(description='مجموع خرید (تومان)', ordering='total_spent')
    def get_formatted_total_spent(self, obj):
        return f"{int(obj.total_spent):,}"