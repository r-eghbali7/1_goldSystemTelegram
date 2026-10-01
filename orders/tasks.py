import asyncio
from celery import shared_task
from telegram import Bot
from telegram.error import NetworkError, TimedOut, TelegramError
from .models import Order

@shared_task(bind=True, max_retries=5, default_retry_delay=60)
def send_telegram_receipt(self, order_id):
    try:
        order = Order.objects.select_related('user', 'store').get(id=order_id)
    except Order.DoesNotExist:
        return "سفارش یافت نشد."

    store = order.store
    
    buyer_text = f"✅ پرداخت شما در {store.bot_username or 'گالری'} با موفقیت تایید شد!\nشماره سفارش: {order.id}\nمبلغ پرداختی: {order.total_amount:,} تومان\nکد پیگیری تراکنش: {order.ref_id}"
    admin_text = f"💰 یک سفارش جدید در فروشگاه شما با موفقیت ثبت و پرداخت شد!\nشماره مشتری: {order.user.phone_number}\nمبلغ: {order.total_amount:,} تومان\nکد پیگیری زرین‌پال: {order.ref_id}"

    # تابع کمکی برای تلاش ارسال روی هر دو پیام‌رسان
    async def send_via_bot(token, base_url, chat_id, text):
        if not token or not chat_id:
            return False, False
        bot = Bot(token=token, base_url=base_url)
        try:
            await bot.send_message(chat_id=chat_id, text=text)
            return True, False
        except (NetworkError, TimedOut):
            return False, True # نیاز به تلاش مجدد
        except TelegramError:
            return False, False # آیدی برای این پیام‌رسان نیست


    async def send_messages():
        network_failure = False
        bots = []
        
        if store.telegram_bot_token:
            bots.append({
                'token': store.telegram_bot_token,
                'url': "https://api.telegram.org/bot",
                'admin_chat_id': store.admin_chat_id_telegram,
                'bot_name': store.telegram_bot_username or 'گالری'
            })
            
        if store.bale_bot_token:
            bots.append({
                'token': store.bale_bot_token,
                'url': "https://tapi.bale.ai/bot",
                'admin_chat_id': store.admin_chat_id_bale,
                'bot_name': store.bale_bot_username or 'گالری'
            })

        # ارسال برای خریدار
        buyer_sent = False
        for bot_info in bots:
            if buyer_sent: break
            # داینامیک کردن نام ربات در متن مشتری
            buyer_text = f"✅ پرداخت شما در {bot_info['bot_name']} با موفقیت تایید شد!..."
            
            success, is_net_err = await send_via_bot(bot_info['token'], bot_info['url'], order.user.chat_id, buyer_text)
            if success: buyer_sent = True
            if is_net_err: network_failure = True

        # ارسال برای ادمین
        admin_sent = False
        for bot_info in bots:
            if admin_sent: break
            # استفاده از چت آیدی مختص همان پلتفرم
            success, is_net_err = await send_via_bot(bot_info['token'], bot_info['url'], bot_info['admin_chat_id'], admin_text)
            if success: admin_sent = True
            if is_net_err: network_failure = True

        return network_failure


    has_network_errors = asyncio.run(send_messages())
    
    if has_network_errors:
        countdown = self.default_retry_delay * (2 ** self.request.retries)
        raise self.retry(exc=Exception("Network Timeout - Retrying"), countdown=countdown)

    return "رسید با موفقیت ارسال شد."