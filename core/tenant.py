# core/tenant.py
from contextvars import ContextVar

# این متغیر در هر ریکوئست ایزوله است و با ریکوئست‌های دیگر تداخل پیدا نمی‌کند
_current_store_id = ContextVar('current_store_id', default=None)

def set_current_store(store_id):
    """تنظیم آیدی فروشگاه برای ریکوئست فعلی"""
    _current_store_id.set(store_id)

def get_current_store():
    """دریافت آیدی فروشگاه در ریکوئست فعلی"""
    return _current_store_id.get()