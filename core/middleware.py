# core/middleware.py
from django.utils.deprecation import MiddlewareMixin
from rest_framework_simplejwt.tokens import AccessToken
from .tenant import set_current_store

class TenantMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # 1. خواندن هدر Authorization
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            try:
                # 2. دیکود کردن توکن بدون زدن کوئری به دیتابیس
                decoded_token = AccessToken(token)
                store_id = decoded_token.get('store_id')
                
                # 3. ذخیره در کانتکست در صورت وجود
                if store_id:
                    set_current_store(store_id)
            except Exception:
                # اگر توکن نامعتبر بود، اجازه می‌دهیم خود DRF در لایه View ارور 401 بدهد
                pass