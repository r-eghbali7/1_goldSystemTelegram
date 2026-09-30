from rest_framework import viewsets
from .models import Product
from api.serializers import ProductSerializer
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.cache import cache


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


class LiveRatesAPIView(APIView):
    permission_classes = []
    authentication_classes = []

    def get(self, request):
        return Response({
            "gold_18k": cache.get('live_gold_18k', 0),
            "yesterday_gold_18k": cache.get('yesterday_gold_18k', 0),
            "change_percent": cache.get('gold_change_percent', 0.0),
            "ounce": cache.get('live_gold_ounce', 0.0),
            "mazaneh": cache.get('live_mazaneh', 0),
            
            # قیمت و درصد نوسان سکه‌ها
            "coin_old": cache.get('coin_old', 0),
            "change_coin_old": cache.get('change_coin_old', 0.0),
            
            "coin_new": cache.get('coin_new', 0),
            "change_coin_new": cache.get('change_coin_new', 0.0),
            
            "coin_half": cache.get('coin_half', 0),
            "change_coin_half": cache.get('change_coin_half', 0.0),
            
            "coin_quarter": cache.get('coin_quarter', 0),
            "change_coin_quarter": cache.get('change_coin_quarter', 0.0),
            
            "coin_gram": cache.get('coin_gram', 0),
            "change_coin_gram": cache.get('change_coin_gram', 0.0),
        })