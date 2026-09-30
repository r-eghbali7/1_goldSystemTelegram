# products/tasks.py
import requests
from bs4 import BeautifulSoup
from celery import shared_task
from django.core.cache import cache
from django.utils import timezone
from .models import DailyGoldPrice

def extract_int(soup, field_name):
    span = soup.find('span', {'data-field': field_name})
    if span:
        return int(span.text.replace(',', '').strip())
    return 0

def calc_change(current, yesterday):
    """تابع کمکی برای محاسبه درصد نوسان"""
    if yesterday and yesterday > 0:
        return round(((current - yesterday) / yesterday) * 100, 2)
    return 0.0

@shared_task
def fetch_live_gold_prices():
    url = "https://www.estjt.ir/tv/"
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # استخراج مقادیر فعلی
        current_price = extract_int(soup, 'IRG18')
        mazaneh_price = extract_int(soup, 'IRG17')
        gold_span = soup.find('span', {'data-field': 'GOLD'})
        ounce_price = float(gold_span.text.replace(',', '').replace('$', '').strip()) if gold_span else 0.0
        
        coin_old = extract_int(soup, 'IRCOLD')
        coin_new = extract_int(soup, 'IRCNEW')
        coin_half = extract_int(soup, 'IRC2')
        coin_quarter = extract_int(soup, 'IRC4')
        coin_gram = extract_int(soup, 'IRCGRAM')

        if current_price == 0:
            return "تگ طلای ۱۸ عیار یافت نشد."

        # ذخیره تمام اطلاعات در دیتابیس (رکورد امروز)
        today = timezone.now().date()
        DailyGoldPrice.objects.update_or_create(
            date=today,
            defaults={
                'price': current_price,
                'coin_old_price': coin_old,
                'coin_new_price': coin_new,
                'coin_half_price': coin_half,
                'coin_quarter_price': coin_quarter,
                'coin_gram_price': coin_gram,
            }
        )
        
        # واکشی رکورد دیروز
        yesterday_record = DailyGoldPrice.objects.filter(date__lt=today).order_by('-date').first()
        
        # مقادیر دیروز (اگر رکوردی نبود، مقدار امروز را در نظر می‌گیریم تا درصد صفر شود)
        y_price = int(yesterday_record.price) if yesterday_record else current_price
        y_old = int(yesterday_record.coin_old_price) if yesterday_record else coin_old
        y_new = int(yesterday_record.coin_new_price) if yesterday_record else coin_new
        y_half = int(yesterday_record.coin_half_price) if yesterday_record else coin_half
        y_quarter = int(yesterday_record.coin_quarter_price) if yesterday_record else coin_quarter
        y_gram = int(yesterday_record.coin_gram_price) if yesterday_record else coin_gram
        
        # ذخیره در کش Redis (قیمت‌های خام + درصدهای تغییر)
        cache.set('live_gold_18k', current_price, timeout=360)
        cache.set('yesterday_gold_18k', y_price, timeout=360)
        cache.set('gold_change_percent', calc_change(current_price, y_price), timeout=360)
        cache.set('live_gold_ounce', ounce_price, timeout=360)
        cache.set('live_mazaneh', mazaneh_price, timeout=360)
        
        cache.set('coin_old', coin_old, timeout=360)
        cache.set('change_coin_old', calc_change(coin_old, y_old), timeout=360)
        
        cache.set('coin_new', coin_new, timeout=360)
        cache.set('change_coin_new', calc_change(coin_new, y_new), timeout=360)
        
        cache.set('coin_half', coin_half, timeout=360)
        cache.set('change_coin_half', calc_change(coin_half, y_half), timeout=360)
        
        cache.set('coin_quarter', coin_quarter, timeout=360)
        cache.set('change_coin_quarter', calc_change(coin_quarter, y_quarter), timeout=360)
        
        cache.set('coin_gram', coin_gram, timeout=360)
        cache.set('change_coin_gram', calc_change(coin_gram, y_gram), timeout=360)

        return "بروزرسانی قیمت‌ها و نوسانات با موفقیت انجام شد."

    except Exception as e:
        return f"خطا در پردازش قیمت: {str(e)}"