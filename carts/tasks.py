from celery import shared_task
from django.utils import timezone
from django.db import transaction
from .models import Cart

@shared_task
def cleanup_expired_carts():
    now = timezone.now()
    
    # پیدا کردن تمامی سبدهای خریدی که پرداخت نشده‌اند و زمانشان گذشته است
    expired_carts = Cart.objects.filter(is_paid=False, expires_at__lt=now)
    carts_count = expired_carts.count()

    if carts_count == 0:
        return "هیچ سبد منقضی شده‌ای یافت نشد."

    # استفاده از تراکنش اتمیک برای جلوگیری از مشکلات همزمانی
    with transaction.atomic():
        for cart in expired_carts:
            for item in cart.items.all():
                product = item.product
                
                # اگر فیلد موجودی (stock) به مدل Product اضافه کرده‌اید:
                # product.stock += 1
                
                # اگر فقط از فیلد is_active استفاده می‌کنید و محصول قبلاً ناموجود شده بود:
                # product.is_active = True
                
                product.save()
        
        # پاک کردن تمامی سبدهای منقضی شده 
        # (آیتم‌های سبد خرید نیز به دلیل on_delete=models.CASCADE خودکار حذف می‌شوند)
        expired_carts.delete()

    return f"تعداد {carts_count} سبد خرید منقضی شده حذف و موجودی‌ها آزاد گردید."