# products/tasks.py
import requests
from bs4 import BeautifulSoup
from celery import shared_task
from django.core.cache import cache

@shared_task
def fetch_live_gold_prices():
    url = "https://www.estjt.ir/tv/"
    try:
        # دریافت سورس صفحه با تایم‌اوت مشخص
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # استخراج قیمت طلای 18 عیار بر اساس data-field
        irg18_span = soup.find('span', {'data-field': 'IRG18'})
        
        if irg18_span:
            # حذف کاما و تبدیل به عدد صحیح
            price_18k = int(irg18_span.text.replace(',', ''))
            
            # ذخیره در کش برای 6 دقیقه (تا تسک بعدی که 5 دقیقه دیگر است)
            cache.set('live_gold_18k', price_18k, timeout=360)
            
            # در صورت نیاز می‌توانید بقیه موارد مثل انس یا سکه را هم اینجا استخراج و کش کنید
            
        return f"قیمت طلای 18 عیار بروز شد: {price_18k}"
    except Exception as e:
        return f"خطا در دریافت قیمت زنده: {str(e)}"