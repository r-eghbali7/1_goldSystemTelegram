from django.db import IntegrityError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User

class TelegramDirectLoginView(APIView):
    # غیرفعال کردن کامل چک‌های امنیتی برای این یک مسیر خاص
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        phone_number = request.data.get('phone_number')
        chat_id = request.data.get('chat_id')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')

        if not phone_number:
            return Response({"detail": "شماره موبایل الزامی است."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # جستجو یا ساخت امن کاربر
            user, created = User.objects.get_or_create(phone_number=phone_number)

            # آپدیت کردن اطلاعات
            if chat_id:
                user.chat_id = chat_id
            if first_name:
                user.first_name = first_name
            if last_name:
                user.last_name = last_name
                
            user.is_verified = True
            user.save()
            
        except IntegrityError:
            # این خطا زمانی رخ می‌دهد که یک کاربر بخواهد با یک اکانت تلگرام، دو شماره مختلف را ثبت کند
            return Response(
                {"detail": "این آیدی تلگرام قبلاً با یک شماره موبایل دیگر در سیستم ثبت شده است."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response({"detail": f"خطای سرور: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        refresh = RefreshToken.for_user(user)

        return Response({
            "detail": "ورود موفقیت‌آمیز بود.",
            "tokens": {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            },
            "user_id": user.id
        }, status=status.HTTP_200_OK)