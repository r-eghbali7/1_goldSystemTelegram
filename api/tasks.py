# api/tasks.py
import asyncio
from celery import shared_task
from telegram import Update
from stores.models import Store
from core.tenant import set_current_store
from django.db.models import Q

@shared_task
def process_telegram_update_task(bot_token, update_data):
    from api.views import get_bot_application 
    
    try:
        store = Store.objects.get(
            Q(telegram_bot_token=bot_token) | Q(bale_bot_token=bot_token), 
            is_active=True
        )
        set_current_store(store.id)
    except Store.DoesNotExist:
        return f"Store with token {bot_token} not found or inactive."

    async def run_bot_update():
        # 👇 ارسال شیء کامل store به تابع
        application = get_bot_application(store)
        update = Update.de_json(update_data, application.bot)
        
        await application.initialize()
        await application.process_update(update)

    asyncio.run(run_bot_update())
    return f"Update for store {store.bot_username} processed."