from django.contrib import admin
from django.utils.html import format_html
from core.admin import TenantModelAdmin
from .models import Category, Product

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


@admin.register(Product)
class ProductAdmin(TenantModelAdmin):
    # نمایش ستون‌های کاربردی در لیست محصولات
    list_display = (
        'title', 
        'category', 
        'product_type_fa', 
        'weight', 
        'is_active'
    )
    
    # اضافه کردن فیلتر نوع محصول به سایدبار ادمین
    list_filter = ('product_type', 'is_active', 'category') + TenantModelAdmin.list_filter
    search_fields = ('title', 'description')

    # گروه‌بندی منظم فیلدها در صفحه افزودن/ویرایش محصول
    fieldsets = (
        ('اطلاعات پایه', {
            'fields': (
                'title', 
                'category', 
                'description', 
                'image', 
                'weight', 
                'price', 
                'is_active'
            )
        }),
        ('تنظیمات محاسبه قیمت زنده', {
            'fields': ('product_type', 'profit_percent'),
            'description': 'نوع کالا را انتخاب کنید تا فیلدهای مربوط به فرمول آن نمایش داده شوند.'
        }),
        ('فرمول طلای زینتی', {
            # کلاس ornamental-group برای کنترل توسط جاوااسکریپت
            'classes': ('ornamental-group',),
            'fields': ('wage', 'tax_percent'),
        }),
        ('فرمول سکه پارسیان', {
            # کلاس parsian-group برای کنترل توسط جاوااسکریپت
            'classes': ('parsian-group',),
            'fields': ('constant_fee',),
        }),
    )

    # اتصال فایل جاوااسکریپت به این صفحه از پنل ادمین
    class Media:
        js = ('admin/js/product_formula_toggle.js',)

    @admin.display(description='نوع محصول')
    def product_type_fa(self, obj):
        return obj.get_product_type_display()

    @admin.display(description='قیمت (تومان)', ordering='price')
    def get_formatted_price(self, obj):
        """نمایش قیمت با جداکننده هزارگان"""
        return f"{int(obj.price):,}" if obj.price else "0"

    @admin.display(description='تصویر')
    def image_preview_list(self, obj):
        """نمایش عکس بندانگشتی (Thumbnail) در لیست محصولات"""
        if obj.image:
            return format_html(
                '<img src="{}" width="40" height="40" style="border-radius: 4px; object-fit: cover;" />', 
                obj.image.url
            )
        return "-"

    @admin.display(description='پیش‌نمایش تصویر فعلی')
    def image_preview_detail(self, obj):
        """نمایش عکس در سایز بزرگتر در صفحه ویرایش محصول"""
        if obj.image:
            return format_html(
                '<img src="{}" width="200" style="border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />', 
                obj.image.url
            )
        return "بدون تصویر"
