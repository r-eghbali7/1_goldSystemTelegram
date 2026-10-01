import requests
import json
from django.http import HttpResponse
from decouple import config
from rest_framework import status, views
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.core.cache import cache

from .models import Order, OrderItem
from carts.models import Cart
from .services import generate_payment_link
from .tasks import send_telegram_receipt

MERCHANT_ID = config('ZARINPAL_MERCHANT_ID')
ZARINPAL_VERIFY_URL = 'https://api.zarinpal.com/pg/v4/payment/verify.json'


class CheckoutAPIView(views.APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        # ۱. دریافت و اعتبارسنجی فروشگاه
        store_id = request.headers.get('X-Store-ID')
        if not store_id:
            return Response({"detail": "شناسه فروشگاه الزامی است."}, status=status.HTTP_400_BAD_REQUEST)

        # ۲. واکشی سبد خرید با استفاده از prefetch_related برای بهینه‌سازی کوئری دیتابیس
        cart = Cart.objects.filter(
            user=request.user, 
            store_id=store_id, 
            is_paid=False
        ).select_related('user').prefetch_related('items__product').order_by('-created_at').first()
        
        if not cart or cart.is_expired or cart.items.count() == 0:
            return Response({"detail": "سبد خرید نامعتبر است یا منقضی شده."}, status=status.HTTP_400_BAD_REQUEST)

        # ۳. 🛡️ لایه امنیتی اول: دریافت قیمت زنده از Redis
        current_gold_price = cache.get('live_gold_18k')
        if not current_gold_price:
            # اگر اسکریپر از کار افتاده باشد یا ردیس خالی باشد، تراکنش باید متوقف شود
            # تا طلا با قیمت صفر یا اشتباه فروخته نشود.
            return Response(
                {"detail": "ارتباط با سرور قیمت‌گذاری برقرار نشد. لطفاً چند دقیقه دیگر مجدداً تلاش کنید."}, 
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        # ۴. 🛡️ لایه امنیتی دوم: محاسبه مجدد قیمت در لحظه پرداخت (جلوگیری از خرید با قیمت قدیمی)
        total_order_amount = 0
        order_items_to_create = []

        for cart_item in cart.items.all():
            product = cart_item.product
            
            # استفاده از متد محاسبه مدلی که در مرحله قبل نوشتیم
            final_item_price = product.calculate_live_price(current_gold_price)
            total_order_amount += final_item_price
            
            # آماده‌سازی دیتا برای ثبت در فاکتور نهایی
            order_items_to_create.append(
                OrderItem(
                    # order=order, (در مرحله بعد ست می‌شود)
                    product=product,
                    purchased_price=final_item_price,
                    gold_weight=product.weight
                )
            )

        # جلوگیری از صدور فاکتور با مبلغ صفر یا منفی
        if total_order_amount <= 0:
            return Response({"detail": "مبلغ کل فاکتور نامعتبر است."}, status=status.HTTP_400_BAD_REQUEST)

        # ۵. ساخت فاکتور نهایی (Order)
        order = Order.objects.create(
            user=request.user,
            store_id=store_id,
            total_amount=total_order_amount
        )

        # ۶. اتصال و ثبت آیتم‌های فاکتور به صورت Bulk (افزایش چشمگیر سرعت دیتابیس)
        for item in order_items_to_create:
            item.order = order
        OrderItem.objects.bulk_create(order_items_to_create)

        # ۷. بستن سبد خرید برای جلوگیری از پرداخت تکراری
        cart.is_paid = True
        cart.save()

        # ۸. ساخت لینک پرداخت داینامیک زرین‌پال
        success, result = generate_payment_link(order.id)
        
        if success:
            return Response({
                "payment_url": result, 
                "order_id": order.id,
                "final_amount": total_order_amount, # ارسال مبلغ نهایی به تلگرام برای نمایش به کاربر
                "live_gold_price": current_gold_price
            }, status=status.HTTP_200_OK)
        else:
            # اگر درگاه خطا داد، تراکنش دیتابیس به لطف transaction.atomic به صورت خودکار Rollback نمی‌شود 
            # اما فاکتور در وضعیت pending باقی می‌ماند که منطق درستی است.
            return Response({"detail": result}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


        
# orders/views.py
import requests
import json
from django.http import HttpResponse
from decouple import config
from .models import Order
from .tasks import send_telegram_receipt

MERCHANT_ID = config('ZARINPAL_MERCHANT_ID')
ZARINPAL_VERIFY_URL = 'https://api.zarinpal.com/pg/v4/payment/verify.json'

def zarinpal_callback_view(request):
    authority = request.GET.get('Authority')
    status_payment = request.GET.get('Status')

    if status_payment != 'OK':
        Order.objects.filter(authority=authority).update(status='failed')
        return HttpResponse("پرداخت لغو شد یا ناموفق بود. می‌توانید پنجره را بسته و به ربات بازگردید.")

    try:
        order = Order.objects.get(authority=authority)
    except Order.DoesNotExist:
        return HttpResponse("سفارش یافت نشد.")

    # جلوگیری از وریفای مجدد فاکتوری که قبلاً پرداخت شده است
    if order.status == 'paid':
        return HttpResponse("این فاکتور قبلاً با موفقیت پرداخت شده است. می‌توانید به ربات بازگردید.")

    data = {
        "merchant_id": MERCHANT_ID,
        "amount": int(order.total_amount) * 10,  # تبدیل به ریال
        "authority": authority
    }
    headers = {'content-type': 'application/json', 'accept': 'application/json'}

    try:
        response = requests.post(ZARINPAL_VERIFY_URL, data=json.dumps(data), headers=headers, timeout=10)
        result = response.json()

        if response.status_code == 200 and result['data']['code'] in [100, 101]:
            ref_id = result['data']['ref_id']
            order.status = 'paid'
            order.ref_id = ref_id
            order.save()
            
            # ارسال رسید به صورت ناهمگام (سلری تشخیص می‌دهد بله است یا تلگرام)
            send_telegram_receipt.delay(order.id)
            
            return HttpResponse(f"پرداخت با موفقیت انجام شد. کد پیگیری: {ref_id}<br><br>اکنون می‌توانید به ربات پیام‌رسان بازگردید.")
        else:
            order.status = 'failed'
            order.save()
            return HttpResponse("تراکنش ناموفق بود یا توسط بانک تایید نشد.")
            
    except requests.exceptions.RequestException:
        return HttpResponse("خطا در برقراری ارتباط با سرورهای زرین‌پال. لطفاً با پشتیبانی تماس بگیرید.")