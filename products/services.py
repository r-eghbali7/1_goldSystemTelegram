from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import Product

def get_products_for_bot(page_number=1, per_page=5, category_uuid=None, max_price=None):
    queryset = Product.objects.filter(is_active=True)
    
    if category_uuid:
        # جستجو بر اساس UUID امن
        queryset = queryset.filter(category_id=category_uuid)
    if max_price:
        queryset = queryset.filter(price__lte=max_price)
        
    queryset = queryset.order_by('-created_at')
    paginator = Paginator(queryset, per_page)
    
    try:
        page = paginator.page(page_number)
    except PageNotAnInteger:
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)
        
    return {
        'items': page.object_list,
        'has_next': page.has_next(),
        'has_previous': page.has_previous(),
        'total_pages': paginator.num_pages,
        'current_page': page.number
    }