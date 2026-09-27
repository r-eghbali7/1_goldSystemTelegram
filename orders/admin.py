from django.contrib import admin
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False  # جلوگیری از حذف آیتم‌های فاکتور
    autocomplete_fields = ('product',)
    readonly_fields = ('purchased_price', 'gold_weight')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'total_amount', 'ref_id', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__phone_number', 'ref_id', 'authority', 'id')
    list_editable = ('status',)
    inlines = [OrderItemInline]
    readonly_fields = ('id', 'created_at', 'updated_at', 'total_amount', 'authority', 'ref_id')
    list_select_related = ('user',)
    
    fieldsets = (
        ('اطلاعات پایه', {'fields': ('id', 'user', 'status', 'total_amount')}),
        ('اطلاعات درگاه پرداخت', {'fields': ('authority', 'ref_id')}),
        ('تاریخ‌ها', {'fields': ('created_at', 'updated_at')}),
    )