from rest_framework import serializers
from products.models import Product, Category
from carts.models import Cart, CartItem
from orders.models import Order

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']

class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    
    class Meta:
        model = Product
        fields = ['id', 'title', 'description', 'price', 'weight', 'image', 'category', 'is_active']

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