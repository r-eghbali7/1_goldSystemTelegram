from django.contrib import admin
from .models import Cart, CartItem

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0  # جلوگیری از نمایش سطرهای خالی اضافه
    autocomplete_fields = ('product',)
    readonly_fields = ('raw_gold_value', 'wage_value', 'profit_value', 'tax_value', 'final_item_price')
    fields = ('product', 'daily_gold_price', 'wage_percent', 'profit_percent', 'tax_percent', 'final_item_price')

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'is_paid', 'total_cart_price', 'expires_at', 'is_expired_status', 'created_at')
    list_filter = ('is_paid', 'created_at')
    search_fields = ('user__phone_number', 'id')
    inlines = [CartItemInline]
    readonly_fields = ('id', 'created_at', 'updated_at', 'total_cart_price', 'is_expired_status')
    list_select_related = ('user',)

    @admin.display(boolean=True, description='منقضی شده')
    def is_expired_status(self, obj):
        return obj.is_expired