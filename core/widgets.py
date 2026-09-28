# core/widgets.py
from django import forms

class PersianAdminDateWidget(forms.TextInput):
    def __init__(self, attrs=None):
        default_attrs = {'class': 'jalali-date-input', 'autocomplete': 'off'}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)

    class Media:
        # لود کردن فایل‌های CSS و JS تقویم شمسی از طریق CDN
        css = {
            'all': ('https://cdn.jsdelivr.net/npm/kamadatepicker@1.6.0/dist/kamadatepicker.min.css',)
        }
        js = (
            'https://cdn.jsdelivr.net/npm/jquery@3.6.0/dist/jquery.min.js',
            'https://cdn.jsdelivr.net/npm/kamadatepicker@1.6.0/dist/kamadatepicker.min.js',
            # اسکریپت اتصال تقویم به فیلدهای ادمین
            'admin/js/persian_datepicker_init.js', 
        )