from django.contrib import admin, messages
from django.db.models import Count
from .models import Store, StoreCustomer
from .services import set_telegram_webhook  # 👈 سرویس تنظیم وب‌هوک را ایمپورت کنید

@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = (
        'bot_username', 
        'owner', 
        'get_customers_count', 
        'is_active', 
        'created_at'
    )
    list_filter = ('is_active', 'created_at')
    search_fields = ('bot_username', 'bot_token', 'owner__phone_number', 'zarinpal_merchant_id')
    list_editable = ('is_active',)
    autocomplete_fields = ('owner',)
    readonly_fields = ('id', 'created_at')
    list_select_related = ('owner',)

    fieldsets = (
        ('اطلاعات پایه و مالکیت', {
            'fields': ('id', 'owner', 'is_active')
        }),
        ('تنظیمات ربات تلگرام', {
            'fields': ('bot_token', 'bot_username', 'channel_id', 'admin_chat_id'),
            'description': 'توجه: پس از تغییر توکن ربات، از منوی اکشن‌ها "تنظیم وب‌هوک" را اجرا کنید.'
        }),
        ('تنظیمات درگاه پرداخت', {
            'fields': ('zarinpal_merchant_id',)
        }),
        ('تاریخ‌ها', {
            'fields': ('created_at',)
        }),
    )

    # 👈 معرفی اکشن به کلاس ادمین
    actions = ['setup_telegram_webhook']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(customers_count=Count('customers'))

    @admin.display(description='تعداد مشتریان', ordering='customers_count')
    def get_customers_count(self, obj):
        return obj.customers_count

    # 👈 پیاده‌سازی منطق اکشن سفارشی
    @admin.action(description='تنظیم وب‌هوک (Webhook) تلگرام برای ربات‌های انتخاب شده')
    def setup_telegram_webhook(self, request, queryset):
        success_count = 0
        
        for store in queryset:
            if not store.bot_token:
                self.message_user(request, f"فروشگاه {store.id} توکن تلگرام ندارد.", level=messages.WARNING)
                continue
                
            try:
                response = set_telegram_webhook(store.bot_token)
                
                # بررسی پاسخ سرور تلگرام
                if response.get('ok'):
                    success_count += 1
                else:
                    error_msg = response.get('description', 'خطای نامشخص')
                    self.message_user(
                        request, 
                        f"خطا در تنظیم وب‌هوک برای ربات {store.bot_username or store.id}: {error_msg}", 
                        level=messages.ERROR
                    )
            except Exception as e:
                self.message_user(
                    request, 
                    f"خطای ارتباط با سرور تلگرام برای ربات {store.bot_username or store.id}: {str(e)}", 
                    level=messages.ERROR
                )
        
        if success_count > 0:
            self.message_user(
                request, 
                f"وب‌هوک {success_count} ربات با موفقیت روی سرور تنظیم شد.", 
                level=messages.SUCCESS
            )


@admin.register(StoreCustomer)
class StoreCustomerAdmin(admin.ModelAdmin):
    list_display = (
        'user', 
        'store', 
        'get_formatted_total_spent', 
        'is_blocked', 
        'joined_at'
    )
    
    list_filter = ('is_blocked', 'store', 'joined_at')
    
    search_fields = (
        'user__phone_number', 
        'user__first_name', 
        'user__last_name', 
        'store__bot_username'
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