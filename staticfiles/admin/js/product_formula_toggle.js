// core/static/admin/js/product_formula_toggle.js
document.addEventListener("DOMContentLoaded", function() {
    // پیدا کردن منوی کشویی نوع محصول
    const typeSelect = document.querySelector("#id_product_type");
    
    // پیدا کردن گروه‌های فیلد (Fieldsets)
    const ornamentalGroup = document.querySelector(".ornamental-group");
    const parsianGroup = document.querySelector(".parsian-group");

    function toggleFields() {
        if (!typeSelect) return;
        
        const selectedType = typeSelect.value;
        
        if (selectedType === "ornamental") {
            // نمایش فیلدهای طلای زینتی و مخفی کردن سکه
            if (ornamentalGroup) ornamentalGroup.style.display = "block";
            if (parsianGroup) parsianGroup.style.display = "none";
        } 
        else if (selectedType === "parsian") {
            // نمایش فیلدهای سکه پارسیان و مخفی کردن طلای زینتی
            if (ornamentalGroup) ornamentalGroup.style.display = "none";
            if (parsianGroup) parsianGroup.style.display = "block";
        }
    }

    if (typeSelect) {
        // اجرای تابع هنگام لود صفحه
        toggleFields();
        
        // اجرای تابع هر بار که منوی کشویی تغییر می‌کند
        typeSelect.addEventListener("change", toggleFields);
    }
});