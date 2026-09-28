from telegram.ext import BasePersistence
from django.core.cache import cache

class RedisTenantPersistence(BasePersistence):
    """
    ذخیره‌سازی وضعیت‌های ConversationHandler و User Data هر ربات به صورت ایزوله در Redis
    """
    def __init__(self, store_id):
        super().__init__()
        # یک پیشوند یکتا برای هر فروشگاه تا اطلاعات ربات‌ها تداخل پیدا نکند
        self.prefix = f"tg_store_{store_id}:"

    async def get_conversations(self, name: str) -> dict:
        data = await cache.aget(f"{self.prefix}conv:{name}")
        return data if data else {}

    async def update_conversation(self, name: str, key: tuple, new_state: object) -> None:
        cache_key = f"{self.prefix}conv:{name}"
        # واکشی وضعیت‌های قبلی، آپدیت و ذخیره مجدد
        conversations = await cache.aget(cache_key) or {}
        conversations[key] = new_state
        # تایم‌اوت را روی یک هفته یا بدون انقضا تنظیم کنید
        await cache.aset(cache_key, conversations, timeout=86400 * 7) 

    async def get_user_data(self) -> dict:
        data = await cache.aget(f"{self.prefix}user_data")
        return data if data else {}

    async def update_user_data(self, user_id: int, data: dict) -> None:
        cache_key = f"{self.prefix}user_data"
        user_data = await cache.aget(cache_key) or {}
        user_data[user_id] = data
        await cache.aset(cache_key, user_data, timeout=86400 * 7)

    async def get_chat_data(self) -> dict:
        data = await cache.aget(f"{self.prefix}chat_data")
        return data if data else {}

    async def update_chat_data(self, chat_id: int, data: dict) -> None:
        cache_key = f"{self.prefix}chat_data"
        chat_data = await cache.aget(cache_key) or {}
        chat_data[chat_id] = data
        await cache.aset(cache_key, chat_data, timeout=86400 * 7)

    async def get_bot_data(self) -> dict:
        data = await cache.aget(f"{self.prefix}bot_data")
        return data if data else {}

    async def update_bot_data(self, data: dict) -> None:
        await cache.aset(f"{self.prefix}bot_data", data, timeout=86400 * 7)

    # پیاده‌سازی متدهای الزامی که در ساختار ساده استفاده نمی‌شوند
    async def get_callback_data(self) -> dict: return {}
    async def update_callback_data(self, data: dict) -> None: pass
    async def drop_chat_data(self, chat_id: int) -> None: pass
    async def drop_user_data(self, user_id: int) -> None: pass
    async def refresh_user_data(self, user_id: int, user_data: dict) -> None: pass
    async def refresh_chat_data(self, chat_id: int, chat_data: dict) -> None: pass
    async def refresh_bot_data(self, bot_data: dict) -> None: pass
    async def flush(self) -> None: pass