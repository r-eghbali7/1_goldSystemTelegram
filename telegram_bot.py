import os
import httpx
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# لود کردن متغیرهای محیطی از فایل .env
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# آدرس پایه APIهای جنگو (در حالت لوکال)
BASE_API_URL = "http://127.0.0.1:8000/api/v1"

# تعریف مراحل (States) برای ConversationHandler
WAITING_FOR_OTP = 1

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /start و درخواست شماره تماس"""
    # بررسی اینکه آیا کاربر از قبل توکن لاگین دارد یا خیر
    if 'access_token' in context.user_data:
        await show_main_menu(update, context)
        return ConversationHandler.END

    # ساخت دکمه درخواست شماره تماس امن تلگرام
    keyboard = [[KeyboardButton(text="ارسال شماره تماس 📱", request_contact=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text(
        "به فروشگاه طلا و جواهر خوش آمدید! 🌟\n"
        "برای مشاهده محصولات و ثبت سفارش، لطفاً شماره تماس خود را از طریق دکمه زیر ارسال کنید:",
        reply_markup=reply_markup
    )
    # از آنجا که دریافت کانتکت هندلر خودش را دارد، نیازی به تغییر وضعیت در اینجا نیست
    return ConversationHandler.END

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت شماره تماس کاربر و درخواست ارسال پیامک از جنگو"""
    contact = update.message.contact
    phone_number = contact.phone_number

    # فرمت کردن شماره (گاهی تلگرام شماره را با کد کشور مثلا +98912... می‌فرستد)
    if phone_number.startswith('+98'):
        phone_number = '0' + phone_number[3:]
    elif phone_number.startswith('98'):
        phone_number = '0' + phone_number[2:]

    # ذخیره موقت شماره برای مرحله بعد
    context.user_data['temp_phone'] = phone_number

    # ارسال درخواست به API جنگو (Send OTP)
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BASE_API_URL}/accounts/send-otp/",
                json={"phone_number": phone_number},
                timeout=10.0
            )
            
            if response.status_code == 200:
                await update.message.reply_text(
                    f"کد تایید به شماره {phone_number} پیامک شد.\nلطفاً کد ۵ رقمی را ارسال کنید:",
                    reply_markup=ReplyKeyboardRemove()
                )
                return WAITING_FOR_OTP
            elif response.status_code == 429:
                await update.message.reply_text("شما به تازگی درخواست کد داده‌اید. لطفاً کمی صبر کنید.")
                return ConversationHandler.END
            else:
                error_detail = response.json().get('detail', 'خطای نامشخص')
                await update.message.reply_text(f"خطا در ارسال کد: {error_detail}")
                return ConversationHandler.END
                
        except httpx.RequestError:
            await update.message.reply_text("ارتباط با سرور قطع شده است. لطفاً بعداً تلاش کنید.")
            return ConversationHandler.END

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
                # ذخیره توکن در مموری ربات برای استفاده در APIهای بعدی
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
        [KeyboardButton("مشاهده فروشگاه 💎")],
        [KeyboardButton("سبد خرید 🛒"), KeyboardButton("پشتیبانی 🎧")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    # اگر از داخل تابع دیگری فراخوانی شده باشد ممکن است update.message در دسترس نباشد (مثل callback)
    message = update.message if update.message else update.callback_query.message
    await message.reply_text("لطفاً یک گزینه را انتخاب کنید:", reply_markup=reply_markup)

def main():
    """اجرای ربات به روش Polling (مناسب برای توسعه و تست)"""
    application = Application.builder().token(TOKEN).build()

    # تعریف سیستم State Machine برای گرفتن شماره و کد
    auth_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.CONTACT, handle_contact)],
        states={
            WAITING_FOR_OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, verify_otp)],
        },
        fallbacks=[CommandHandler('start', start)]
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(auth_conv_handler)
    
    # اینجا هندلرهای مربوط به دکمه‌های منوی اصلی در آینده اضافه می‌شود
    
    print("ربات در حال اجراست...")
    application.run_polling()

if __name__ == '__main__':
    main()