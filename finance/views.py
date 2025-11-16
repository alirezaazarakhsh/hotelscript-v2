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

from .models import  AdminCardSettings, Wallet, WalletPack
from .serializers import  AdminCardSettingsSerializer, WalletPackSerializer, WalletSerializer, WalletTopUpSerializer





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
        if amount_toman < 10000 or amount_toman > 1000000:
            return Response(
                {"amount": ["مبلغ باید بین ۱۰,۰۰۰ تا ۱,۰۰۰,۰۰۰ تومان باشد."]},
                status=status.HTTP_400_BAD_REQUEST
            )
        amount_riel = amount_toman * 10  # تبدیل تومان به ریال

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
        # اصلاح شده: آدرس کال‌بک دقیق با استفاده از build_absolute_uri و مسیر صحیح
        callback_url = request.build_absolute_uri('/api/v1/finance/payment/callback/')

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        data = {
            "merchant_id": gateway.merchant_code,
            "amount": amount_riel,
            "callback_url": callback_url,
            "description": "افزایش موجودی کیف پول",
        }

        if gateway.mode == 'sandbox':
            url = "https://sandbox.zarinpal.com/pg/v4/payment/request.json"
            payment_base_url = "https://sandbox.zarinpal.com/pg/StartPay"
        else:
            url = "https://api.zarinpal.com/pg/v4/payment/request.json"
            payment_base_url = "https://www.zarinpal.com/pg/StartPay"

        resp = requests.post(url, json=data, headers=headers, timeout=10)
        if resp.status_code != 200:
            raise Exception(f"HTTP error from Zarinpal: {resp.status_code}")

        result = resp.json()
        if result.get("data", {}).get("code") == 100:
            authority = result["data"].get("authority")
            if not authority or not authority.startswith("S"):
                raise Exception("Invalid authority received from Zarinpal.")
            payment_link = f"{payment_base_url}/{authority}"
            return payment_link
        else:
            code = result.get("data", {}).get("code")
            message = (
                result.get("errors", {}).get("message") or
                result.get("data", {}).get("message") or
                "خطایی در دریافت لینک پرداخت رخ داده است."
            )
            raise Exception(f"Zarinpal error {code}: {message}")

    def _build_iraniangateway_payment_link(self, gateway: IranianGateway, amount_riel: int) -> str:
        return f"{gateway.payment_url}/{gateway.merchant_code}?amount={amount_riel}"
    
    

# ای پی ای کال‌بک پرداخت زرین‌پال
class PaymentCallbackAPIView(APIView):
    def get(self, request):
        authority = request.GET.get('Authority')
        status_param = request.GET.get('Status')

        # اینجا می‌تونی لاجیک وریفای پرداخت رو انجام بدی

        return Response({
            "message": "Callback received",
            "Authority": authority,
            "Status": status_param
        }, status=status.HTTP_200_OK)
        
        
        
        
#ای پی ای مشخصات شماره کارت ادمین
class AdminCardSettingsAPIView(APIView):
    """
    API برای دریافت تنظیمات شماره کارت ادمین
    """

    @swagger_auto_schema(
        operation_summary="دریافت تنظیمات شماره کارت ادمین",
        operation_description="""
        این API تنظیمات شماره کارت ادمین را برمی‌گرداند.
        
        شامل شماره کارت ۱۶ رقمی، شماره شبای ۲۴ رقمی و نام صاحب حساب است.
        
        توجه: فقط یک تنظیمات وجود دارد و اگر تنظیمی ثبت نشده باشد، خطا بازگردانده می‌شود.
        """,
        responses={200: AdminCardSettingsSerializer}
    )
    def get(self, request):
        try:
            setting = AdminCardSettings.objects.get()
        except AdminCardSettings.DoesNotExist:
            return Response(
                {"detail": "تنظیمات شماره کارت ادمین ثبت نشده است."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = AdminCardSettingsSerializer(setting)
        return Response(serializer.data, status=status.HTTP_200_OK)