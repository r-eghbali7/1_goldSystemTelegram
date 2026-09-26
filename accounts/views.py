from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
import re
from .services import verify_otp_code,send_otp_code # تابعی که در مراحل قبل برای کاوه‌نگار نوشتیم
from .models import User




class VerifyOTPAndLoginView(APIView):
    """
    دریافت شماره موبایل و کد پیامک شده، و صدور توکن JWT
    """
    def post(self, request):
        phone_number = request.data.get('phone_number')
        code = request.data.get('code')
        chat_id = request.data.get('chat_id') # گرفتن آیدی تلگرام هنگام لاگین

        if not phone_number or not code:
            return Response({"detail": "شماره موبایل و کد الزامی است."}, status=status.HTTP_400_BAD_REQUEST)

        # بررسی صحت کد در Redis
        if verify_otp_code(phone_number, code):
            # کاربر را پیدا می‌کنیم یا می‌سازیم
            user, created = User.objects.get_or_create(phone_number=phone_number)
            
            # آپدیت کردن chat_id تلگرام کاربر
            if chat_id:
                user.chat_id = chat_id
            
            user.is_verified = True
            user.save()

            # صدور توکن‌های JWT
            refresh = RefreshToken.for_user(user)

            return Response({
                "detail": "ورود موفقیت‌آمیز بود.",
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
                "user_id": user.id
            }, status=status.HTTP_200_OK)
        else:
            return Response({"detail": "کد وارد شده اشتباه است یا منقضی شده."}, status=status.HTTP_400_BAD_REQUEST)



class SendOTPView(APIView):
    """
    دریافت شماره موبایل و درخواست ارسال پیامک کد تایید (OTP)
    """
    # نیازی به توکن ندارد (چون کاربر هنوز لاگین نکرده)
    permission_classes = [] 

    def post(self, request):
        phone_number = request.data.get('phone_number')

        # اعتبارسنجی اولیه شماره موبایل (فقط فرمت ایران)
        if not phone_number or not re.match(r'^09\d{9}$', str(phone_number)):
            return Response(
                {"detail": "شماره موبایل نامعتبر است. شماره باید با 09 شروع شده و 11 رقم باشد."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # فراخوانی سرویس ارسال پیامک (که شامل Rate Limiting هم هست)
        success, message = send_otp_code(phone_number)

        if success:
            # ارسال موفقیت‌آمیز کد
            return Response({"detail": message}, status=status.HTTP_200_OK)
        else:
            # اگر کاربر خیلی زود درخواست مجدد داده باشد یا کاوه‌نگار قطعی داشته باشد
            # استفاده از کد 429 به فرانت‌اند/ربات می‌فهماند که باید به کاربر تایمر نشان دهد
            return Response({"detail": message}, status=status.HTTP_429_TOO_MANY_REQUESTS)



        