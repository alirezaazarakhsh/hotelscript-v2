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

    @swagger_auto_schema(
        operation_summary="ایجاد لینک پرداخت برای افزایش موجودی کیف پول کاربر",
        operation_description="""
        این API یک مبلغ افزایش موجودی کیف پول را از کاربر دریافت می‌کند و با توجه به 
        تنظیمات پنل مدیریت، درگاه پرداخت فعال را شناسایی کرده و لینک پرداخت مناسب را تولید می‌کند.
        
        ✔ همین API همچنین کال‌بک برگشتی زرین‌پال را هندل می‌کند (GET)
        ✔ پرداخت را Verify می‌کند
        ✔ کاربر را به آدرس زیر Redirect می‌کند:
            - موفق:  payment_status=ok
            - ناموفق: payment_status=no
        """,
        request_body=WalletTopUpSerializer,
        responses={200: "Payment link created"}
    )
    def post(self, request):
        """ساخت لینک پرداخت (مرحله ۱)"""

        serializer = WalletTopUpSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        amount_toman = serializer.validated_data['amount']
        if amount_toman < 10000 or amount_toman > 1000000:
            return Response(
                {"amount": ["مبلغ باید بین ۱۰,۰۰۰ تا ۱,۰۰۰,۰۰۰ تومان باشد."]},
                status=400
            )

        amount_riel = amount_toman * 10
        pref = PaymentGatewayPreference.objects.first()

        if not pref:
            return Response({"error": "Gateway preference not configured"}, status=500)

        if pref.active_gateway == "zarinpal":
            gateway = ZarinpalGateway.objects.first()
            if not gateway:
                return Response({"error": "Zarinpal gateway not configured"}, status=500)

            try:
                payment_link, authority = self._create_zarinpal_payment(
                    gateway, amount_riel, request
                )
            except Exception as e:
                return Response({"error": str(e)}, status=500)

            # ذخیره اطلاعات در سشن برای وریفای
            request.session["wallet_amount"] = amount_riel
            request.session["wallet_authority"] = authority

            return Response({
                "gateway": "zarinpal",
                "amount": amount_toman,
                "payment_link": payment_link
            })

        return Response({"error": "Unsupported gateway"}, status=500)

    # -----------------------------------------------------------------
    # 🎯 همین API کال‌بک زرین‌پال را هندل می‌کند
    # -----------------------------------------------------------------
    def get(self, request):
        """کال‌بک زرین‌پال (مرحله ۲)"""

        status_param = request.GET.get("Status")
        authority = request.GET.get("Authority")

        # اگر کاربر پرداخت را لغو کرد
        if status_param != "OK":
            return redirect(
                "https://safarnameh24.com/dashboard/financial/wallet?payment_status=no"
            )

        # داده‌های ذخیره‌شده
        saved_amount = request.session.get("wallet_amount")
        saved_authority = request.session.get("wallet_authority")

        if not saved_amount or not saved_authority or saved_authority != authority:
            return redirect(
                "https://safarnameh24.com/dashboard/financial/wallet?payment_status=no"
            )

        # وریفای نهایی
        gateway = ZarinpalGateway.objects.first()
        verify_url = (
            "https://sandbox.zarinpal.com/pg/v4/payment/verify.json"
            if gateway.mode == "sandbox"
            else "https://api.zarinpal.com/pg/v4/payment/verify.json"
        )

        verify_data = {
            "merchant_id": gateway.merchant_code,
            "amount": saved_amount,
            "authority": authority
        }

        response = requests.post(verify_url, json=verify_data)
        result = response.json()

        if result.get("data", {}).get("code") == 100:
            # ✔ پرداخت موفق → می‌توانی اینجا کیف پول را شارژ کنی
            return redirect(
                "https://safarnameh24.com/dashboard/financial/wallet?payment_status=ok"
            )

        # ❌ پرداخت ناموفق
        return redirect(
            "https://safarnameh24.com/dashboard/financial/wallet?payment_status=no"
        )

    # -----------------------------------------------------------------
    # ساخت لینک زرین‌پال
    # -----------------------------------------------------------------
    def _create_zarinpal_payment(self, gateway, amount, request):
        callback_url = request.build_absolute_uri()  # همین API کال‌بک است

        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        data = {
            "merchant_id": gateway.merchant_code,
            "amount": amount,
            "callback_url": callback_url,
            "description": "افزایش موجودی کیف پول",
        }

        # محیط
        if gateway.mode == "sandbox":
            url = "https://sandbox.zarinpal.com/pg/v4/payment/request.json"
            base = "https://sandbox.zarinpal.com/pg/StartPay"
        else:
            url = "https://api.zarinpal.com/pg/v4/payment/request.json"
            base = "https://www.zarinpal.com/pg/StartPay"

        resp = requests.post(url, json=data, headers=headers)
        if resp.status_code != 200:
            raise Exception("Zarinpal request failed")

        res = resp.json()

        if res.get("data", {}).get("code") != 100:
            raise Exception("Zarinpal error")

        authority = res["data"]["authority"]
        payment_link = f"{base}/{authority}"

        return payment_link, authority
    
           
        
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
    permission_classes = [permissions.IsAuthenticated]

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