import os
import re
import httpx
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, PicklePersistence
import datetime




# لود کردن متغیرهای محیطی از فایل .env
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_TELEGRAM_CHAT_ID")

# آدرس پایه APIهای جنگو (در حالت لوکال)
BASE_API_URL = "http://127.0.0.1:8000/api/v1"
DJANGO_SERVER_URL = "http://127.0.0.1:8000"

# تعریف مراحل (States) برای ConversationHandler
WAITING_FOR_OTP = 1
SUPPORT_MODE = 2

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /start و درخواست شماره تماس"""
    if 'access_token' in context.user_data:
        await show_main_menu(update, context)
        return ConversationHandler.END

    keyboard = [[KeyboardButton(text="ارسال شماره تماس 📱", request_contact=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text(
        "به فروشگاه طلا و جواهر خوش آمدید! 🌟\n"
        "برای مشاهده محصولات و ثبت سفارش، لطفاً شماره تماس خود را از طریق دکمه زیر ارسال کنید:",
        reply_markup=reply_markup
    )
    return ConversationHandler.END


async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت شماره تماس و لاگین مستقیم در جنگو"""
    contact = update.message.contact
    
    # 🛡️ بررسی امنیتی: جلوگیری از فوروارد کردن شماره دیگران
    if contact.user_id != update.message.from_user.id:
        await update.message.reply_text("❌ لطفاً فقط شماره تماس خودتان را با استفاده از دکمه کیبورد ارسال کنید.")
        return

    phone_number = contact.phone_number
    chat_id = str(update.message.chat_id)
    first_name = contact.first_name or ""
    last_name = contact.last_name or ""

    # نرمال‌سازی شماره موبایل
    if phone_number.startswith('+98'):
        phone_number = '0' + phone_number[3:]
    elif phone_number.startswith('98'):
        phone_number = '0' + phone_number[2:]
    elif not phone_number.startswith('0'):
        phone_number = '0' + phone_number

    await update.message.reply_text("⏳ در حال بررسی اطلاعات...")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BASE_API_URL}/accounts/telegram-login/",
                json={
                    "phone_number": phone_number, 
                    "chat_id": chat_id,
                    "first_name": first_name,
                    "last_name": last_name
                },
                timeout=15.0
            )
            
            # 🔍 لاگ‌های ترمینال برای دیباگ کردن شما
            print(f"--- Telegram Login Debug ---")
            print(f"Status Code: {response.status_code}")
            print(f"Response Body: {response.text}")
            print(f"----------------------------")
            
            if response.status_code == 200:
                data = response.json()
                context.user_data['access_token'] = data['tokens']['access']
                
                await update.message.reply_text(
                    "✅ احراز هویت با موفقیت انجام شد!\nشماره شما در سیستم ثبت گردید.",
                    reply_markup=ReplyKeyboardRemove()
                )
                await show_main_menu(update, context)
            else:
                try:
                    error_detail = response.json().get('detail', 'خطای نامشخص')
                except ValueError:
                    error_detail = f"ارور سرور (کد {response.status_code})"
                await update.message.reply_text(f"❌ خطا در ثبت‌نام: {error_detail}")

        except httpx.RequestError as e:
            print(f"Request Error: {e}")
            await update.message.reply_text("❌ ارتباط با سرور قطع شده است. لطفاً بعداً تلاش کنید.")



