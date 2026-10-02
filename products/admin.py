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
    list_display = ('title', 'category', 'product_type_fa', 'weight', 'is_active') # price حذف شد
    
    # اضافه کردن فیلتر نوع محصول به سایدبار ادمین
    list_filter = ('product_type', 'is_active', 'category') + TenantModelAdmin.list_filter
    search_fields = ('title', 'description')

    # گروه‌بندی منظم فیلدها در صفحه افزودن/ویرایش محصول
    fieldsets = (
        ('اطلاعات پایه', {
            'fields': ('title', 'category', 'description', 'image', 'weight', 'is_active') # price حذف شد
        }),
        ('تنظیمات محاسبه قیمت زنده', {
            'fields': ('product_type', 'profit_percent'),
        }),
        ('فرمول طلای زینتی', {
            'classes': ('ornamental-group',),
            'fields': ('wage_percent', 'tax_percent'), # wage به wage_percent تغییر کرد
        }),
        ('فرمول سکه پارسیان', {
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


    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # اگر کاربر سوپریوزر نبود، فقط محصولات فروشگاه خودش را نشان بده
        if not request.user.is_superuser:
            user_store = request.user.stores.first() # ارتباط مالک با فروشگاه
            if user_store:
                return qs.filter(store=user_store)
            return qs.none()
        return qs
