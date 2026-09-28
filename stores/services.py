# stores/services.py
import httpx
from django.conf import settings

def set_telegram_webhook(bot_token):
    # آدرس سرور شما (باید HTTPS باشد)
    domain = "https://parsiancoine.ir"
    webhook_url = f"{domain}/api/v1/webhook/{bot_token}/"
    
    telegram_api = f"https://api.telegram.org/bot{bot_token}/setWebhook"
    
    response = httpx.post(telegram_api, data={"url": webhook_url})
    return response.json()