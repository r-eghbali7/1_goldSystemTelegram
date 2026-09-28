from rest_framework import serializers
from core.utils import to_jalali_format, to_persian_digits
from products.models import Product, Category
from carts.models import Cart, CartItem
from orders.models import Order

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']

class ProductSerializer(serializers.ModelSerializer):
    price_fa = serializers.SerializerMethodField()
    created_at_jalali = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'title', 'price', 'price_fa', 'weight', 'created_at_jalali', 'image']

    def get_price_fa(self, obj):
        return f"{to_persian_digits(obj.price)} تومان"

    def get_created_at_jalali(self, obj):
        return to_jalali_format(obj.created_at, include_time=False)


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    final_price = serializers.ReadOnlyField(source='final_item_price')
    
    class Meta:
        model = CartItem
        fields = ['id', 'product', 'daily_gold_price', 'wage_percent', 'tax_percent', 'final_price']

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.ReadOnlyField(source='total_cart_price')
    is_expired = serializers.ReadOnlyField()

    class Meta:
        model = Cart
        fields = ['id', 'user', 'items', 'total_price', 'is_expired', 'expires_at', 'is_paid']