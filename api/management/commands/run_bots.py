import asyncio
from django.core.management.base import BaseCommand
from telegram.ext import TypeHandler
from telegram import Update

from stores.models import Store
from api.views import get_bot_application
from core.tenant import set_current_store


async def run_multiple_bots(applications):
    """
    اجرای همزمان چندین ربات در حالت پولینگ با استفاده از asyncio
    """
    for app in applications:
        await app.initialize()
        
        # پاک کردن وب‌هوک قبلی برای جلوگیری از خطای تداخل وب‌هوک و پولینگ
        await app.bot.delete_webhook(drop_pending_updates=True)
        
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
    
    stop_event = asyncio.Event()
    try:
        # نگه‌داشتن Event Loop برای فعال ماندن ربات‌ها
        await stop_event.wait()
    except asyncio.exceptions.CancelledError:
        pass
    finally:
        for app in applications:
            await app.updater.stop()
            await app.stop()
            await app.shutdown()


class Command(BaseCommand):
    help = 'اجرای ربات‌های بله و تلگرام در حالت Polling برای تست لوکال (بدون تداخل با Webhook)'

    def handle(self, *args, **options):
        # دریافت تمامی فروشگاه‌های فعال
        stores = Store.objects.filter(is_active=True)
        applications = []

        for store in stores:
            # میدل‌ور برای تنظیم ContextVar مربوط به Tenant هر فروشگاه در حالت پولینگ
            def create_tenant_middleware(store_id):
                async def tenant_middleware(update: Update, context):
                    set_current_store(store_id)
                return tenant_middleware

            # راه‌اندازی ربات تلگرام در صورت وجود توکن
            if store.telegram_bot_token:
                self.stdout.write(f"Preparing Telegram bot for store ID: {store.id}")
                app_tg = get_bot_application(store, store.telegram_bot_token)
                
                # تزریق میدل‌ور قبل از اجرای سایر هندلرها (با گروه منفی)
                app_tg.add_handler(TypeHandler(Update, create_tenant_middleware(store.id)), group=-100)
                applications.append(app_tg)
                
            # راه‌اندازی ربات بله در صورت وجود توکن
            if store.bale_bot_token:
                self.stdout.write(f"Preparing Bale bot for store ID: {store.id}")
                app_bale = get_bot_application(store, store.bale_bot_token)
                
                app_bale.add_handler(TypeHandler(Update, create_tenant_middleware(store.id)), group=-100)
                applications.append(app_bale)

        if not applications:
            self.stdout.write(self.style.WARNING("هیچ ربات فعالی برای اجرای پولینگ یافت نشد!"))
            return

        self.stdout.write(self.style.SUCCESS(f"در حال اجرای {len(applications)} ربات در حالت Polling..."))
        
        try:
            # اجرای غیرهمزمان تمامی ربات‌ها
            asyncio.run(run_multiple_bots(applications))
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\nدر حال متوقف کردن ربات‌ها..."))