import httpx

def setup_store_webhooks(store):
    # آدرس Ngrok خود را برای تست لوکال اینجا قرار دهید
    domain = "https://tough-times-occur.loca.lt" 
    results = []
    
    if store.telegram_bot_token:
        url = f"{domain}/api/v1/webhook/{store.telegram_bot_token}/"
        res = httpx.post(f"https://api.telegram.org/bot{store.telegram_bot_token}/setWebhook", data={"url": url})
        data = res.json()
        if data.get('ok'):
            results.append(f"✅ تلگرام: {data.get('description')}")
        else:
            results.append(f"❌ خطای تلگرام: {data.get('description')}")
            
    if store.bale_bot_token:
        url = f"{domain}/api/v1/webhook/{store.bale_bot_token}/"
        res = httpx.post(f"https://tapi.bale.ai/bot{store.bale_bot_token}/setWebhook", data={"url": url})
        data = res.json()
        if data.get('ok'):
            results.append(f"✅ بله: {data.get('description')}")
        else:
            results.append(f"❌ خطای بله: {data.get('description')}")
            
    return results



