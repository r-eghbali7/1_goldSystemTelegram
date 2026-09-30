from django.db import models
from .tenant import get_current_store

class TenantManager(models.Manager):
    """
    منیجر اختصاصی برای فیلتر خودکار دیتا بر اساس فروشگاه فعلی (Tenant)
    """
    def get_queryset(self):
        qs = super().get_queryset()
        current_store_id = get_current_store()
        if current_store_id:
            return qs.filter(store_id=current_store_id)
        return qs

class TenantModel(models.Model):
    """
    مدل پایه (Abstract) که سایر مدل‌های وابسته به فروشگاه از آن ارث‌بری می‌کنند.
    """
    store = models.ForeignKey(
        'stores.Store', 
        on_delete=models.CASCADE, 
        verbose_name="فروشگاه"
    )

    # منیجر پیش‌فرض که دیتا را فیلتر می‌کند
    objects = TenantManager()
    # منیجری برای دسترسی ادمین کل به دیتای تمامی فروشگاه‌ها
    all_objects = models.Manager()

    class Meta:
        abstract = True