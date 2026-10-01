import httpx

def setup_store_webhooks(store):
    domain = "https://parsiancoine.ir" # دامنه سرور شما
    results = []
    
    # ۱. تنظیم وب‌هوک تلگرام
    if store.telegram_bot_token:
        url = f"{domain}/api/v1/webhook/{store.telegram_bot_token}/"
        res = httpx.post(f"https://api.telegram.org/bot{store.telegram_bot_token}/setWebhook", data={"url": url})
        results.append(f"Telegram: {res.json().get('description')}")
        
    # ۲. تنظیم وب‌هوک بله
    if store.bale_bot_token:
        url = f"{domain}/api/v1/webhook/{store.bale_bot_token}/"
        res = httpx.post(f"https://tapi.bale.ai/bot{store.bale_bot_token}/setWebhook", data={"url": url})
        results.append(f"Bale: {res.json().get('description')}")
        
    return results