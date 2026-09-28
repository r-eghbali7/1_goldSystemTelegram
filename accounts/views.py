from django.db import IntegrityError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User

# ایمپورت مدل‌های فروشگاه برای اتصال کاربر به ربات هدف
from stores.models import Store, StoreCustomer

class TelegramDirectLoginView(APIView):
    # غیرفعال کردن کامل چک‌های امنیتی برای این یک مسیر خاص
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        phone_number = request.data.get('phone_number')
        chat_id = request.data.get('chat_id')
        store_id = request.data.get('store_id')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')

        if not phone_number:
            return Response({"detail": "شماره موبایل الزامی است."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # ۱. جستجو یا ساخت امن کاربر در دیتابیس مرکزی (هویت یکپارچه)
            user, created = User.objects.get_or_create(phone_number=phone_number)
            
            # آپدیت کردن اطلاعات شخصی کاربر
            if chat_id:
                user.chat_id = chat_id
            if first_name:
                user.first_name = first_name
            if last_name:
                user.last_name = last_name
                
            user.is_verified = True
            user.save()

            # ۲. اتصال کاربر به فروشگاه فعلی (تشکیل پروفایل مشتری برای این ربات)
            if store_id:
                store = Store.objects.get(id=store_id)
                StoreCustomer.objects.get_or_create(store=store, user=user)

        except Store.DoesNotExist:
            return Response({"detail": "فروشگاهی با این شناسه یافت نشد."}, status=status.HTTP_404_NOT_FOUND)
        except IntegrityError:
            # این خطا زمانی رخ می‌دهد که یک کاربر بخواهد با یک اکانت تلگرام، دو شماره مختلف را ثبت کند
            return Response(
                {"detail": "این آیدی تلگرام قبلاً با یک شماره موبایل دیگر در سیستم ثبت شده است."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response({"detail": f"خطای سرور: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # ۳. صدور توکن و تزریق آیدی فروشگاه به داخل توکن برای امنیت درخواست‌های بعدی
        refresh = RefreshToken.for_user(user)
        if store_id:
            refresh['store_id'] = str(store_id)

        return Response({
            "detail": "ورود موفقیت‌آمیز بود.",
            "tokens": {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            },
            "user_id": user.id,
            "store_id": store_id
        }, status=status.HTTP_200_OK)