// static/admin/js/persian_datepicker_init.js
(function($) {
    $(document).ready(function() {
        // فعال‌سازی تقویم شمسی روی اینپوت‌های دارای کلاس مشخص
        kamaDatepicker('.jalali-date-input', {
            placeholder: 'انتخاب تاریخ شمسی',
            twodigit: true,
            closeAfterSelect: true,
            markToday: true
        });
    });
})(django.jQuery);