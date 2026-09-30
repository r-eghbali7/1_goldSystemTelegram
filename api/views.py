from rest_framework import viewsets, status, views
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework.views import APIView
from telegram import Update, Bot
from telegram.ext import Application
from api.persistence import RedisTenantPersistence
from api.tasks import process_telegram_update_task
from stores.models import Store

from products.models import Product
from carts.models import Cart, CartItem
from orders.models import Order, OrderItem
from orders.services import generate_payment_link
from .serializers import ProductSerializer, CartSerializer
from .throttling import BotTokenThrottle, TelegramUserThrottle # 👈 اضافه شد

# 1. API محصولات (نمایش، صفحه‌بندی و فیلتر)
class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.filter(is_active=True).order_by('-created_at')
    serializer_class = ProductSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        category_id = self.request.query_params.get('category')
        max_price = self.request.query_params.get('max_price')
        
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        return queryset

# 2. API مدیریت سبد خرید
class CartAPIView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # دریافت سبد خرید فعال کاربر
        cart = Cart.objects.filter(user=request.user, is_paid=False).order_by('-created_at').first()
        if not cart or cart.is_expired:
            return Response({"detail": "سبد خرید فعال یا معتبری یافت نشد."}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = CartSerializer(cart)
        return Response(serializer.data)

    def post(self, request):
        # افزودن محصول به سبد خرید
        product_id = request.data.get('product_id')
        product = get_object_or_404(Product, id=product_id, is_active=True)
        
        # پیدا کردن سبد فعال یا ساخت سبد جدید
        cart, created = Cart.objects.get_or_create(
            user=request.user, 
            is_paid=False,
            defaults={'expires_at': Cart._meta.get_field('expires_at').default()}
        )
        
        # اگر سبد منقضی شده بود، تایمر آن را ریست می‌کنیم
        if cart.is_expired:
            cart.refresh_expiration()

        # TODO: در پروژه واقعی، قیمت روز طلا را از یک وب‌سرویس دریافت کنید
        current_gold_price = 4500000 # قیمت فرضی روز طلا
        
        # اضافه کردن آیتم به سبد (جلوگیری از تکراری بودن)
        if not cart.items.filter(product=product).exists():
            CartItem.objects.create(
                cart=cart,
                product=product,
                daily_gold_price=current_gold_price,
                wage_percent=15.0, # اجرت فرضی
                profit_percent=7.0,
                tax_percent=9.0
            )
            cart.refresh_expiration() # تمدید زمان سبد با هر افزودن جدید
            return Response({"detail": "محصول به سبد اضافه شد."}, status=status.HTTP_201_CREATED)
            
        return Response({"detail": "این محصول قبلاً در سبد شما موجود است."}, status=status.HTTP_400_BAD_REQUEST)

# 3. API تسویه حساب و تولید فاکتور (Checkout)
class CheckoutAPIView(views.APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        cart = Cart.objects.filter(user=request.user, is_paid=False).order_by('-created_at').first()
        
        if not cart or cart.is_expired or cart.items.count() == 0:
            return Response({"detail": "سبد خرید نامعتبر است."}, status=status.HTTP_400_BAD_REQUEST)

        # ساخت فاکتور نهایی (Order)
        order = Order.objects.create(
            user=request.user,
            total_amount=cart.total_cart_price
        )

        # انتقال آیتم‌ها از Cart به Order
        for item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=item.product,
                purchased_price=item.final_item_price,
                gold_weight=item.product.weight
            )

        # علامت‌گذاری سبد به عنوان پرداخت شده (یا حذف آن)
        cart.is_paid = True
        cart.save()

        # درخواست لینک پرداخت از زرین‌پال
        success, result = generate_payment_link(order.id)
        
        if success:
            return Response({"payment_url": result, "order_id": order.id}, status=status.HTTP_200_OK)
        else:
            return Response({"detail": result}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



# کش کردن اپلیکیشن‌های تلگرام برای سرعت بیشتر
bot_applications = {}

def get_bot_application(bot_token):
    if bot_token not in bot_applications:
        # ساختن نمونه اپلیکیشن برای ربات خاص
        application = Application.builder().token(bot_token).build()
        
        # هندلرهای خود را اینجا اضافه کنید (مثل کد قبلی خودتان)
        # application.add_handler(CommandHandler("start", start))
        # application.add_handler(CallbackQueryHandler(add_to_cart_callback, pattern=r'^add_cart_'))
        
        bot_applications[bot_token] = application
    return bot_applications[bot_token]


# کش کردن اپلیکیشن‌های تلگرام
bot_applications = {}

def get_bot_application(bot_token):
    if bot_token not in bot_applications:
        # واکشی فروشگاه برای گرفتن ID و ساخت پیشوند دیتابیس
        store = Store.objects.get(bot_token=bot_token, is_active=True)
        
        # معرفی Redis به عنوان منبع ذخیره وضعیت‌ها
        persistence = RedisTenantPersistence(store_id=store.id)
        
        application = (
            Application.builder()
            .token(bot_token)
            .persistence(persistence)
            .build()
        )
        
        # هندلرهای خود را اینجا اضافه کنید
        # application.add_handler(...)
        
        bot_applications[bot_token] = application
        
    return bot_applications[bot_token]


class TelegramWebhookView(APIView):
    permission_classes = []
    authentication_classes = []
    
    # 👈 اعمال محدودیت‌ها روی این ویو
    throttle_classes = [BotTokenThrottle, TelegramUserThrottle] 

    def post(self, request, bot_token, *args, **kwargs):
        # این کد فقط زمانی اجرا می‌شود که درخواست‌ها از سقف Throttling عبور نکرده باشند
        process_telegram_update_task.delay(bot_token, request.data)
        return Response({"status": "ok"}, status=status.HTTP_200_OK)





