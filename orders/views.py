import requests
import json
from django.http import HttpResponse
from decouple import config
from rest_framework import status, views
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction

from .models import Order, OrderItem
from carts.models import Cart
from .services import generate_payment_link
from .tasks import send_telegram_receipt

MERCHANT_ID = config('ZARINPAL_MERCHANT_ID')
ZARINPAL_VERIFY_URL = 'https://api.zarinpal.com/pg/v4/payment/verify.json'

class CheckoutAPIView(views.APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        cart = Cart.objects.filter(user=request.user, is_paid=False).order_by('-created_at').first()
        
        if not cart or cart.is_expired or cart.items.count() == 0:
            return Response({"detail": "سبد خرید نامعتبر است."}, status=status.HTTP_400_BAD_REQUEST)

        order = Order.objects.create(
            user=request.user,
            total_amount=cart.total_cart_price
        )

        for item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=item.product,
                purchased_price=item.final_item_price,
                gold_weight=item.product.weight
            )

        cart.is_paid = True
        cart.save()

        success, result = generate_payment_link(order.id)
        
        if success:
            return Response({"payment_url": result, "order_id": order.id}, status=status.HTTP_200_OK)
        else:
            return Response({"detail": result}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def zarinpal_callback_view(request):
    # [کدهای قبلی zarinpal_callback_view را دقیقاً اینجا قرار دهید]
    authority = request.GET.get('Authority')
    status_payment = request.GET.get('Status')

    if status_payment != 'OK':
        Order.objects.filter(authority=authority).update(status='failed')
        return HttpResponse("پرداخت لغو شد یا ناموفق بود.")

    try:
        order = Order.objects.get(authority=authority)
    except Order.DoesNotExist:
        return HttpResponse("سفارش یافت نشد.")

    data = {
        "merchant_id": MERCHANT_ID,
        "amount": int(order.total_amount) * 10,
        "authority": authority
    }
    headers = {'content-type': 'application/json', 'accept': 'application/json'}

    response = requests.post(ZARINPAL_VERIFY_URL, data=json.dumps(data), headers=headers)
    result = response.json()

    if response.status_code == 200 and result['data']['code'] in [100, 101]:
        ref_id = result['data']['ref_id']
        order.status = 'paid'
        order.ref_id = ref_id
        order.save()
        send_telegram_receipt.delay(order.id)
        return HttpResponse(f"پرداخت با موفقیت انجام شد. کد پیگیری: {ref_id}")
    else:
        order.status = 'failed'
        order.save()
        return HttpResponse("تراکنش ناموفق بود یا تایید نشد.")