from django.contrib import admin
from .models import User

@admin.register(User)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'first_name', 'last_name', 'is_verified', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('is_verified', 'is_staff', 'is_active', 'date_joined')
    search_fields = ('phone_number', 'chat_id', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    readonly_fields = ('id', 'last_login', 'date_joined')
    
    fieldsets = (
        ('اطلاعات ورود', {'fields': ('phone_number', 'password')}),
        ('اطلاعات شخصی', {'fields': ('first_name', 'last_name', 'chat_id')}),
        ('دسترسی‌ها و وضعیت', {'fields': ('is_verified', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('تاریخ‌ها', {'fields': ('last_login', 'date_joined')}),
    )