from rest_framework import status, views
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from products.models import Product
from .models import Cart, CartItem
from api.serializers import CartSerializer

class CartAPIView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart = Cart.objects.filter(user=request.user, is_paid=False).order_by('-created_at').first()
        if not cart or cart.is_expired:
            return Response({"detail": "سبد خرید فعال یا معتبری یافت نشد."}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = CartSerializer(cart)
        return Response(serializer.data)

def post(self, request):
        product_id = request.data.get('product_id')
        product = get_object_or_404(Product, id=product_id, is_active=True)

        # به جای get_or_create از این روش امن‌تر استفاده کنید تا سرور کرش نکند
        cart = Cart.objects.filter(user=request.user, is_paid=False).order_by('-created_at').first()
        
        if not cart:
            cart = Cart.objects.create(user=request.user, is_paid=False)

        if cart.is_expired:
            cart.refresh_expiration()

        current_gold_price = 4500000 

        if not cart.items.filter(product=product).exists():
            CartItem.objects.create(
                cart=cart,
                product=product,
                daily_gold_price=current_gold_price,
                wage_percent=15.0, 
                profit_percent=7.0,
                tax_percent=9.0
            )
            cart.refresh_expiration() 
            return Response({"detail": "محصول به سبد اضافه شد."}, status=status.HTTP_201_CREATED)

        return Response({"detail": "این محصول قبلاً در سبد شما موجود است."}, status=status.HTTP_400_BAD_REQUEST)