# core/utils.py
import jdatetime

def to_jalali_format(datetime_obj, include_time=True):
    """تبدیل تاریخ میلادی به شمسی"""
    if not datetime_obj:
        return ""
    
    # تبدیل به تاریخ شمسی
    j_dt = jdatetime.datetime.fromgregorian(datetime=datetime_obj)
    
    if include_time:
        formatted = j_dt.strftime('%Y/%m/%d ساعت %H:%M')
    else:
        formatted = j_dt.strftime('%Y/%m/%d')
        
    return to_persian_digits(formatted)

def to_persian_digits(value):
    """تبدیل تمام اعداد انگلیسی و کاما به ارقام فارسی"""
    if value is None:
        return ""
    
    # اگر ورودی عدد باشد، ابتدا آن را با کاما فرمت می‌کنیم
    if isinstance(value, (int, float)):
        str_val = f"{value:,}"
    else:
        str_val = str(value)
        
    # جدول نگاشت ارقام انگلیسی به فارسی
    english_to_persian = str.maketrans('0123456789,', '۰۱۲۳۴۵۶۷۸۹،')
    return str_val.translate(english_to_persian)