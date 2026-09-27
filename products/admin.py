from django.contrib import admin
from .models import Category, Product

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'id')
    search_fields = ('name',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'price', 'weight', 'is_active', 'created_at')
    list_filter = ('is_active', 'category', 'created_at')
    search_fields = ('title', 'description')
    list_editable = ('price', 'weight', 'is_active')
    autocomplete_fields = ('category',)
    readonly_fields = ('id', 'created_at')
    ordering = ('-created_at',)
    
    # برای بهینه‌سازی کوئری‌های دیتابیس
    list_select_related = ('category',)