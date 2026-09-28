from django.contrib import admin

class TenantModelAdmin(admin.ModelAdmin):
    list_select_related = ('store',)

    def get_list_filter(self, request):
        # اگر کاربر سوپریوزر است، فیلتر فروشگاه را نشان بده، برای فروشنده نیازی نیست
        if request.user.is_superuser:
            return ('store',) + getattr(self, 'list_filter', ())
        return getattr(self, 'list_filter', ())

    def get_queryset(self, request):
        """
        فیلتر کردن هوشمند دیتا بر اساس سطح دسترسی کاربر
        """
        qs = self.model.all_objects.get_queryset()
        
        # ۱. اگر ادمین کل سیستم (Superuser) است، تمام دیتای کل پلتفرم را ببیند
        if request.user.is_superuser:
            ordering = self.get_ordering(request)
            if ordering:
                qs = qs.order_by(*ordering)
            return qs
            
        # ۲. اگر فروشنده معمولی است، فقط دیتای فروشگاه‌های متعلق به خودش را ببیند
        user_stores = request.user.stores.all()
        qs = qs.filter(store__in=user_stores)
        
        ordering = self.get_ordering(request)
        if ordering:
            qs = qs.order_by(*ordering)
        return qs

    def save_model(self, request, obj, form, change):
        """
        تخصیص خودکار فروشگاه در زمان ایجاد رکورد جدید توسط فروشنده
        """
        if not change and not getattr(obj, 'store_id', None):
            # اگر فروشنده خودش فروشگاه دارد، به صورت پیش‌فرض روی آن ست شود
            user_store = request.user.stores.first()
            if user_store:
                obj.store = user_store
                
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        محدود کردن لیست کشویی (Dropdown) انتخاب فروشگاه در فرم‌ها
        """
        if db_field.name == 'store' and not request.user.is_superuser:
            # فروشنده نباید بتواند محصول را برای فروشگاه دیگران ثبت کند
            kwargs['queryset'] = request.user.stores.all()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)