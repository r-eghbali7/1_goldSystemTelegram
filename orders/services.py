import requests
import json
from decouple import config

MERCHANT_ID = config('ZARINPAL_MERCHANT_ID')
# آدرسی که کاربر پس از پرداخت به آن بازمی‌گردد (باید در URL های جنگو تعریف شود)
CALLBACK_URL = config('ZARINPAL_CALLBACK_URL') 

ZARINPAL_REQUEST_URL = 'https://api.zarinpal.com/pg/v4/payment/request.json'
ZARINPAL_STARTPAY_URL = 'https://www.zarinpal.com/pg/StartPay/'

def generate_payment_link(order_id):
    from .models import Order
    order = Order.objects.get(id=order_id)
    
    headers = {
        'accept': 'application/json',
        'content-type': 'application/json'
    }
    
    data = {
        'merchant_id': MERCHANT_ID,
        # زرین‌پال مبالغ را به ریال دریافت می‌کند، بنابراین در ۱۰ ضرب می‌شود
        'amount': int(order.total_amount) * 10, 
        'description': f"پرداخت فاکتور فروشگاه طلا - سفارش {order.id}",
        'callback_url': CALLBACK_URL,
        'metadata': {
            'mobile': order.user.phone_number,
        }
    }

    try:
        response = requests.post(ZARINPAL_REQUEST_URL, data=json.dumps(data), headers=headers, timeout=10)
        result = response.json()
        
        if response.status_code == 200 and result['data']['code'] == 100:
            authority = result['data']['authority']
            
            # ذخیره کد ارجاع برای تطبیق هنگام بازگشت از درگاه
            order.authority = authority
            order.save()
            
            payment_url = f"{ZARINPAL_STARTPAY_URL}{authority}"
            return True, payment_url
            
        return False, "خطا در ساخت لینک پرداخت از سمت زرین‌پال"
        
    except requests.exceptions.RequestException:
        return False, "خطا در ارتباط با سرور زرین‌پال"