from django.contrib.contenttypes.models import ContentType
import requests
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListCreateAPIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from setting_payment.models import IranianGateway, PaymentGatewayPreference, ZarinpalGateway

from .models import  Wallet, WalletPack
from .serializers import  WalletPackSerializer, WalletSerializer, WalletTopUpSerializer





# ای پی ای دریافت موجودی کیف پول
class WalletRetrieveAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="دریافت موجودی کیف پول",
        operation_description="""
        این API به کاربر احراز هویت شده اجازه می‌دهد تا موجودی کیف پول خود را مشاهده کند.
        
        این موجودی فقط برای کاربر جاری بازگردانده می‌شود.
        """,
        responses={200: WalletSerializer()}
    )
    def get(self, request):
        try:
            wallet = Wallet.objects.get(user=request.user)
        except Wallet.DoesNotExist:
            return Response({"detail": "کیف پول یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

        serializer = WalletSerializer(wallet)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    

# ای پی ای لیست بسته های کیف پول
class WalletPackListAPIView(APIView):
    """
    API برای دریافت لیست مبالغ پکیج‌های کیف پول
    """

    @swagger_auto_schema(
        operation_summary="دریافت مبالغ پکیج‌های کیف پول",
        operation_description="""
        این API تمام پکیج‌های تعریف‌شده برای شارژ کیف پول را برمی‌گرداند.
        
        هر پکیج شامل چهار مبلغ از پیش تعیین‌شده است.
        
        مقدار‌ها در پنل مدیریت توسط شما تنظیم می‌شوند.
        """,
        responses={200: WalletPackSerializer(many=True)}
    )
    def get(self, request):
        packs = WalletPack.objects.all()

        if not packs.exists():
            return Response(
                {"detail": "هیچ پکیجی برای کیف پول ثبت نشده است."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = WalletPackSerializer(packs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    
    
#ای پی ای افزایش موجودی کیف پول 
class CreatePaymentLinkAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="ایجاد لینک پرداخت برای افزایش موجودی کیف پول کاربر",
        operation_description="""
        این API یک مبلغ افزایش موجودی کیف پول را به تومان از کاربر دریافت می‌کند و با توجه به 
        تنظیمات پنل مدیریت، درگاه پرداخت فعال را شناسایی کرده و لینک پرداخت مناسب را تولید می‌کند.
        """,
        request_body=WalletTopUpSerializer,
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'gateway': openapi.Schema(type=openapi.TYPE_STRING, description='نام درگاه پرداخت فعال'),
                    'amount': openapi.Schema(type=openapi.TYPE_INTEGER, description='مبلغ افزایش کیف پول به تومان'),
                    'payment_link': openapi.Schema(type=openapi.TYPE_STRING, description='لینک پرداخت'),
                }
            ),
            400: 'درخواست نامعتبر (مبلغ خارج از بازه یا فرمت نامعتبر)',
            500: 'خطای داخلی سرور (تنظیمات درگاه پرداخت موجود نیست یا نامعتبر است)',
        }
    )
    def post(self, request):
        serializer = WalletTopUpSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        amount_toman = serializer.validated_data['amount']
        amount_riel = amount_toman * 10  # تومان به ریال

        pref = PaymentGatewayPreference.objects.first()
        if not pref:
            return Response({"error": "No active gateway preference configured"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if pref.active_gateway == "zarinpal":
            gateway = ZarinpalGateway.objects.first()
            if not gateway:
                return Response({"error": "Zarinpal gateway is not configured"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            try:
                payment_link = self._request_zarinpal_payment_link(gateway, amount_riel, request)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            gateway_name = "zarinpal"

        elif pref.active_gateway == "iraniangateway":
            gateway = IranianGateway.objects.first()
            if not gateway:
                return Response({"error": "Iranian gateway is not configured"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            # ایران درگاه همان لینک ساده است
            payment_link = self._build_iraniangateway_payment_link(gateway, amount_riel)
            gateway_name = "iraniangateway"

        else:
            return Response({"error": "Unknown active gateway"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            "gateway": gateway_name,
            "amount": amount_toman,
            "payment_link": payment_link,
        }, status=status.HTTP_200_OK)

    def _request_zarinpal_payment_link(self, gateway: ZarinpalGateway, amount_riel: int, request) -> str:
        callback_url = request.build_absolute_uri("/api/payment/callback/")  # آدرس callback خودت رو اصلاح کن
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        data = {
            "MerchantID": gateway.merchant_code,
            "Amount": amount_riel,
            "CallbackURL": callback_url,
            "Description": "افزایش موجودی کیف پول",
        }
        # انتخاب url بر اساس حالت sandbox یا production
        if gateway.mode == 'sandbox':
            url = "https://sandbox.zarinpal.com/pg/rest/WebGate/PaymentRequest.json"
            payment_base_url = "https://sandbox.zarinpal.com/pg/StartPay"
        else:
            url = "https://www.zarinpal.com/pg/rest/WebGate/PaymentRequest.json"
            payment_base_url = "https://www.zarinpal.com/pg/StartPay"

        resp = requests.post(url, json=data, headers=headers, timeout=10)
        if resp.status_code != 200:
            raise Exception(f"HTTP error from Zarinpal: {resp.status_code}")
        result = resp.json()
        if result.get("Status") == 100:
            authority = result.get("Authority")
            if not authority or not authority.startswith("S"):
                raise Exception("Invalid authority received from Zarinpal.")
            payment_link = f"{payment_base_url}/{authority}"
            return payment_link
        else:
            raise Exception(f"Zarinpal error: {result.get('Status')}")

    def _build_iraniangateway_payment_link(self, gateway: IranianGateway, amount_riel: int) -> str:
        # فرض شده در ایران‌درگاه لینک مستقیم بر اساس payment_url و merchant_code ساخته می‌شود
        return f"{gateway.payment_url}/{gateway.merchant_code}?amount={amount_riel}"