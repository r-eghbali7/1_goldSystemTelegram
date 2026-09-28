from rest_framework.throttling import SimpleRateThrottle

class BotTokenThrottle(SimpleRateThrottle):
    """
    محدودیت کلی برای هر ربات (محافظت از منابع سرور در برابر حملات گسترده)
    """
    scope = 'bot_webhook'

    def get_cache_key(self, request, view):
        bot_token = view.kwargs.get('bot_token')
        if not bot_token:
            return None
            
        return self.cache_format % {
            'scope': self.scope,
            'ident': bot_token
        }

class TelegramUserThrottle(SimpleRateThrottle):
    """
    محدودیت برای هر کاربر تلگرام (جلوگیری از اسپم شدن ربات توسط یک شخص)
    """
    scope = 'telegram_user'

    def get_cache_key(self, request, view):
        bot_token = view.kwargs.get('bot_token')
        
        # استخراج ایمن آیدی کاربر تلگرام از دیتای JSON
        try:
            # بررسی پیام‌های متنی
            user_id = request.data.get('message', {}).get('from', {}).get('id')
            if not user_id:
                # بررسی کلیک روی دکمه‌های شیشه‌ای (Inline Keyboards)
                user_id = request.data.get('callback_query', {}).get('from', {}).get('id')
        except Exception:
            user_id = None

        if not bot_token or not user_id:
            return None

        # ترکیب توکن ربات و آیدی کاربر تا محدودیت فقط برای همین فروشگاه اعمال شود
        return self.cache_format % {
            'scope': self.scope,
            'ident': f"{bot_token}_{user_id}"
        }