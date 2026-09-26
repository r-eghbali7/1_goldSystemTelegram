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
    status = request.GET.get('Status')

    if status != 'OK':
        # پرداخت توسط کاربر لغو شده است
        Order.objects.filter(authority=authority).update(status='failed')
        return HttpResponse("پرداخت لغو شد یا ناموفق بود.")

    try:
        order = Order.objects.get(authority=authority)
    except Order.DoesNotExist:
        return HttpResponse("سفارش یافت نشد.")

    # ارسال درخواست تایید به زرین‌پال
    data = {
        "merchant_id": MERCHANT_ID,
        "amount": int(order.total_amount) * 10, # مبلغ به ریال
        "authority": authority
    }
    headers = {'content-type': 'application/json', 'accept': 'application/json'}

    response = requests.post(ZARINPAL_VERIFY_URL, data=json.dumps(data), headers=headers)
    result = response.json()

    if response.status_code == 200 and result['data']['code'] in [100, 101]:
        # تراکنش موفق (100: موفق، 101: قبلا وریفای شده)
        ref_id = result['data']['ref_id']
        
        # بروزرسانی وضعیت سفارش
        order.status = 'paid'
        order.ref_id = ref_id
        order.save()

        # فراخوانی تسک Celery برای ارسال پیام تلگرام در بک‌گراند
        send_telegram_receipt.delay(order.id)

        return HttpResponse(f"پرداخت با موفقیت انجام شد. کد پیگیری: {ref_id}")
    else:
        order.status = 'failed'
        order.save()
        return HttpResponse("تراکنش ناموفق بود یا تایید نشد.")