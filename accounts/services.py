import random
from django.core.cache import cache
from kavenegar import KavenegarAPI, APIException, HTTPException
from decouple import config

def send_otp_code(phone_number):
    cache_key = f'otp_{phone_number}'
    ttl = cache.ttl(cache_key)
    
    # Rate Limiting: اگر کمتر از 90 ثانیه از درخواست قبلی گذشته باشد، پیامک جدید ارسال نمی‌شود
    if ttl and ttl > 30: 
        return False, "لطفاً تا پایان زمان تایمر صبر کنید."

    otp = random.randint(10000, 99999)
    cache.set(cache_key, otp, timeout=120) # اعتبار 2 دقیقه
    
    try:
        api = KavenegarAPI(config('KAVENEGAR_API_KEY'))
        params = {
            'receptor': phone_number,
            'template': 'VerifyTemplateName', 
            'token': otp,
            'type': 'sms'
        }
        api.verify_lookup(params)
        return True, "کد تایید ارسال شد."
    except (APIException, HTTPException) as e:
        return False, "خطا در ارتباط با سرویس پیامک."

def verify_otp_code(phone_number, code):
    cache_key = f'otp_{phone_number}'
    cached_code = cache.get(cache_key)
    
    if cached_code and str(cached_code) == str(code):
        cache.delete(cache_key)
        return True
    return False