async def verify_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت کد وارد شده توسط کاربر و دریافت توکن JWT از جنگو"""
    code = update.message.text
    phone_number = context.user_data.get('temp_phone')
    chat_id = str(update.message.chat_id)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BASE_API_URL}/accounts/verify-otp/",
                json={"phone_number": phone_number, "code": code, "chat_id": chat_id},
                timeout=10.0
            )
            
            if response.status_code == 200:
                data = response.json()
                context.user_data['access_token'] = data['tokens']['access']
                
                await update.message.reply_text("احراز هویت با موفقیت انجام شد! ✅")
                await show_main_menu(update, context)
                return ConversationHandler.END
            else:
                await update.message.reply_text("کد وارد شده اشتباه است یا منقضی شده. مجدداً تلاش کنید:")
                return WAITING_FOR_OTP
                
        except httpx.RequestError:
            await update.message.reply_text("ارتباط با سرور قطع شده است.")
            return ConversationHandler.END

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش منوی اصلی ربات پس از لاگین"""
    keyboard = [
            [KeyboardButton("مشاهده فروشگاه 💎"), KeyboardButton("نرخ زنده بازار 📈")], # 👈 دکمه اضافه شد
            [KeyboardButton("سبد خرید 🛒"), KeyboardButton("پشتیبانی 🎧")]
        ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    message = update.message if update.message else update.callback_query.message
    await message.reply_text("لطفاً یک گزینه را انتخاب کنید:", reply_markup=reply_markup)


async def view_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت اطلاعات سبد خرید از API و نمایش پیش‌فاکتور"""
    access_token = context.user_data.get('access_token')
    
    if not access_token:
        await update.message.reply_text("لطفاً ابتدا احراز هویت کنید. دستور /start را بزنید.")
        return

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_API_URL}/carts/", headers=headers, timeout=10.0)
            
            if response.status_code == 404:
                await update.message.reply_text("سبد خرید شما خالی است 🛒")
                return
            elif response.status_code == 200:
                cart_data = response.json()
                items = cart_data.get('items', [])
                total_price = cart_data.get('total_price', 0)
                
                if not items:
                    await update.message.reply_text("سبد خرید شما خالی است 🛒")
                    return

                text = "🧾 **پیش فاکتور شما:**\n\n"
                for idx, item in enumerate(items, 1):
                    p_type = item.get('product_type')
                    product_title = item['product']['title']
                    final_price = item['final_price']
                
                text += f"*{idx}. {product_title}*\n"
                
                if p_type == 'ornamental':
                    text += f"▫️ طلای خام: {int(item['raw_gold_value']):,} ت\n"
                    text += f"▫️ اجرت: {int(item['wage']):,} ت\n"
                    text += f"▫️ سود ({item['profit_percent']}٪): {int(item['profit_value']):,} ت\n"
                    text += f"▫️️ مالیات ({item['tax_percent']}٪): {int(item['tax_value']):,} ت\n"
                elif p_type == 'parsian':
                    text += f"▫️ ارزش طلا: {int(item['raw_gold_value']):,} ت\n"
                    text += f"▫️ سود: {int(item['profit_value']):,} ت\n"
                    text += f"▫️ بسته‌بندی/صدور: {int(item['constant_fee']):,} ت\n"
                    
                text += f"✅ **قیمت نهایی:** {final_price:,} تومان\n"
                text += "➖➖➖➖➖➖➖\n"
                
                text += f"💳 **مبلغ کل قابل پرداخت:** {total_price:,} تومان\n"

                keyboard = [
                    [InlineKeyboardButton("تسویه حساب و پرداخت 💳", callback_data="process_checkout")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
            else:
                await update.message.reply_text("مشکلی در دریافت سبد خرید به وجود آمد.")
                
        except httpx.RequestError:
            await update.message.reply_text("خطا در ارتباط با سرور.")

async def process_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تایید نهایی سبد، ساخت سفارش در جنگو و دریافت لینک زرین‌پال"""
    query = update.callback_query
    await query.answer()
    
    access_token = context.user_data.get('access_token')
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    await query.edit_message_text("⏳ در حال اتصال به درگاه پرداخت...")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{BASE_API_URL}/orders/checkout/", headers=headers, timeout=15.0)
            
            if response.status_code == 200:
                data = response.json()
                payment_url = data['payment_url']
                order_id = data['order_id']
                
                keyboard = [
                    [InlineKeyboardButton("رفتن به درگاه زرین‌پال 🔗", url=payment_url)]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                success_text = (
                    f"✅ فاکتور شما با موفقیت صادر شد.\n"
                    f"شماره سفارش: `{order_id}`\n\n"
                    f"برای پرداخت روی دکمه زیر کلیک کنید. پس از پرداخت موفق، نتیجه از همین طریق به شما اطلاع داده می‌شود."
                )
                await query.edit_message_text(success_text, reply_markup=reply_markup, parse_mode="Markdown")
            
            elif response.status_code == 400:
                await query.edit_message_text("❌ سبد خرید شما نامعتبر یا منقضی شده است.")
            else:
                error_detail = response.json().get('detail', 'خطای نامشخص')
                await query.edit_message_text(f"❌ خطا در صدور فاکتور: {error_detail}")
                
        except httpx.RequestError:
            await query.edit_message_text("خطا در برقراری ارتباط با سرور بانکی.")

async def enter_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ورود به بخش پشتیبانی و تغییر کیبورد"""
    keyboard = [[KeyboardButton("بازگشت 🔙")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "🎧 شما به بخش پشتیبانی متصل شدید.\n\n"
        "متن، عکس یا ویس خود را ارسال کنید تا مستقیماً به مدیریت ارجاع داده شود.\n"
        "برای خروج از حالت پشتیبانی، دکمه «بازگشت 🔙» را بزنید.",
        reply_markup=reply_markup
    )
    return SUPPORT_MODE

async def send_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت پیام کاربر و ارسال برای ادمینِ همان فروشگاه"""
    user = update.message.from_user
    
    # فرض بر این است که آبجکت store در context ذخیره شده است (در وب‌هوک)
    store = context.bot_data.get('store')
    admin_chat_id = store.admin_chat_id

    if not admin_chat_id:
        await update.message.reply_text("❌ متاسفانه پشتیبانی برای این فروشگاه فعال نشده است.")
        return SUPPORT_MODE
    
    # فوروارد پیام برای ادمین فروشگاه
    await update.message.copy(chat_id=admin_chat_id)
    
    await context.bot.send_message(
        chat_id=admin_chat_id,
        text=f"👤 فرستنده: {user.first_name}\n💬 آیدی عددی: {user.id}\n"
             f"جهت پاسخ دادن، روی همین پیام ریپلای (Reply) کنید.",
    )

    await update.message.reply_text("✅ پیام شما دریافت شد. مدیریت فروشگاه به زودی پاسخ خواهد داد.")
    return SUPPORT_MODE

async def exit_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """خروج از پشتیبانی و بازگشت به منوی اصلی"""
    await update.message.reply_text("شما از بخش پشتیبانی خارج شدید.")
    await show_main_menu(update, context) 
    return ConversationHandler.END

async def admin_reply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت پاسخ ادمین و ارسال آن برای کاربر"""
    store = context.bot_data.get('store')
    admin_chat_id = store.admin_chat_id

    # بررسی اینکه آیا فرستنده، ادمینِ این فروشگاه است؟
    if str(update.message.chat_id) == str(admin_chat_id) and update.message.reply_to_message:
        original_text = update.message.reply_to_message.text
        
        if original_text and "آیدی عددی:" in original_text:
            import re
            match = re.search(r'آیدی عددی:\s*(\d+)', original_text)
            if match:
                user_chat_id = match.group(1)
                
                try:
                    await context.bot.send_message(chat_id=user_chat_id, text="🎧 پاسخ پشتیبانی گالری:\n")
                    await update.message.copy(chat_id=user_chat_id)
                    await update.message.reply_text("پاسخ شما با موفقیت برای مشتری ارسال شد ✅")
                except Exception as e:
                    await update.message.reply_text(f"خطا در ارسال پیام. ممکن است کاربر ربات را بلاک کرده باشد.\n{e}")

# تغییر در فایل telegram_bot.py (که حالا هندلرهای جنگو است)
async def fetch_and_send_products(chat_id: int, page: int, context: ContextTypes.DEFAULT_TYPE, store_id: str):
    headers = {"X-Store-ID": str(store_id)}
    async with httpx.AsyncClient() as client:
        # ارسال آیدی فروشگاه به API
        response = await client.get(f"{BASE_API_URL}/products/?page={page}", headers=headers)
        try:
            response = await client.get(f"{BASE_API_URL}/products/?page={page}", timeout=10.0)

            if response.status_code == 200:
                data = response.json()
                products = data.get('results', []) 

                if not products:
                    await context.bot.send_message(chat_id, "هیچ محصولی یافت نشد.")
                    return

                for p in products:
                    text = f"💎 **{p['title']}**\n\n"
                    text += f"📝 توضیحات: {p['description']}\n"
                    text += f"⚖️ وزن: {p['weight']} گرم\n"
                    price_int = int(float(p['price']))
                    text += f"💰 قیمت پایه: {price_int:,} تومان\n"

                    keyboard = [[InlineKeyboardButton("افزودن به سبد خرید 🛒", callback_data=f"add_cart_{p['id']}")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)

                    image_path = p.get('image')
                    if image_path:
                        # در حالت لوکال، مسیر نسبی عکس را از آدرس استخراج کرده و فایل را باز می‌کنیم
                        # مثال: image_path مقدارش /media/products/img.jpg است
                        
                        import urllib.parse
                        # جدا کردن بخش آدرس از دامین در صورت وجود
                        parsed_url = urllib.parse.urlparse(image_path)
                        local_file_path = f".{parsed_url.path}" # تبدیل به ./media/products/img.jpg
                        
                        import os
                        if os.path.exists(local_file_path):
                            # ارسال فایل به صورت باینری (آپلود مستقیم از روی سرور/سیستم شما)
                            with open(local_file_path, 'rb') as photo_file:
                                await context.bot.send_photo(chat_id=chat_id, photo=photo_file, caption=text, reply_markup=reply_markup, parse_mode="Markdown")
                        else:
                            # اگر فایل به هر دلیلی روی هارد نبود، فقط متن را بفرست
                            await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode="Markdown")
                    else:
                        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode="Markdown")

            
                nav_buttons = []
                if data.get('previous'):
                    nav_buttons.append(InlineKeyboardButton("◀️ قبلی", callback_data=f"page_{page-1}"))
                
                nav_buttons.append(InlineKeyboardButton(f"صفحه {page}", callback_data="ignore"))
                
                if data.get('next'):
                    nav_buttons.append(InlineKeyboardButton("بعدی ▶️", callback_data=f"page_{page+1}"))

                if len(nav_buttons) > 1:
                    await context.bot.send_message(
                        chat_id=chat_id, 
                        text="🔽 صفحات فروشگاه:", 
                        reply_markup=InlineKeyboardMarkup([nav_buttons])
                    )
            else:
                await context.bot.send_message(chat_id, "خطا در دریافت اطلاعات فروشگاه.")
        except httpx.RequestError:
            await context.bot.send_message(chat_id, "ارتباط با سرور قطع است.")

async def view_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر کلیک روی دکمه 'مشاهده فروشگاه' از کیبورد اصلی"""
    await update.message.reply_text("⏳ در حال دریافت جدیدترین کارهای گالری...")
    await fetch_and_send_products(update.message.chat_id, 1, context)

async def change_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر کلیک روی دکمه‌های صفحه‌بندی (Next/Prev)"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "ignore":
        return

    page_number = int(query.data.split('_')[1])
    
    await query.edit_message_text(f"⏳ در حال بارگذاری صفحه {page_number}...")
    await fetch_and_send_products(query.message.chat_id, page_number, context)
    await query.message.delete()

async def add_to_cart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر کلیک روی دکمه 'افزودن به سبد خرید' محصولات"""
    query = update.callback_query
    
    product_id = query.data.replace('add_cart_', '').strip()
    
    access_token = context.user_data.get('access_token')
    if not access_token:
        await query.answer("❌ لطفاً ابتدا شماره تماس خود را در ربات ثبت کنید.", show_alert=True)
        return

    headers = {"Authorization": f"Bearer {access_token}"}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BASE_API_URL}/carts/", 
                json={"product_id": product_id}, 
                headers=headers
            )
            
            if response.status_code == 201:
                await query.answer("✅ محصول با موفقیت به سبد خرید شما اضافه شد.", show_alert=True)
            elif response.status_code == 400:
                await query.answer("⚠️ این محصول قبلاً در سبد خرید شما ثبت شده است.", show_alert=True)
            elif response.status_code == 401:
                await query.answer("❌ نشست شما منقضی شده است. لطفاً دستور /start را مجدداً ارسال کنید.", show_alert=True)
            else:
                # با این خط، دلیل اصلی خطا در ترمینال شما چاپ می‌شود
                print(f"⚠️ Cart Error: Status {response.status_code} - Body: {response.text}")
                await query.answer("❌ خطا در ثبت سفارش. ارتباط با سرور مشکل دارد.", show_alert=True)
        except httpx.RequestError:
            await query.answer("❌ ارتباط با سرور قطع می‌باشد.", show_alert=True)



def format_price_line(title, price, change_percent):
    """تابع کمکی برای تولید خط متن مربوط به قیمت و درصد رشد"""
    if change_percent > 0:
        sign = "▲"
    elif change_percent < 0:
        sign = "▼"
    else:
        sign = "—"
    
    return f"🪙 {title}: {price:,} تومان ({sign} {abs(change_percent)}%)"


async def fetch_rates_text():
    """تابع کمکی برای دریافت اطلاعات از API و تولید متن پیام"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_API_URL}/products/rates/", timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                
                # مقادیر اصلی
                current = data.get('gold_18k', 0)
                yesterday = data.get('yesterday_gold_18k', 0)
                change = data.get('change_percent', 0.0)
                ounce = data.get('ounce', 0.0)
                mazaneh = data.get('mazaneh', 0)
                
                # خطوط مربوط به سکه‌ها با فرمت جدید
                line_new = format_price_line("سکه امامی", data.get('coin_new', 0), data.get('change_coin_new', 0.0))
                line_old = format_price_line("بهار آزادی", data.get('coin_old', 0), data.get('change_coin_old', 0.0))
                line_half = format_price_line("نیم سکه", data.get('coin_half', 0), data.get('change_coin_half', 0.0))
                line_quarter = format_price_line("ربع سکه", data.get('coin_quarter', 0), data.get('change_coin_quarter', 0.0))
                line_gram = format_price_line("سکه گرمی", data.get('coin_gram', 0), data.get('change_coin_gram', 0.0))
                
                sign = "▲" if change > 0 else ("▼" if change < 0 else "—")
                current_time = datetime.datetime.now().strftime('%H:%M:%S')
                
                text = (
                    "📊 **نرخ لحظه‌ای بازار**\n\n"
                    f"🌍 انس جهانی طلا: {ounce:,} دلار\n"
                    f"⚖️ مظنه تهران: {mazaneh:,} تومان\n"
                    f"💰 طلای ۱۸ عیار: {current:,} تومان\n"
                    f"📈 نوسان طلا (۲۴ ساعت): {sign} {abs(change)}%\n\n"
                    "🟡 **نرخ انواع سکه:**\n"
                    f"{line_new}\n"
                    f"{line_old}\n"
                    f"{line_half}\n"
                    f"{line_quarter}\n"
                    f"{line_gram}\n\n"
                    f"⏱ آخرین بروزرسانی: `{current_time}`"
                )
                return text
            return "❌ دریافت نرخ‌ها موقتاً با مشکل مواجه شده است."
        except httpx.RequestError:
            return "❌ ارتباط با سرور قیمت‌ها قطع می‌باشد."


async def show_live_rates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر کلیک روی دکمه 'نرخ زنده بازار 📈'"""
    text = await fetch_rates_text()
    
    # ساخت دکمه شیشه‌ای
    keyboard = [[InlineKeyboardButton("بروزرسانی 🔄", callback_data="refresh_rates")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def refresh_live_rates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر کلیک روی دکمه شیشه‌ای 'بروزرسانی'"""
    query = update.callback_query
    await query.answer("در حال دریافت قیمت‌های جدید... ⏳") # پیام پاپ‌آپ کوچک
    
    text = await fetch_rates_text()
    keyboard = [[InlineKeyboardButton("بروزرسانی 🔄", callback_data="refresh_rates")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        # آپدیت کردن متن همان پیام بدون ارسال پیام جدید
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    except Exception as e:
        # اگر کاربر دکمه را پشت سر هم بزند و متن تغییری نکرده باشد، تلگرام ارور می‌دهد که ما آن را نادیده می‌گیریم
        if "Message is not modified" in str(e):
            pass



def main():
    """اجرای ربات و ثبت تمامی هندلرها"""
    # پروکسی و سایر تنظیمات... (همان کد قبلی شما)
    persistence = PicklePersistence(filepath="bot_data.pickle")
    application = Application.builder().token(TOKEN).persistence(persistence).build()
    # دیگر نیازی به ConversationHandler برای لاگین نیست
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    application.add_handler(CallbackQueryHandler(add_to_cart_callback, pattern=r'^add_cart_'))
    application.add_handler(CallbackQueryHandler(change_page, pattern=r'^page_'))
    application.add_handler(CallbackQueryHandler(process_checkout, pattern=r'^process_checkout$'))
    application.add_handler(CallbackQueryHandler(refresh_live_rates, pattern=r'^refresh_rates$'))
    
    support_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^پشتیبانی 🎧$'), enter_support)],
        states={
            SUPPORT_MODE: [
                MessageHandler(filters.ALL & ~filters.Regex('^بازگشت 🔙$'), send_to_admin)
            ],
        },
        fallbacks=[MessageHandler(filters.Regex('^بازگشت 🔙$'), exit_support)]
    )

    admin_handler = MessageHandler(
        filters.Chat(chat_id=int(ADMIN_CHAT_ID)) & filters.REPLY, 
        admin_reply_handler
    )
    
    # بقیه هندلرها دقیقاً مثل قبل اضافه شوند
    application.add_handler(MessageHandler(filters.Regex('^نرخ زنده بازار 📈$'), show_live_rates))
    application.add_handler(MessageHandler(filters.Regex('^سبد خرید 🛒$'), view_cart))
    application.add_handler(MessageHandler(filters.Regex('^مشاهده فروشگاه 💎$'), view_shop))
    # ...
    
    application.add_handler(support_conv_handler)
    application.add_handler(admin_handler)
    
    print("🚀 ربات با موفقیت راه‌اندازی شد...")
    application.run_polling()



if __name__ == '__main__':
    main()