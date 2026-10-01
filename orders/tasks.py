import asyncio
from celery import shared_task
from telegram import Bot
# ایمپورت خطاهای اختصاصی کتابخانه تلگرام
from telegram.error import NetworkError, TimedOut, TelegramError 
from decouple import config
from .models import Order

# ۱. اضافه کردن قابلیت bind و محدودیت‌های تلاش مجدد به دکوراتور
@shared_task(bind=True, max_retries=5, default_retry_delay=60)
def send_telegram_receipt(self, order_id):
    try:
        order = Order.objects.select_related('user', 'store').get(id=order_id)
    except Order.DoesNotExist:
        return "سفارش یافت نشد."

    store = order.store
    
    # تشخیص هوشمند پلتفرم و توکن بر اساس معماری چندکاناله
    platform = getattr(store, 'platform', 'telegram') 
    bot_token = store.bale_bot_token if platform == 'bale' else store.telegram_bot_token
    admin_chat_id = store.admin_chat_id

    if not bot_token:
        return "توکن ربات برای این فروشگاه ثبت نشده است."

    base_url = "https://tapi.bale.ai/bot" if platform == 'bale' else "https://api.telegram.org/bot"
    bot = Bot(token=bot_token, base_url=base_url)

    buyer_text = f"✅ پرداخت شما در {store.bot_username or 'گالری'} با موفقیت تایید شد!\nشماره سفارش: {order.id}\nمبلغ پرداختی: {order.total_amount:,} تومان\nکد پیگیری تراکنش: {order.ref_id}"
    admin_text = f"💰 یک سفارش جدید در فروشگاه شما با موفقیت ثبت و پرداخت شد!\nشماره مشتری: {order.user.phone_number}\nمبلغ: {order.total_amount:,} تومان\nکد پیگیری زرین‌پال: {order.ref_id}"

    async def send_messages():
        network_failure = False
        
        # ارسال به خریدار
        if order.user.chat_id:
            try:
                await bot.send_message(chat_id=order.user.chat_id, text=buyer_text)
            except (NetworkError, TimedOut):
                # خطای سرور یا اینترنت - نیاز به تلاش مجدد
                network_failure = True 
            except TelegramError as e:
                # خطای منطقی (مثلا کاربر ربات را بلاک کرده) - تلاش مجدد نیاز نیست
                print(f"Logic Error (Buyer): {e}")

        # ارسال به ادمین
        if admin_chat_id:
            try:
                await bot.send_message(chat_id=admin_chat_id, text=admin_text)
            except (NetworkError, TimedOut):
                network_failure = True
            except TelegramError as e:
                print(f"Logic Error (Admin): {e}")

        return network_failure

    # ۲. اجرای توابع و دریافت وضعیت قطعی شبکه
    has_network_errors = asyncio.run(send_messages())
    
    # ۳. در صورت بروز خطای شبکه، تسک به صف باز می‌گردد
    if has_network_errors:
        # تأخیر تصاعدی (Exponential Backoff): زمان صبر در هر تلاش دو برابر می‌شود
        countdown = self.default_retry_delay * (2 ** self.request.retries)
        raise self.retry(exc=Exception("Network Timeout - Retrying"), countdown=countdown)

    return f"رسید برای فروشگاه {store.id} با موفقیت پردازش شد."