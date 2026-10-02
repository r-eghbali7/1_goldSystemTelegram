import openpyxl
from django.http import HttpResponse
from django.utils import timezone
from django.contrib import admin
from django.db import models
from core.admin import TenantModelAdmin
from core.utils import to_jalali_format, to_persian_digits
from core.widgets import PersianAdminDateWidget
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False  
    readonly_fields = ('product', 'get_purchased_price', 'gold_weight')
    fields = ('product', 'get_purchased_price', 'gold_weight')

    @admin.display(description='قیمت نهایی پرداخت شده (تومان)')
    def get_purchased_price(self, obj):
        return f"{int(obj.purchased_price):,}" if obj.pk else "-"
        
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(TenantModelAdmin):
    list_display = (
        'id', 
        'user', 
        'store', 
        'status', 
        'get_persian_total_amount', 
        'get_persian_created_at',   
        'ref_id'
    )
    
    list_filter = TenantModelAdmin.list_filter + ('status', 'created_at')
    search_fields = ('user__phone_number', 'store__telegram_bot_username', 'store__bale_bot_username')    
    inlines = [OrderItemInline]
    actions = ['export_orders_as_excel']
    
    readonly_fields = (
        'id', 
        'user', 
        'store', 
        'total_amount', 
        'get_formatted_total_amount', 
        'authority', 
        'ref_id', 
        'created_at', 
        'updated_at'
    )
    
    list_select_related = ('user', 'store')
    
    fieldsets = (
        ('اطلاعات پایه', {
            'fields': ('id', 'user', 'store', 'status')
        }),
        ('اطلاعات مالی', {
            'fields': ('total_amount', 'get_formatted_total_amount')
        }),
        ('اطلاعات درگاه پرداخت زرین‌پال', {
            'fields': ('authority', 'ref_id')
        }),
        ('تاریخ‌ها', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    @admin.action(description='📥 دانلود خروجی اکسل واقعی (.xlsx) با تنظیم خودکار پهنای ستون‌ها')
    def export_orders_as_excel(self, request, queryset):
        current_time = timezone.now().strftime('%Y-%m-%d_%H-%M')
        filename = f"orders_report_{current_time}.xlsx"

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "گزارش فاکتورها"
        ws.sheet_view.rightToLeft = True

        headers = [
            'شناسه سفارش (UUID)', 
            'مشتری (شماره موبایل)', 
            'فروشگاه', 
            'مبلغ کل (تومان)', 
            'وضعیت تراکنش', 
            'کد پیگیری (RefID)', 
            'تاریخ ثبت'
        ]
        ws.append(headers)

        for col_num in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_num)
            cell.font = openpyxl.styles.Font(bold=True)

        for order in queryset:
            status_mapping = {
                'pending': 'در انتظار پرداخت',
                'paid': 'پرداخت شده موفق',
                'failed': 'پرداخت ناموفق'
            }
            persian_status = status_mapping.get(order.status, order.status)
            
            ws.append([
                str(order.id),
                order.user.phone_number if order.user else 'مهمان',
                order.store.telegram_bot_username or order.store.bale_bot_username if order.store else 'ناشناس',
                int(order.total_amount),
                persian_status,
                order.ref_id or 'ندارد',
                order.created_at.strftime('%Y-%m-%d %H:%M')
            ])

        for col in ws.columns:
            max_length = 0
            col_letter = openpyxl.utils.get_column_letter(col[0].column)
            for cell in col:
                try:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                except:
                    pass
            adjusted_width = max(max_length + 4, 12)
            ws.column_dimensions[col_letter].width = adjusted_width

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        wb.save(response)
        return response

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if isinstance(db_field, (models.DateField, models.DateTimeField)):
            kwargs['widget'] = PersianAdminDateWidget()
        return super().formfield_for_dbfield(db_field, request, **kwargs)
    
    @admin.display(description='مبلغ کل فاکتور')
    def get_persian_total_amount(self, obj):
        return f"{to_persian_digits(obj.total_amount)} تومان"

    @admin.display(description='تاریخ ثبت سفارش')
    def get_persian_created_at(self, obj):
        return to_jalali_format(obj.created_at)
    
    @admin.display(description='مبلغ کل فاکتور (تومان)')
    def get_formatted_total_amount(self, obj):
        return f"{int(obj.total_amount):,}" if obj.total_amount else "0"
        
    def has_add_permission(self, request):
        return False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # اگر کاربر سوپریوزر نبود، فقط محصولات فروشگاه خودش را نشان بده
        if not request.user.is_superuser:
            user_store = request.user.stores.first() # ارتباط مالک با فروشگاه
            if user_store:
                return qs.filter(store=user_store)
            return qs.none()
        return qs