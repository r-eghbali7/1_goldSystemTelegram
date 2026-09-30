from django.contrib import admin

class TenantModelAdmin(admin.ModelAdmin):
    """
    کلاس پایه و حرفه‌ای برای تمام مدل‌های وابسته به فروشگاه در ادمین مرکزی
    این کلاس مستقیماً رجیستر نمی‌شود.
    """
    # جلوگیری از خطای وحشتناک N+1 با جوین کردن خودکار جدول فروشگاه
    list_select_related = ('store',)
    
    # اضافه کردن پیش‌فرض فیلتر فروشگاه به سایدبار برای ادمین مرکزی
    list_filter = ('store',)

    def get_queryset(self, request):
        """
        بازنویسی کوئری‌ست برای استفاده از all_objects.
        دلیل: TenantManager ممکن است به خاطر مقداردهی ناخواسته context، 
        دیتای ادمین مرکزی را فیلتر کند. all_objects تضمین می‌کند که ادمین کل سیستم، 
        به دیتای تمامی مستاجرین (Tenants) دسترسی دارد.
        """
        qs = self.model.all_objects.get_queryset()
        
        # اعمال مرتب‌سازی‌های پیش‌فرض ادمین روی کوئری‌ست
        ordering = self.get_ordering(request)
        if ordering:
            qs = qs.order_by(*ordering)
        return qs

    def save_model(self, request, obj, form, change):
        """
        محافظت در زمان ذخیره‌سازی: 
        اگر قرار است ادمین‌ها/فروشندگان از طریق این پنل دیتا ثبت کنند و فراموش کردند
        فروشگاه را انتخاب کنند، سیستم به صورت هوشمند فروشگاه متصل به آن‌ها را اختصاص دهد.
        """
        # اگر رکورد جدید است و فیلد فروشگاه مقداردهی نشده:
        if not change and not getattr(obj, 'store_id', None):
            # بررسی اینکه آیا این کاربر خودش صاحب فروشگاهی هست یا خیر
            user_store = request.user.stores.first()
            if user_store:
                obj.store = user_store
                
        super().save_model(request, obj, form, change)