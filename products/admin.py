from django.contrib import admin
from django.utils.html import format_html
from core.admin import TenantModelAdmin
from .models import Category, Product

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'id')
    search_fields = ('name',)
    # اگر تعداد دسته‌بندی‌ها زیاد است، این مورد برای پرفورمنس عالی است
    ordering = ('name',)


@admin.register(Product)
class ProductAdmin(TenantModelAdmin):
    # استفاده از متدهای کاستوم برای نمایش زیبای قیمت و عکس
    list_display = (
        'title', 
        'store', 
        'category', 
        'get_formatted_price', 
        'weight', 
        'is_active', 
        'image_preview_list', 
        'created_at'
    )
    
    # فیلترها (اضافه شدن فیلتر فروشگاه از TenantModelAdmin)
    list_filter = TenantModelAdmin.list_filter + ('is_active', 'category', 'created_at')
    
    # جستجو در نام محصول، توضیحات، نام دسته‌بندی و آیدی ربات فروشگاه
    search_fields = ('title', 'description', 'category__name', 'store__bot_username')
    
    # قابلیت سرچ در دراپ‌داون‌ها (برای فرم‌های شلوغ)
    autocomplete_fields = ('category',)
    
    # تغییر سریع وضعیت موجودی مستقیماً از لیست محصولات بدون ورود به صفحه ویرایش
    list_editable = ('is_active',)
    
    readonly_fields = ('id', 'created_at', 'image_preview_detail')
    
    # بهینه‌سازی کوئری‌های دیتابیس
    list_select_related = ('category', 'store')

    # دسته‌بندی فیلدها در صفحه ایجاد/ویرایش محصول
    fieldsets = (
        ('اطلاعات پایه', {
            'fields': ('id', 'store', 'category', 'title', 'is_active')
        }),
        ('مشخصات و قیمت', {
            'fields': ('price', 'weight', 'description')
        }),
        ('تصویر محصول', {
            'fields': ('image', 'image_preview_detail')
        }),
        ('تاریخ‌ها', {
            'fields': ('created_at',)
        }),
    )

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