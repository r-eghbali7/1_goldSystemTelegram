# api/bot_handlers.py
import os
import re
import datetime
from asgiref.sync import sync_to_async
from django.core.cache import cache
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from accounts.models import User
from products.models import Product
from carts.models import Cart, CartItem
from orders.models import Order, OrderItem
from orders.services import generate_payment_link
from stores.models import StoreCustomer
from core.tenant import get_current_store

ADMIN_CHAT_ID = os.getenv("ADMIN_TELEGRAM_CHAT_ID")

WAITING_FOR_OTP = 1
SUPPORT_MODE = 2
SEARCH_MODE = 10
CALC_WEIGHT, CALC_WAGE, CALC_PROFIT, CALC_TAX = range(3, 7)


calc_cancel_kb = ReplyKeyboardMarkup([[KeyboardButton("انصراف ❌")]], resize_keyboard=True)

# ==========================================
# توابع ارتباط مستقیم با دیتابیس (ORM)
# ==========================================

@sync_to_async
def register_or_get_user(phone_number, chat_id, first_name, last_name, platform):
    user, _ = User.objects.get_or_create(phone_number=phone_number)
    
    # ذخیره آیدی در ستون مربوط به همان پلتفرم
    if platform == 'bale':
        user.bale_chat_id = chat_id
    else:
        user.telegram_chat_id = chat_id
        
    user.first_name = first_name
    user.last_name = last_name
    user.is_verified = True
    user.save()
    
    store_id = get_current_store()
    if store_id:
        StoreCustomer.objects.get_or_create(store_id=store_id, user=user)
    return str(user.id)

@sync_to_async
def get_products_page(page_number, per_page=5):
    from django.core.paginator import Paginator
    # دریافت محصولاتی که موجود و فعال هستند
    qs = Product.objects.filter(is_active=True).order_by('-created_at')
    
    # تنظیم تعداد در هر صفحه (۵ محصول)
    paginator = Paginator(qs, per_page)
    try:
        page = paginator.page(page_number)
    except Exception:
        return [], False, False
        
    return list(page.object_list), page.has_previous(), page.has_next()


