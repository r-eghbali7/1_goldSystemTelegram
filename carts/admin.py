from django.contrib import admin
from .models import Cart, CartItem

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    can_delete = True
    autocomplete_fields = ('product',)
    
    readonly_fields = (
        'get_raw_gold_value', 
        'get_profit_value', 
        'get_tax_value', 
        'get_final_item_price'
    )
    
    fields = (
        'product', 
        'daily_gold_price', 
        'wage', 
        'profit_percent', 
        'tax_percent',
        'constant_fee',
        'get_raw_gold_value',
        'get_profit_value',
        'get_tax_value',
        'get_final_item_price'
    )

    @admin.display(description='طلای خام (تومان)')
    def get_raw_gold_value(self, obj):
        return f"{int(obj.raw_gold_value):,}" if obj.pk else "-"

    @admin.display(description='سود')
    def get_profit_value(self, obj):
        return f"{int(obj.profit_value):,}" if obj.pk else "-"

    @admin.display(description='مالیات')
    def get_tax_value(self, obj):
        return f"{int(obj.tax_value):,}" if obj.pk else "-"

    @admin.display(description='قیمت نهایی')
    def get_final_item_price(self, obj):
        return f"{int(obj.final_item_price):,}" if obj.pk else "-"


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    # از آنجا که Cart از TenantModel ارث‌بری کرده، فیلد store نیز در دسترس است
    list_display = (
        'id', 
        'user', 
        'store', 
        'is_paid', 
        'get_total_price', 
        'is_expired_status', 
        'created_at'
    )
    
    list_filter = ('is_paid', 'created_at', 'store')
    search_fields = ('user__phone_number', 'store__telegram_bot_username', 'store__bale_bot_username')    
    inlines = [CartItemInline]
    
    readonly_fields = (
        'id', 
        'created_at', 
        'updated_at', 
        'get_total_price', 
        'is_expired_status'
    )
    
    # بهینه‌سازی کوئری‌های دیتابیس (جلوگیری از مشکل N+1 در پنل ادمین)
    list_select_related = ('user', 'store')

    # گروه‌بندی فیلدها در صفحه جزئیات سبد خرید
    fieldsets = (
        ('اطلاعات پایه', {
            'fields': ('id', 'user', 'store', 'is_paid')
        }),
        ('وضعیت و مبالغ', {
            'fields': ('get_total_price', 'expires_at', 'is_expired_status')
        }),
        ('تاریخ‌ها', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    @admin.display(boolean=True, description='وضعیت انقضا')
    def is_expired_status(self, obj):
        return obj.is_expired

    @admin.display(description='مبلغ کل سبد (تومان)')
    def get_total_price(self, obj):
        return f"{obj.total_cart_price:,}"