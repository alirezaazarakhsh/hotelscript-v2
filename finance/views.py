from urllib.parse import urljoin
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import redirect
import requests
import logging
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListCreateAPIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from setting_payment.models import IranianGateway, PaymentGatewayPreference, ZarinpalGateway

from .models import  AdminCardSettings, Wallet, WalletPack
from .serializers import  AdminCardSettingsSerializer, DepositReceiptSerializer, WalletPackSerializer, WalletSerializer, WalletTopUpSerializer

logger = logging.getLogger(__name__)




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

    REDIRECT_BASE_URL = "https://safarnameh24.com/dashboard/financial/wallet"
    CALLBACK_PATH = "/api/v1/finance/wallet/payment-callback/"
    MIN_TOPUP = 1_000_000
    MAX_TOPUP = 100_000_000
    # وضعیت‌های استاندارد خروجی برای فرانت
    STATUS_SUCCESS = "success"          # پرداخت موفق
    STATUS_FAILURE = "unsuccessfull"    # پرداخت ناموفق

    def _validate_amount(self, amount_toman):
        if amount_toman < self.MIN_TOPUP or amount_toman > self.MAX_TOPUP:
            raise ValidationError({"amount": [f"مبلغ باید بین {self.MIN_TOPUP:,} تا {self.MAX_TOPUP:,} تومان باشد."]})

    def _store_session(self, request, **kwargs):
        for k, v in kwargs.items():
            request.session[k] = v
        request.session.save()

    def _build_redirect(self, status_key, amount):
        amount_part = amount if amount else ''
        return redirect(f"{self.REDIRECT_BASE_URL}?payment_status={status_key}&amount={amount_part}")

    @swagger_auto_schema(
        operation_summary="ایجاد لینک پرداخت برای افزایش موجودی کیف پول کاربر",
        operation_description="""
        این API یک مبلغ افزایش موجودی کیف پول را از کاربر دریافت می‌کند و با توجه به
        تنظیمات پنل مدیریت، درگاه پرداخت فعال را شناسایی کرده و لینک پرداخت مناسب را تولید می‌کند.

        ✔ لینک پرداخت را با توجه به درگاه فعال (زرین‌پال یا ایران‌درگاه) تولید می‌کند
        ✔ اطلاعات پرداخت را در Session ذخیره می‌کند
        ✔ کاربر را به درگاه پرداخت هدایت می‌کند
        ✔ پس از پرداخت، درگاه کاربر را به callback API برمی‌گرداند
        """,
        request_body=WalletTopUpSerializer,
        responses={200: "Payment link created"}
    )
    def post(self, request):
        serializer = WalletTopUpSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        amount_toman = serializer.validated_data['amount']
        try:
            self._validate_amount(amount_toman)
        except ValidationError as ve:
            return Response(ve.detail, status=400)

        pref = PaymentGatewayPreference.objects.first()
        if not pref:
            return Response({"error": "Gateway preference not configured"}, status=500)

        if pref.active_gateway == "zarinpal":
            gateway = ZarinpalGateway.objects.first()
            if not gateway:
                return Response({"error": "Zarinpal gateway not configured"}, status=500)

            amount_riel = amount_toman * 10  # تبدیل تومان به ریال برای زرین‌پال
            try:
                payment_link, authority = self._create_zarinpal_payment(gateway, amount_riel, request)
            except Exception as e:
                return Response({"error": str(e)}, status=500)

            self._store_session(request,
                                wallet_amount=amount_toman,
                                wallet_authority=authority,
                                active_gateway="zarinpal")

            return Response({
                "gateway": "zarinpal",
                "amount": amount_toman,
                "payment_link": payment_link,
            })

        elif pref.active_gateway == "iraniangateway":
            gateway = IranianGateway.objects.first()
            if not gateway:
                return Response({"error": "Iranian gateway not configured"}, status=500)

            try:
                payment_link, order_id = self._create_iraniangateway_payment(gateway, amount_toman, request)
            except Exception as e:
                return Response({"error": str(e)}, status=500)

            self._store_session(request,
                                wallet_amount=amount_toman,
                                wallet_order_id=order_id,
                                active_gateway="iraniangateway")

            return Response({
                "gateway": "iraniangateway",
                "amount": amount_toman,
                "payment_link": payment_link,
            })

        else:
            return Response({"error": "Unsupported gateway"}, status=500)

    def get_permissions(self):
        # اجازه دسترسی آزاد برای کال‌بک (GET) تا درگاه بتواند کاربر را برگرداند
        if getattr(self, 'request', None) and self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    # هندل کردن کال‌بک پرداخت از همان View
    def get(self, request, *args, **kwargs):
        return self._handle_payment_callback(request)

    def _handle_payment_callback(self, request):
        authority = request.GET.get("Authority")
        status_param = request.GET.get("Status") or request.GET.get("status")
        order_id = request.GET.get("order_id")

        saved_amount = request.session.get("wallet_amount", 0)
        # active_gateway = request.session.get("active_gateway")  # در صورت نیاز

        # زرین‌پال
        if authority and status_param:
            if status_param == "OK":
                try:
                    gateway = ZarinpalGateway.objects.first()
                    if gateway and request.user.is_authenticated:
                        amount_riel = saved_amount * 10
                        verify_url = (
                            "https://sandbox.zarinpal.com/pg/v4/payment/verify.json"
                            if gateway.mode == "sandbox"
                            else "https://api.zarinpal.com/pg/v4/payment/verify.json"
                        )
                        verify_data = {
                            "merchant_id": gateway.merchant_code,
                            "amount": amount_riel,
                            "authority": authority,
                        }
                        headers = {"Content-Type": "application/json", "Accept": "application/json"}
                        resp = requests.post(verify_url, json=verify_data, headers=headers)
                        if resp.status_code == 200:
                            result = resp.json()
                            logger.info(f"Zarinpal verify response: {result}")
                            if result.get("data", {}).get("code") == 100:
                                wallet = Wallet.objects.get(user=request.user)
                                wallet.balance += saved_amount
                                wallet.save()
                                self._clear_session(request)
                                # پرداخت موفق (success)
                                return self._build_redirect(self.STATUS_SUCCESS, saved_amount)
                except Exception:
                    pass
            # عدم موفقیت یا عدم verify
            self._clear_session(request)
            # پرداخت ناموفق (unsuccessfull)
            return self._build_redirect(self.STATUS_FAILURE, saved_amount)

        # ایران‌درگاه
        if order_id and status_param:
            if status_param.lower() in ["success", "ok", "1"]:
                try:
                    gateway = IranianGateway.objects.first()
                    if gateway and request.user.is_authenticated:
                        verify_data = {
                            "merchant_id": gateway.merchant_code,
                            "order_id": order_id,
                        }
                        resp = requests.post(gateway.verify_url, json=verify_data)
                        if resp.status_code == 200:
                            result = resp.json()
                            logger.info(f"IranianGateway verify response: {result}")
                            if result.get("success"):
                                wallet = Wallet.objects.get(user=request.user)
                                wallet.balance += saved_amount
                                wallet.save()
                                self._clear_session(request)
                                return self._build_redirect(self.STATUS_SUCCESS, saved_amount)
                except Exception:
                    pass
            self._clear_session(request)
            return self._build_redirect(self.STATUS_FAILURE, saved_amount)

        # ورودی نامعتبر
        self._clear_session(request)
        # عدم نمایش مقدار صفر؛ اگر مبلغ ذخیره شده نبود، پارامتر amount را خالی می‌فرستیم
        return self._build_redirect(self.STATUS_FAILURE, saved_amount)

    def _create_zarinpal_payment(self, gateway, amount_riel, request):
        base_url = request.build_absolute_uri('/')  # https://cps.safarnameh24.com/
        callback_url = urljoin(base_url, self.CALLBACK_PATH.lstrip('/'))

        data = {
            "merchant_id": gateway.merchant_code,
            "amount": amount_riel,
            "callback_url": callback_url,
            "description": "افزایش موجودی کیف پول",
        }
        headers = {"Content-Type": "application/json", "Accept": "application/json"}

        url = (
            "https://sandbox.zarinpal.com/pg/v4/payment/request.json"
            if gateway.mode == "sandbox"
            else "https://api.zarinpal.com/pg/v4/payment/request.json"
        )
        base = (
            "https://sandbox.zarinpal.com/pg/StartPay"
            if gateway.mode == "sandbox"
            else "https://www.zarinpal.com/pg/StartPay"
        )

        resp = requests.post(url, json=data, headers=headers)
        if resp.status_code != 200:
            raise Exception("Zarinpal request failed")

        res = resp.json()

        if res.get("data", {}).get("code") != 100:
            raise Exception(f"Zarinpal error: {res}")

        authority = res["data"]["authority"]
        payment_link = f"{base}/{authority}"
        return payment_link, authority

    def _create_iraniangateway_payment(self, gateway, amount_toman, request):
        base_url = request.build_absolute_uri('/')
        callback_url = urljoin(base_url, self.CALLBACK_PATH.lstrip('/'))

        data = {
            "merchant_id": gateway.merchant_code,
            "amount": amount_toman,
            "callback_url": callback_url,
            "description": "افزایش موجودی کیف پول",
        }

        resp = requests.post(gateway.request_url, json=data)
        if resp.status_code != 200:
            raise Exception("Iranian gateway request failed")

        result = resp.json()
        if not result.get("success"):
            raise Exception(f"Iranian gateway error: {result.get('message')}")

        payment_url = result.get("payment_url")
        order_id = result.get("order_id")
        if not payment_url or not order_id:
            raise Exception("Invalid Iranian gateway response")

        return payment_url, order_id

    def _clear_session(self, request):
        keys = ["wallet_amount", "wallet_authority", "wallet_order_id", "active_gateway"]
        for key in keys:
            if key in request.session:
                del request.session[key]
        request.session.save()


# حذف View کال‌بک جداگانه؛ همه چیز در CreatePaymentLinkAPIView هندل می‌شود
        
        
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
    
    

#ای پی ای فیش واریز دستی کاربران
class DepositReceiptCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=DepositReceiptSerializer,
        operation_summary="ثبت فیش واریزی",
        operation_description="""
        این API به کاربر اجازه می‌دهد فیش واریزی خود را ثبت کند.
        
        فیلدهای مورد نیاز:
        - نام واریز کننده
        - شماره پیگیری ۱۲ رقمی
        - مبلغ واریز
        - تاریخ واریز به فرمت شمسی (YYYY/MM/DD)
        - عکس فیش
        
        فیلد تایید (is_approved) فقط توسط ادمین قابل تغییر است.
        """,
        responses={
            201: DepositReceiptSerializer,
            400: "خطا در داده‌های ورودی"
        }
    )
    def post(self, request):
        serializer = DepositReceiptSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)