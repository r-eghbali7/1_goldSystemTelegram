import asyncio
from celery import shared_task
from telegram import Bot
from decouple import config
from .models import Order

@shared_task
def send_telegram_receipt(order_id):
    """
    ارسال پیام موفقیت آمیز بودن خرید به خریدار و ادمین
    """
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return "سفارش یافت نشد."

    bot_token = config('TELEGRAM_BOT_TOKEN') # توکن ربات که از BotFather گرفتید
    admin_chat_id = config('ADMIN_TELEGRAM_CHAT_ID')
    
    bot = Bot(token=bot_token)

    # متن پیام خریدار
    buyer_text = (
        f"✅ پرداخت شما با موفقیت تایید شد!\n\n"
        f"شماره سفارش: {order.id}\n"
        f"مبلغ پرداختی: {order.total_amount:,} تومان\n"
        f"کد پیگیری تراکنش: {order.ref_id}\n\n"
        f"سفارش شما به زودی پردازش می‌شود."
    )

    # متن پیام ادمین
    admin_text = (
        f"💰 یک سفارش جدید با موفقیت ثبت و پرداخت شد!\n\n"
        f"📱 شماره مشتری: {order.user.phone_number}\n"
        f"👤 شناسه خریدار: {order.user.chat_id}\n"
        f"💵 مبلغ: {order.total_amount:,} تومان\n"
        f"🧾 کد پیگیری زرین‌پال: {order.ref_id}\n"
        f"🔗 شناسه سفارش (UUID): {order.id}"
    )

    # تعریف تابع Asynchronous برای ارسال پیام‌ها
    async def send_messages():
        # پیام خریدار (اگر chat_id او را داریم)
        if order.user.chat_id:
            try:
                await bot.send_message(chat_id=order.user.chat_id, text=buyer_text)
            except Exception as e:
                print(f"Failed to send message to user: {e}")
        
        # پیام ادمین
        try:
            await bot.send_message(chat_id=admin_chat_id, text=admin_text)
        except Exception as e:
            print(f"Failed to send message to admin: {e}")

    # اجرای حلقه رویداد (Event Loop) برای فراخوانی متدهای ناهمگام
    asyncio.run(send_messages())
    
    return "پیام‌های رسید با موفقیت به تلگرام ارسال شدند."