async def fetch_and_send_products(chat_id: int, page: int, context: ContextTypes.DEFAULT_TYPE):
    # دریافت ۵ محصول برای صفحه درخواستی
    products, has_prev, has_next = await get_products_page(page, per_page=5)

    if not products:
        await context.bot.send_message(chat_id, "هیچ محصولی یافت نشد.")
        return

    current_gold_price = cache.get('live_gold_18k') or 0

    # ارسال ۵ محصول به صورت پیام‌های جداگانه
    for p in products:
        final_price = p.calculate_live_price(current_gold_price)
        text = f"💎 **{p.title}**\n\n📝 توضیحات: {p.description}\n⚖️ وزن: {p.weight} گرم\n💰 قیمت لحظه‌ای: {final_price:,} تومان\n"
        
        keyboard = [[InlineKeyboardButton("افزودن به سبد خرید 🛒", callback_data=f"add_cart_{p.id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if p.image and hasattr(p.image, 'path') and os.path.exists(p.image.path):
            with open(p.image.path, 'rb') as photo_file:
                await context.bot.send_photo(
                    chat_id=chat_id, 
                    photo=photo_file, 
                    caption=text, 
                    reply_markup=reply_markup, 
                    parse_mode="Markdown"
                )
        else:
            await context.bot.send_message(
                chat_id=chat_id, 
                text=text, 
                reply_markup=reply_markup, 
                parse_mode="Markdown"
            )

    # ایجاد دکمه‌های صفحه‌بندی در یک آرایه دو بعدی برای نمایش زیر هم
    nav_buttons = []
    
    if has_prev:
        nav_buttons.append([InlineKeyboardButton("نمایش محصولات قبلی ⏫", callback_data=f"page_{page-1}")])
        
    if has_next:
        nav_buttons.append([InlineKeyboardButton("ادامه نمایش محصولات ⏬", callback_data=f"page_{page+1}")])

    # اگر محصولی قبل یا بعد وجود داشته باشد دکمه‌ها را می‌فرستیم
    if nav_buttons:
        await context.bot.send_message(
            chat_id=chat_id, 
            text=f"📄 صفحه {page} - برای مشاهده سایر محصولات کلیک کنید:", 
            reply_markup=InlineKeyboardMarkup(nav_buttons)
        )


@sync_to_async
def get_cart_details(user_id):
    store_id = get_current_store()
    cart = Cart.objects.filter(user_id=user_id, store_id=store_id, is_paid=False).first()
    if not cart or cart.is_expired:
        return None
        
    items = []
    for item in cart.items.select_related('product').all():
        items.append({
            'id': str(item.id),
            'title': item.product.title,
            'product_type': item.product.product_type,
            'raw_gold_value': item.raw_gold_value,
            'wage': item.wage_amount, # 👈 اصلاح شد: استفاده از پراپرتی محاسبه شده مبلغ اجرت
            'profit_value': item.profit_value,
            'tax_value': item.tax_value,
            'constant_fee': item.constant_fee,
            'final_price': item.final_item_price
        })
    return {'items': items, 'total_price': cart.total_cart_price}



@sync_to_async
def add_product_to_cart(user_id, product_id, current_gold_price):
    store_id = get_current_store()
    try:
        user = User.objects.get(id=user_id)
        product = Product.objects.get(id=product_id, is_active=True)
    except (User.DoesNotExist, Product.DoesNotExist):
        return False, "کاربر یا محصول یافت نشد."

    cart, _ = Cart.objects.get_or_create(user=user, store_id=store_id, is_paid=False)
    if cart.is_expired:
        cart.refresh_expiration()

    if cart.items.filter(product=product).exists():
        return False, "⚠️ این محصول قبلاً در سبد خرید شما ثبت شده است."

    CartItem.objects.create(
        cart=cart, product=product, daily_gold_price=current_gold_price,
        wage_percent=product.wage_percent, # 👈 اصلاح شد: استفاده از درصد اجرت
        profit_percent=product.profit_percent,
        tax_percent=product.tax_percent, 
        constant_fee=product.constant_fee
    )
    cart.refresh_expiration()
    return True, "✅ محصول با موفقیت به سبد خرید شما اضافه شد."


@sync_to_async
def checkout_cart(user_id, current_gold_price):
    store_id = get_current_store()
    cart = Cart.objects.filter(user_id=user_id, store_id=store_id, is_paid=False).first()
    
    if not cart or cart.is_expired or cart.items.count() == 0:
        return False, "❌ سبد خرید نامعتبر است یا منقضی شده.", None

    total_order_amount = 0
    order_items_to_create = []

    for cart_item in cart.items.all():
        product = cart_item.product
        final_item_price = product.calculate_live_price(current_gold_price)
        total_order_amount += final_item_price
        
        order_items_to_create.append(
            OrderItem(product=product, purchased_price=final_item_price, gold_weight=product.weight)
        )

    if total_order_amount <= 0:
        return False, "❌ مبلغ کل فاکتور نامعتبر است.", None

    order = Order.objects.create(user_id=user_id, store_id=store_id, total_amount=total_order_amount)
    
    for item in order_items_to_create:
        item.order = order
    OrderItem.objects.bulk_create(order_items_to_create)

    cart.is_paid = True
    cart.save()

    success, result = generate_payment_link(order.id)
    if success:
        return True, result, order.id
    return False, "❌ خطا در دریافت لینک پرداخت از زرین‌پال.", None

# ==========================================
# هندلرهای ربات (متصل به تلگرام/بله)
# ==========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'user_id' in context.user_data:
        await show_main_menu(update, context)
        return ConversationHandler.END

    keyboard = [[KeyboardButton(text="ارسال شماره تماس 📱", request_contact=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text(
        "به فروشگاه طلا و جواهر خوش آمدید! 🌟\nبرای مشاهده محصولات و ثبت سفارش، لطفاً شماره تماس خود را ارسال کنید:",
        reply_markup=reply_markup
    )
    return ConversationHandler.END

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    if contact.user_id != update.message.fromuser.id:
        await update.message.reply_text("❌ لطفاً فقط شماره تماس خودتان را با استفاده از دکمه کیبورد ارسال کنید.")
        return

    phone_number = contact.phone_number
    if phone_number.startswith('+98'): phone_number = '0' + phone_number[3:]
    elif phone_number.startswith('98'): phone_number = '0' + phone_number[2:]
    elif not phone_number.startswith('0'): phone_number = '0' + phone_number

    await update.message.reply_text("⏳ در حال ارسال پیامک تایید...")
    
    # ارسال پیامک با سرویس از قبل نوشته شده
    success, msg = send_otp_code(phone_number)
    
    if success:
        # ذخیره موقت اطلاعات
        context.user_data['pending_phone'] = phone_number
        context.user_data['pending_first'] = contact.first_name or ""
        context.user_data['pending_last'] = contact.last_name or ""
        
        await update.message.reply_text("✅ کد تایید ۵ رقمی برای شما پیامک شد. لطفا آن را وارد کنید:", reply_markup=ReplyKeyboardRemove())
        return WAITING_FOR_OTP
    else:
        await update.message.reply_text("❌ خطا در ارسال پیامک. لطفاً دقایقی دیگر تلاش کنید.")
        return ConversationHandler.END


async def verify_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text
    phone_number = context.user_data.get('pending_phone')
    
    if verify_otp_code(phone_number, code):
        await update.message.reply_text("⏳ در حال تکمیل ثبت‌نام...")
        
        is_bale = 'bale' in context.bot.base_url
        platform = 'bale' if is_bale else 'telegram'
            
        user_id = await register_or_get_user(
            phone_number, 
            str(update.message.chat_id), 
            context.user_data.get('pending_first'), 
            context.user_data.get('pending_last'),
            platform
        )
        context.user_data['user_id'] = user_id

        await update.message.reply_text("✅ ثبت‌نام با موفقیت انجام شد!")
        await show_main_menu(update, context)
        return ConversationHandler.END
    else:
        await update.message.reply_text("❌ کد وارد شده اشتباه است یا منقضی شده. لطفا مجددا دقت کنید:")
        return WAITING_FOR_OTP


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("مشاهده فروشگاه 💎"), KeyboardButton("جستجوی محصول 🔍")],
        [KeyboardButton("سبد خرید 🛒"), KeyboardButton("نمایش قیمت لحظه ای 💰")],
        [KeyboardButton("محاسبه‌گر طلا 🧮"), KeyboardButton("پشتیبانی 🎧")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    message = update.message if update.message else update.callback_query.message
    await message.reply_text("لطفاً یک گزینه را انتخاب کنید:", reply_markup=reply_markup)


# ----------------------------------------------------
# تابع ارتباط با دیتابیس برای جستجوی نام محصول
# ----------------------------------------------------
@sync_to_async
def search_products_by_name(query, limit=5):
    # کلمه icontains باعث می‌شود در تمام بخشی از عنوان جستجو کند
    qs = Product.objects.filter(is_active=True, title__icontains=query).order_by('-created_at')[:limit]
    return list(qs)


# ----------------------------------------------------
# هندلرهای مربوط به روال جستجو در ربات
# ----------------------------------------------------
async def start_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[KeyboardButton("بازگشت 🔙")]]
    await update.message.reply_text(
        "🔍 **جستجوی محصول**\n\nلطفاً کلمه‌ای از نام محصول مورد نظر خود را وارد کنید:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        parse_mode="Markdown"
    )
    return SEARCH_MODE

async def process_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text
    chat_id = update.message.chat_id
    
    await update.message.reply_text(f"⏳ در حال جستجو برای «{query}»...")
    
    products = await search_products_by_name(query)
    
    if not products:
        await update.message.reply_text(
            "❌ متأسفانه محصولی با این نام یافت نشد.\nمی‌توانید کلمه دیگری را جستجو کنید یا برای خروج دکمه «بازگشت 🔙» را بزنید."
        )
        return SEARCH_MODE

    current_gold_price = cache.get('live_gold_18k') or 0

    for p in products:
        final_price = p.calculate_live_price(current_gold_price)
        text = f"💎 **{p.title}**\n\n📝 توضیحات: {p.description}\n⚖️ وزن: {p.weight} گرم\n💰 قیمت لحظه‌ای: {final_price:,} تومان\n"
        
        keyboard = [[InlineKeyboardButton("افزودن به سبد خرید 🛒", callback_data=f"add_cart_{p.id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if p.image and hasattr(p.image, 'path') and os.path.exists(p.image.path):
            with open(p.image.path, 'rb') as photo_file:
                await context.bot.send_photo(
                    chat_id=chat_id, 
                    photo=photo_file, 
                    caption=text, 
                    reply_markup=reply_markup, 
                    parse_mode="Markdown"
                )
        else:
            await context.bot.send_message(
                chat_id=chat_id, 
                text=text, 
                reply_markup=reply_markup, 
                parse_mode="Markdown"
            )

    await update.message.reply_text(
        "✅ نتایج جستجو نمایش داده شد.\nبرای جستجوی مجدد کلمه جدیدی بفرستید، و یا برای بازگشت به منوی اصلی «بازگشت 🔙» را بزنید."
    )
    return SEARCH_MODE

async def cancel_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("جستجو لغو شد.")
    await show_main_menu(update, context)
    return ConversationHandler.END



async def view_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = context.user_data.get('user_id')
    if not user_id:
        await update.message.reply_text("لطفاً ابتدا احراز هویت کنید. دستور /start را بزنید.")
        return

    cart_data = await get_cart_details(user_id)
    if not cart_data or not cart_data['items']:
        await update.message.reply_text("سبد خرید شما خالی است 🛒")
        return

    text = "🧾 **پیش فاکتور شما:**\n\n"
    keyboard = []
    for idx, item in enumerate(cart_data['items'], 1):
        p_type = item['product_type']
        text += f"*{idx}. {item['title']}*\n"
        if p_type == 'ornamental':
            text += f"▫️ طلای خام: {int(item['raw_gold_value']):,} ت\n"
            text += f"▫️️ اجرت: {int(item['wage']):,} ت\n"
            text += f"▫️ سود: {int(item['profit_value']):,} ت\n"
            text += f"▫ مالیات: {int(item['tax_value']):,} ت\n"
            keyboard.append([InlineKeyboardButton(f"🔴 حذف {item['title']} 🔴", callback_data=f"del_item_{item['id']}")])
        elif p_type == 'parsian':
            text += f"▫️ ارزش طلا: {int(item['raw_gold_value']):,} ت\n"
            text += f"▫️ سود: {int(item['profit_value']):,} ت\n"
            text += f"▫️ بسته‌بندی/صدور: {int(item['constant_fee']):,} ت\n"
            keyboard.append([InlineKeyboardButton(f"🔴 حذف {item['title']} 🔴", callback_data=f"del_item_{item['id']}")])
        text += f"✅ **قیمت نهایی:** {item['final_price']:,} تومان\n➖➖➖➖➖➖➖\n"
    
    text += f"💳 **مبلغ کل قابل پرداخت:** {cart_data['total_price']:,} تومان\n"
    
    keyboard.append([InlineKeyboardButton("🗑 خالی کردن کل سبد خرید 🗑", callback_data="empty_cart")])
    keyboard.append([InlineKeyboardButton("💳 تسویه حساب و پرداخت 💳", callback_data="process_checkout")])
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

@sync_to_async
def remove_cart_item_db(item_id, user_id):
    CartItem.objects.filter(id=item_id, cart__user_id=user_id, cart__is_paid=False).delete()


@sync_to_async
def empty_cart_db(user_id):
    Cart.objects.filter(user_id=user_id, is_paid=False).delete()


async def delete_item_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    item_id = query.data.replace('del_item_', '')
    user_id = context.user_data.get('user_id')
    
    await remove_cart_item_db(item_id, user_id)
    await query.answer("❌ محصول از سبد حذف شد", show_alert=True)
    await query.message.delete()
    await view_cart(update, context) # نمایش مجدد سبد

async def empty_cart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = context.user_data.get('user_id')
    
    await empty_cart_db(user_id)
    await query.answer("🗑 سبد خرید خالی شد", show_alert=True)
    await query.message.delete()



async def process_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = context.user_data.get('user_id')
    
    current_gold_price = cache.get('live_gold_18k')
    if not current_gold_price:
        await query.edit_message_text("❌ سیستم در حال بروزرسانی قیمت‌های بازار است. لطفاً چند دقیقه دیگر تلاش کنید.")
        return

    await query.edit_message_text("⏳ در حال صدور فاکتور و اتصال به درگاه پرداخت...")
    success, result, order_id = await checkout_cart(user_id, current_gold_price)

    if success:
        keyboard = [[InlineKeyboardButton("رفتن به درگاه پرداخت 🔗", url=result)]]
        text = f"✅ فاکتور با موفقیت صادر شد.\nشماره سفارش: `{order_id}`\n\nبرای پرداخت روی دکمه زیر کلیک کنید."
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        await query.edit_message_text(result)


async def fetch_and_send_products(chat_id: int, page: int, context: ContextTypes.DEFAULT_TYPE):
    products, has_prev, has_next = await get_products_page(page)

    if not products:
        await context.bot.send_message(chat_id, "هیچ محصولی یافت نشد.")
        return

    # دریافت قیمت زنده برای محاسبه داینامیک
    current_gold_price = cache.get('live_gold_18k') or 0

    for p in products:
        # محاسبه قیمت لحظه‌ای برای نمایش به کاربر
        final_price = p.calculate_live_price(current_gold_price)
        
        text = f"💎 **{p.title}**\n\n📝 توضیحات: {p.description}\n⚖️ وزن: {p.weight} گرم\n💰 قیمت لحظه‌ای: {final_price:,} تومان\n"
        
        keyboard = [[InlineKeyboardButton("🟢 افزودن به سبد خرید 🟢", callback_data=f"add_cart_{p.id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # ساختار بهینه و ایمن برای جلوگیری از ارسال پیام تکراری
        if p.image and hasattr(p.image, 'path') and os.path.exists(p.image.path):
            with open(p.image.path, 'rb') as photo_file:
                await context.bot.send_photo(
                    chat_id=chat_id, 
                    photo=photo_file, 
                    caption=text, 
                    reply_markup=reply_markup, 
                    parse_mode="Markdown"
                )
        else:
            await context.bot.send_message(
                chat_id=chat_id, 
                text=text, 
                reply_markup=reply_markup, 
                parse_mode="Markdown"
            )
    nav_buttons = []
    if has_prev: nav_buttons.append(InlineKeyboardButton("◀️ قبلی", callback_data=f"page_{page-1}"))
    nav_buttons.append(InlineKeyboardButton(f"صفحه {page}", callback_data="ignore"))
    if has_next: nav_buttons.append(InlineKeyboardButton("بعدی ▶️", callback_data=f"page_{page+1}"))

    if len(nav_buttons) > 1:
        await context.bot.send_message(chat_id=chat_id, text="🔽 صفحات فروشگاه:", reply_markup=InlineKeyboardMarkup([nav_buttons]))

async def view_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ در حال دریافت جدیدترین کارهای گالری...")
    await fetch_and_send_products(update.message.chat_id, 1, context)

async def change_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "ignore": return
    
    page_number = int(query.data.split('_')[1])
    
    # پاک کردن پیام حاوی دکمه‌های صفحه‌بندی قبلی تا چت شلوغ نشود
    try:
        await query.message.delete()
    except Exception:
        pass
        
    # نمایش پیام انتظار به کاربر
    wait_msg = await context.bot.send_message(
        chat_id=query.message.chat_id, 
        text=f"⏳ در حال بارگذاری ۵ محصول بعدی (صفحه {page_number})..."
    )
    
    # دریافت و ارسال ۵ محصول جدید
    await fetch_and_send_products(query.message.chat_id, page_number, context)
    
    # پاک کردن پیام انتظار پس از اتمام ارسال
    try:
        await wait_msg.delete()
    except Exception:
        pass

async def add_to_cart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    product_id = query.data.replace('add_cart_', '').strip()
    user_id = context.user_data.get('user_id')
    
    if not user_id:
        await query.answer("❌ لطفاً ابتدا شماره تماس خود را در ربات ثبت کنید.", show_alert=True)
        return

    current_gold_price = cache.get('live_gold_18k')
    if not current_gold_price:
        await query.answer("❌ سیستم در حال بروزرسانی قیمت‌های بازار است. لطفاً چند دقیقه دیگر تلاش کنید.", show_alert=True)
        return

    success, msg = await add_product_to_cart(user_id, product_id, current_gold_price)
    await query.answer(msg, show_alert=True)

def format_price_line(title, price, change_percent):
    sign = "▲" if change_percent > 0 else ("▼" if change_percent < 0 else "—")
    return f"🪙 {title}: {price:,} تومان ({sign} {abs(change_percent)}%)"

@sync_to_async
def get_live_rates_text():
    current = cache.get('live_gold_18k', 0)
    change = cache.get('gold_change_percent', 0.0)
    ounce = cache.get('live_gold_ounce', 0.0)
    mazaneh = cache.get('live_mazaneh', 0)
    
    line_new = format_price_line("سکه امامی", cache.get('coin_new', 0), cache.get('change_coin_new', 0.0))    
    line_old = format_price_line("بهار آزادی", cache.get('coin_old', 0), cache.get('change_coin_old', 0.0))
    line_half = format_price_line("نیم سکه", cache.get('coin_half', 0), cache.get('change_coin_half', 0.0))
    line_quarter = format_price_line("ربع سکه", cache.get('coin_quarter', 0), cache.get('change_coin_quarter', 0.0))
    line_gram = format_price_line("سکه گرمی", cache.get('coin_gram', 0), cache.get('change_coin_gram', 0.0))
    
    sign = "▲" if change > 0 else ("▼" if change < 0 else "—")
    current_time = datetime.datetime.now().strftime('%H:%M:%S')
    
    text = (
        "📊 **نرخ لحظه‌ای بازار**\n\n"
        f"🌍 انس جهانی طلا: {ounce:,} دلار\n"
        f"⚖️ مظنه تهران: {mazaneh:,} تومان\n"
        f"💰 طلای ۱۸ عیار: {current:,} تومان\n"
        f"📈 نوسان طلا: {sign} {abs(change)}%\n\n"
        "🟡 **نرخ انواع سکه:**\n"
        f"{line_new}\n{line_old}\n{line_half}\n{line_quarter}\n{line_gram}\n\n"
        f"⏱ آخرین بروزرسانی: `{current_time}`"
    )
    return text

async def show_live_rates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = await get_live_rates_text()
    keyboard = [[InlineKeyboardButton("بروزرسانی 🔄", callback_data="refresh_rates")]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def refresh_live_rates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("در حال دریافت قیمت‌های جدید... ⏳")
    text = await get_live_rates_text()
    keyboard = [[InlineKeyboardButton("بروزرسانی 🔄", callback_data="refresh_rates")]]
    try:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    except Exception:
        pass

async def start_calculator(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🧮 **به محاسبه‌گر آنلاین طلا خوش آمدید!**\n\nلطفاً **وزن طلا** را به گرم وارد کنید (مثلاً 2.5):",
        reply_markup=calc_cancel_kb, parse_mode="Markdown"
    )
    return CALC_WEIGHT

async def calc_get_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "انصراف ❌":
        await update.message.reply_text("عملیات لغو شد.")
        await show_main_menu(update, context)
        return ConversationHandler.END
    try:
        context.user_data['calc_weight'] = float(text)
        await update.message.reply_text("✅ وزن ثبت شد.\n\nحالا **درصد اجرت** را وارد کنید (مثلاً 15):")
        return CALC_WAGE
    except ValueError:
        await update.message.reply_text("❌ لطفاً فقط یک عدد معتبر برای وزن وارد کنید:")
        return CALC_WEIGHT

async def calc_get_wage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "انصراف ❌":
        await update.message.reply_text("عملیات لغو شد.")
        await show_main_menu(update, context)
        return ConversationHandler.END
    try:
        context.user_data['calc_wage'] = float(text)
        await update.message.reply_text("✅ اجرت ثبت شد.\n\nحالا **درصد سود فروشنده** را وارد کنید (مثلاً 7):")
        return CALC_PROFIT
    except ValueError:
        await update.message.reply_text("❌ لطفاً فقط یک عدد معتبر برای اجرت وارد کنید:")
        return CALC_WAGE

async def calc_get_profit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "انصراف ❌":
        await update.message.reply_text("عملیات لغو شد.")
        await show_main_menu(update, context)
        return ConversationHandler.END
    try:
        context.user_data['calc_profit'] = float(text)
        await update.message.reply_text("✅ درصد سود ثبت شد.\n\nدر مرحله آخر، **درصد مالیات** را وارد کنید (مثلاً 10):")
        return CALC_TAX
    except ValueError:
        await update.message.reply_text("❌ لطفاً فقط عدد وارد کنید:")
        return CALC_PROFIT


async def calc_get_tax(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "انصراف ❌":
        await update.message.reply_text("عملیات لغو شد.")
        await show_main_menu(update, context)
        return ConversationHandler.END
        
    try:
        tax_percent = float(text)
        weight = context.user_data['calc_weight']
        wage_percent = context.user_data['calc_wage']
        profit_percent = context.user_data['calc_profit']

        live_18k_price = cache.get('live_gold_18k', 0)
        if live_18k_price == 0:
            await update.message.reply_text("❌ دریافت قیمت لحظه‌ای با مشکل مواجه شد. لطفاً بعداً تلاش کنید.")
            await show_main_menu(update, context)
            return ConversationHandler.END

        # پیاده‌سازی فرمول دقیق
        raw_gold_value = weight * live_18k_price
        wage_amount = raw_gold_value * (wage_percent / 100)
        profit_amount = (raw_gold_value + wage_amount) * (profit_percent / 100)
        tax_amount = (profit_amount + wage_amount) * (tax_percent / 100)
        
        final_price = int(raw_gold_value + wage_amount + profit_amount + tax_amount)

        result_text = (
            "🧾 **نتیجه محاسبه آنلاین شما:**\n\n"
            f"⚖️ وزن وارد شده: {weight} گرم\n"
            f"💰 نرخ روز طلا: {live_18k_price:,} تومان\n"
            f"▫️ ارزش طلای خام: {int(raw_gold_value):,} تومان\n"
            f"▫️ اجرت ساخت ({wage_percent}٪): {int(wage_amount):,} تومان\n"
            f"▫️ سود فروش ({profit_percent}٪): {int(profit_amount):,} تومان\n"
            f"▫️ مالیات ({tax_percent}٪): {int(tax_amount):,} تومان\n"
            "➖➖➖➖➖➖➖\n"
            f"✅ **مبلغ نهایی: {final_price:,} تومان**"
        )
        await update.message.reply_text(result_text, parse_mode="Markdown")
        await show_main_menu(update, context)
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text("❌ لطفاً فقط عدد وارد کنید:")
        return CALC_TAX


async def enter_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[KeyboardButton("بازگشت 🔙")]]
    await update.message.reply_text(
        "🎧 شما به بخش پشتیبانی متصل شدید.\nمتن، عکس یا ویس خود را ارسال کنید تا به مدیریت ارجاع داده شود.\nبرای خروج، دکمه «بازگشت 🔙» را بزنید.",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return SUPPORT_MODE


@sync_to_async
def get_store_admin_id(bot_token):
    store_id = get_current_store()
    from stores.models import Store
    store = Store.objects.filter(id=store_id).first()
    
    if store:
        if bot_token == store.telegram_bot_token:
            return store.admin_chat_id_telegram
        elif bot_token == store.bale_bot_token:
            return store.admin_chat_id_bale
            
    return ADMIN_CHAT_ID


async def send_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    admin_chat_id = await get_store_admin_id(context.bot.token)
    
    if not admin_chat_id:
        await update.message.reply_text("❌ پشتیبانی برای این فروشگاه فعال نشده است.")
        return SUPPORT_MODE
    
    await update.message.copy(chat_id=admin_chat_id)
    await context.bot.send_message(
        chat_id=admin_chat_id,
        text=f"👤 فرستنده: {user.first_name}\n💬 آیدی عددی: {user.id}\nجهت پاسخ دادن، روی همین پیام ریپلای کنید."
    )
    await update.message.reply_text("✅ پیام شما دریافت شد. مدیریت فروشگاه به زودی پاسخ خواهد داد.")
    return SUPPORT_MODE

async def exit_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("شما از بخش پشتیبانی خارج شدید.")
    await show_main_menu(update, context) 
    return ConversationHandler.END

async def admin_reply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_chat_id = await get_store_admin_id(context.bot.token)
    if str(update.message.chat_id) == str(admin_chat_id) and update.message.reply_to_message:
        original_text = update.message.reply_to_message.text
        if original_text and "آیدی عددی:" in original_text:
            match = re.search(r'آیدی عددی:\s*(\d+)', original_text)
            if match:
                user_chat_id = match.group(1)
                try:
                    await context.bot.send_message(chat_id=user_chat_id, text="🎧 پاسخ پشتیبانی گالری:\n")
                    await update.message.copy(chat_id=user_chat_id)
                    await update.message.reply_text("پاسخ شما با موفقیت برای مشتری ارسال شد ✅")
                except Exception as e:
                    await update.message.reply_text(f"خطا در ارسال پیام. ممکن است کاربر ربات را بلاک کرده باشد.\n{e}")