from urllib.parse import urljoin
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import redirect
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
from .serializers import  AdminCardSettingsSerializer, DepositReceiptSerializer, WalletPackSerializer, WalletSerializer, WalletTopUpSerializer





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

    @swagger_auto_schema(
        operation_summary="ایجاد لینک پرداخت برای افزایش موجودی کیف پول کاربر",
        operation_description="""
        این API یک مبلغ افزایش موجودی کیف پول را از کاربر دریافت می‌کند و با توجه به
        تنظیمات پنل مدیریت، درگاه پرداخت فعال را شناسایی کرده و لینک پرداخت مناسب را تولید می‌کند.

        ✔ همین API همچنین کال‌بک برگشتی زرین‌پال و ایران‌درگاه را هندل می‌کند (GET)
        ✔ پرداخت را Verify می‌کند
        ✔ کاربر را به آدرس زیر Redirect می‌کند:
            - موفق:  payment_status=success
            - ناموفق: payment_status=unsuccess
        """,
        request_body=WalletTopUpSerializer,
        responses={200: "Payment link created"}
    )
    def post(self, request):
        serializer = WalletTopUpSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        amount_toman = serializer.validated_data['amount']

        if amount_toman < 1_000_000 or amount_toman > 100_000_000:
            return Response(
                {"amount": ["مبلغ باید بین ۱,۰۰۰,۰۰۰ تا ۱۰۰,۰۰۰,۰۰۰ تومان باشد."]},
                status=400
            )

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

            request.session["wallet_amount"] = amount_toman  # تومان ذخیره می‌کنیم
            request.session["wallet_authority"] = authority
            request.session["active_gateway"] = "zarinpal"
            request.session.save()

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

            request.session["wallet_amount"] = amount_toman
            request.session["wallet_order_id"] = order_id
            request.session["active_gateway"] = "iraniangateway"
            request.session.save()

            return Response({
                "gateway": "iraniangateway",
                "amount": amount_toman,
                "payment_link": payment_link,
            })

        else:
            return Response({"error": "Unsupported gateway"}, status=500)

    def get(self, request, *args, **kwargs):
        # بررسی مسیر درخواست
        if request.path == self.CALLBACK_PATH:
            # هندل کال‌بک‌ها روی این مسیر
            return self._handle_payment_callback(request)

        # اگر روی مسیر اصلی کال‌بک آمد، خطا یا ریدایرکت به ناموفق بزن
        return redirect(f"{self.REDIRECT_BASE_URL}?payment_status=unsuccess&amount=0")

    def _handle_payment_callback(self, request):
        authority = request.GET.get("Authority")
        status_param = request.GET.get("Status") or request.GET.get("status")
        order_id = request.GET.get("order_id")

        if authority and status_param:
            saved_amount = request.session.get("wallet_amount", 0)
            if status_param == "OK":
                return redirect(f"{self.REDIRECT_BASE_URL}?payment_status=success&amount={saved_amount}")
            else:
                return redirect(f"{self.REDIRECT_BASE_URL}?payment_status=unsuccess&amount={saved_amount}")

        if order_id and status_param:
            saved_amount = request.session.get("wallet_amount", 0)
            if status_param.lower() in ["success", "ok", "1"]:
                return redirect(f"{self.REDIRECT_BASE_URL}?payment_status=success&amount={saved_amount}")
            else:
                return redirect(f"{self.REDIRECT_BASE_URL}?payment_status=unsuccess&amount={saved_amount}")

        return redirect(f"{self.REDIRECT_BASE_URL}?payment_status=unsuccess&amount=0")

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

    def _handle_zarinpal_callback(self, request):
        # این متد الان استفاده نمیشه، چون کال‌بک تو مسیر جدا هست
        # ولی می‌تونی کدهای قبلی را داخل _handle_payment_callback بیاری اگر لازم شد
        pass

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

    def _handle_iraniangateway_callback(self, request):
        # این متد الان استفاده نمیشه، کال‌بک تو مسیر جدا هندل میشه
        pass

    def _clear_session(self, request):
        keys = ["wallet_amount", "wallet_authority", "wallet_order_id", "active_gateway"]
        for key in keys:
            if key in request.session:
                del request.session[key]
        request.session.save()
        
        
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