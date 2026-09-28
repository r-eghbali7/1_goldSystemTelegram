
import asyncio
from celery import shared_task
from telegram import Update
from stores.models import Store
from core.tenant import set_current_store
# فرض می‌کنیم متد get_bot_application را در فایلی مثل api/utils.py یا api/bot.py تعریف کرده‌اید
from api.views import get_bot_application 

@shared_task
def process_telegram_update_task(bot_token, update_data):
    """
    پردازش آپدیت تلگرام در بک‌گراند توسط Celery
    """
    try:
        # ۱. تنظیم کانتکست ایزوله فروشگاه برای این Worker
        store = Store.objects.get(bot_token=bot_token, is_active=True)
        set_current_store(store.id)
    except Store.DoesNotExist:
        return f"Store with token {bot_token} not found or inactive."

    # ۲. تعریف یک تابع async داخلی برای اجرای کدهای تلگرام
    async def run_bot_update():
        application = get_bot_application(bot_token)
        # تبدیل دیتای دیکشنری به آبجکت Update تلگرام
        update = Update.de_json(update_data, application.bot)
        
        await application.initialize()
        await application.process_update(update)

    # ۳. اجرای تابع async در محیط sync سلری
    asyncio.run(run_bot_update())
    
    return f"Update for store {store.bot_username} processed."