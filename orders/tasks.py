import asyncio
from celery import shared_task
from telegram import Bot
from decouple import config
from .models import Order

@shared_task
def send_telegram_receipt(order_id):
    """
    ارسال پیام موفقیت آمیز بودن خرید به خریدار و ادمین مختص به همان فروشگاه
    """
    try:
        # واکشی سفارش به همراه اطلاعات کاربر و فروشگاه (برای بهینه‌سازی کوئری)
        order = Order.objects.select_related('user', 'store').get(id=order_id)
    except Order.DoesNotExist:
        return "سفارش یافت نشد."

    store = order.store
    
    # دریافت توکن ربات و آیدی ادمین از تنظیمات فروشگاه در دیتابیس
    bot_token = store.bot_token
    admin_chat_id = store.admin_chat_id

    if not bot_token:
        return "توکن ربات برای این فروشگاه ثبت نشده است."

    bot = Bot(token=bot_token)

    # متن پیام خریدار
    buyer_text = (
        f"✅ پرداخت شما در {store.bot_username or 'گالری'} با موفقیت تایید شد!\n\n"
        f"شماره سفارش: {order.id}\n"
        f"مبلغ پرداختی: {order.total_amount:,} تومان\n"
        f"کد پیگیری تراکنش: {order.ref_id}\n\n"
        f"سفارش شما به زودی پردازش می‌شود."
    )

    # متن پیام ادمین فروشگاه
    admin_text = (
        f"💰 یک سفارش جدید در فروشگاه شما با موفقیت ثبت و پرداخت شد!\n\n"
        f"📱 شماره مشتری: {order.user.phone_number}\n"
        f"💵 مبلغ: {order.total_amount:,} تومان\n"
        f"🧾 کد پیگیری زرین‌پال: {order.ref_id}\n"
        f"🔗 شناسه سفارش: {order.id}"
    )

    async def send_messages():
        # ارسال به خریدار
        if order.user.chat_id:
            try:
                await bot.send_message(chat_id=order.user.chat_id, text=buyer_text)
            except Exception as e:
                print(f"Failed to send message to user: {e}")
        
        # ارسال فقط به ادمین همین فروشگاه
        if admin_chat_id:
            try:
                await bot.send_message(chat_id=admin_chat_id, text=admin_text)
            except Exception as e:
                print(f"Failed to send message to admin: {e}")

    # اجرای حلقه رویداد
    asyncio.run(send_messages())
    return f"رسید با موفقیت برای کاربر و ادمین فروشگاه {store.id} ارسال شد."