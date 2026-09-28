from rest_framework import viewsets
from .models import Product
from api.serializers import ProductSerializer

class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.filter(is_active=True).order_by('-created_at')
    serializer_class = ProductSerializer
    
    def get_queryset(self):
        store_id = self.request.headers.get('X-Store-ID')
        queryset = Product.objects.filter(is_active=True, store_id=store_id).order_by('-created_at')        
        category_id = self.request.query_params.get('category')
        max_price = self.request.query_params.get('max_price')
        
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        return queryset