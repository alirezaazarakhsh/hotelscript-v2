from django.contrib.contenttypes.models import ContentType
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

        مراحل کلی:
        1. دریافت مقدار 'amount' به تومان از درخواست کاربر.
        2. اعتبارسنجی مبلغ (عدد صحیح، در بازه مجاز بین 10,000 تا 1,000,000 تومان).
        3. خواندن تنظیمات درگاه فعال از مدل PaymentGatewayPreference.
        4. اگر درگاه فعال زرین‌پال باشد، لینک پرداخت مخصوص زرین‌پال ساخته می‌شود.
        5. اگر درگاه فعال ایران‌درگاه باشد، لینک پرداخت مخصوص ایران‌درگاه ساخته می‌شود.
        6. در صورت نبود درگاه فعال یا تنظیمات ناقص، خطای مناسب برگردانده می‌شود.

        **توجه**:
        - مبلغ وارد شده باید بین ده هزار تا یک میلیون تومان باشد.
        - تنها یک تنظیم درگاه فعال در سیستم باید وجود داشته باشد.
        - لینک پرداخت تولید شده، شامل پارامترهای مورد نیاز هر درگاه است (مبلغ به ریال و شناسه مرچنت).

        نمونه ورودی (JSON):
        ```json
        {
            "amount": 15000
        }
        ```

        نمونه خروجی موفق (HTTP 200):
        ```json
        {
            "gateway": "zarinpal",
            "amount": 15000,
            "payment_link": "https://sandbox.zarinpal.com/pg/StartPay/MERCHANT_CODE?amount=150000"
        }
        ```

        نمونه خطای مبلغ نامعتبر (HTTP 400):
        ```json
        {
            "amount": ["Ensure this value is greater than or equal to 10000."]
        }
        ```

        نمونه خطای عدم تنظیم درگاه (HTTP 500):
        ```json
        {
            "error": "No active gateway preference configured"
        }
        ```
        """,
        request_body=WalletTopUpSerializer,
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'gateway': openapi.Schema(type=openapi.TYPE_STRING, description='نام درگاه پرداخت فعال (مثلاً zarinpal یا iraniangateway)'),
                    'amount': openapi.Schema(type=openapi.TYPE_INTEGER, description='مبلغ افزایش کیف پول به تومان'),
                    'payment_link': openapi.Schema(type=openapi.TYPE_STRING, description='لینک پرداخت ایجاد شده برای انتقال کاربر به صفحه پرداخت'),
                },
                example={
                    'gateway': 'zarinpal',
                    'amount': 15000,
                    'payment_link': 'https://sandbox.zarinpal.com/pg/StartPay/MERCHANT_CODE?amount=150000'
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
        amount_riel = amount_toman * 10  # تبدیل تومان به ریال برای ارسال به درگاه

        pref = PaymentGatewayPreference.objects.first()
        if not pref:
            return Response(
                {"error": "No active gateway preference configured"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        if pref.active_gateway == "zarinpal":
            gateway = ZarinpalGateway.objects.first()
            if not gateway:
                return Response(
                    {"error": "Zarinpal gateway is not configured"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            payment_link = self._build_zarinpal_payment_link(gateway, amount_riel)
            gateway_name = "zarinpal"

        elif pref.active_gateway == "iraniangateway":
            gateway = IranianGateway.objects.first()
            if not gateway:
                return Response(
                    {"error": "Iranian gateway is not configured"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            payment_link = self._build_iraniangateway_payment_link(gateway, amount_riel)
            gateway_name = "iraniangateway"

        else:
            return Response(
                {"error": "Unknown active gateway"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {
                "gateway": gateway_name,
                "amount": amount_toman,  # در خروجی تومان نشان می‌دهیم
                "payment_link": payment_link,
            },
            status=status.HTTP_200_OK
        )

    def _build_zarinpal_payment_link(self, gateway: ZarinpalGateway, amount_riel: int) -> str:
        return f"{gateway.payment_url}/{gateway.merchant_code}?amount={amount_riel}"

    def _build_iraniangateway_payment_link(self, gateway: IranianGateway, amount_riel: int) -> str:
        return f"{gateway.payment_url}/{gateway.merchant_code}?amount={amount_riel}"