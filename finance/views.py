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

from .models import  AdminCardSettings, Wallet, WalletPack, WithdrawalRequest, WalletTopUpLog, CardToCardInstruction
from .serializers import  AdminCardSettingsSerializer, DepositReceiptSerializer, WalletPackSerializer, WalletSerializer, WalletTopUpSerializer, WithdrawalRequestSerializer, CardToCardInstructionSerializer

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
    
    
    
from django.conf import settings

# ===================== ای پی ای افزایش موجودی کیف پول =====================
class CreatePaymentLinkAPIView(APIView):
    permission_classes = [IsAuthenticated]

    REDIRECT_BASE_URL = getattr(settings, 'CALLBACK_REDIRECT_BASE_URL', 'https://safarnameh24.com') + "/dashboard/financial/wallet"
    CALLBACK_PATH = "/api/v1/finance/wallet/payment-callback/"
    MIN_TOPUP = 1_000_000
    MAX_TOPUP = 100_000_000

    STATUS_SUCCESS = "success"
    STATUS_FAILURE = "unsuccessfull"

    def get_permissions(self):
        if getattr(self, 'request', None) and self.request.method in ['GET', 'POST']:
            return [AllowAny()]
        return [IsAuthenticated()]

    def _validate_amount(self, amount_toman):
        if amount_toman < self.MIN_TOPUP or amount_toman > self.MAX_TOPUP:
            raise ValidationError({"amount": [f"مبلغ باید بین {self.MIN_TOPUP:,} تا {self.MAX_TOPUP:,} تومان باشد."]})

    def _store_session(self, request, **kwargs):
        for k, v in kwargs.items():
            request.session[k] = v
        request.session.save()

    def _clear_session(self, request):
        keys = ["wallet_amount", "wallet_authority", "wallet_order_id", "active_gateway", "wallet_user_id"]
        for key in keys:
            request.session.pop(key, None)
        request.session.save()

    def _build_response(self, status_key, amount=0):
        """JSON برمی‌گرداند تا فرانت بهتر مدیریت کند"""
        return Response({
            "status": status_key,
            "amount": amount,
            "redirect_url": f"{self.REDIRECT_BASE_URL}?payment_status={status_key}&amount={amount}"
        })

    def _get_user(self, request):
        if request.user.is_authenticated:
            return request.user
        user_id = request.session.get("wallet_user_id")
        if user_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                return User.objects.get(id=user_id)
            except User.DoesNotExist:
                pass
        return None

    # POST: ایجاد لینک پرداخت
    @swagger_auto_schema(
        operation_summary="ایجاد لینک پرداخت برای افزایش موجودی کیف پول کاربر",
        request_body=WalletTopUpSerializer,
        responses={200: "Payment link created"}
    )
    def post(self, request):
        # تشخیص کال‌بک تست
        if "/payment-callback/" in request.path:
            return self._handle_payment_callback(request)

        serializer = WalletTopUpSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        amount_toman = serializer.validated_data['amount']
        try:
            self._validate_amount(amount_toman)
        except ValidationError as ve:
            return Response(ve.detail, status=400)

        # ذخیره مبلغ و کاربر در session
        self._store_session(request, wallet_user_id=request.user.id, wallet_amount=amount_toman)

        pref = PaymentGatewayPreference.objects.first()
        if not pref:
            return Response({"error": "Gateway preference not configured"}, status=500)

        if pref.active_gateway == "zarinpal":
            return self._handle_zarinpal_payment(amount_toman, request)
        elif pref.active_gateway == "iraniangateway":
            return self._handle_iraniangateway_payment(amount_toman, request)
        else:
            return Response({"error": "Unsupported gateway"}, status=500)

    def get(self, request, *args, **kwargs):
        return self._handle_payment_callback(request)

    def post(self, request, *args, **kwargs):   # تست دستی کال‌بک
        if "/payment-callback/" in request.path:
            return self._handle_payment_callback(request)
        # fallback به متد اصلی
        return self.post(request)

    def _handle_payment_callback(self, request):
        authority = request.GET.get("Authority") or request.data.get("Authority")
        status_param = request.GET.get("Status") or request.GET.get("status") or request.data.get("status")
        order_id = request.GET.get("order_id") or request.data.get("order_id")

        saved_amount = request.session.get("wallet_amount", 0)
        user = self._get_user(request)

        if not user:
            logger.error("Callback: User not found")
            self._clear_session(request)
            return self._build_response(self.STATUS_FAILURE, saved_amount)

        if authority and status_param == "OK":
            return self._verify_zarinpal(request, user, authority, saved_amount)

        if order_id and status_param and status_param.lower() in ["success", "ok", "1"]:
            return self._verify_iraniangateway(request, user, order_id, saved_amount)

        self._clear_session(request)
        return self._build_response(self.STATUS_FAILURE, saved_amount)

    def _verify_zarinpal(self, request, user, authority, amount_toman):
        try:
            gateway = ZarinpalGateway.objects.first()
            if not gateway:
                raise Exception("Zarinpal not configured")

            if gateway.mode == "sandbox":
                logger.info("Sandbox: Payment accepted")
                self._update_wallet_and_log(user, amount_toman, 'zarinpal', authority)
                self._clear_session(request)
                return self._build_response(self.STATUS_SUCCESS, amount_toman)

            amount_riel = amount_toman * 10
            resp = requests.post(
                "https://api.zarinpal.com/pg/v4/payment/verify.json",
                json={"merchant_id": gateway.merchant_code, "amount": amount_riel, "authority": authority},
                headers={"Content-Type": "application/json", "Accept": "application/json"}
            )

            if resp.status_code == 200:
                result = resp.json()
                if result.get("data", {}).get("code") == 100:
                    self._update_wallet_and_log(user, amount_toman, 'zarinpal', authority)
                    self._clear_session(request)
                    return self._build_response(self.STATUS_SUCCESS, amount_toman)
        except Exception as e:
            logger.error(f"Zarinpal verify error: {e}")

        self._clear_session(request)
        return self._build_response(self.STATUS_FAILURE, amount_toman)

    def _verify_iraniangateway(self, request, user, order_id, amount_toman):
        try:
            gateway = IranianGateway.objects.first()
            if not gateway:
                raise Exception("Iranian gateway not configured")

            resp = requests.post(gateway.verify_url, json={
                "merchant_id": gateway.merchant_code,
                "order_id": order_id,
            })

            if resp.status_code == 200:
                result = resp.json()
                if result.get("success"):
                    self._update_wallet_and_log(user, amount_toman, 'iraniangateway', order_id)
                    self._clear_session(request)
                    return self._build_response(self.STATUS_SUCCESS, amount_toman)
        except Exception as e:
            logger.error(f"IranianGateway verify error: {e}")

        self._clear_session(request)
        return self._build_response(self.STATUS_FAILURE, amount_toman)

    def _update_wallet_and_log(self, user, amount, gateway_name, authority_or_order):
        wallet = Wallet.objects.get(user=user)
        wallet.balance += amount
        wallet.save()

        WalletTopUpLog.objects.create(
            user=user,
            amount=amount,
            gateway=gateway_name,
            authority_or_order=authority_or_order
        )
        logger.info(f"Wallet topped up: {user} +{amount:,} via {gateway_name}")

    def _handle_zarinpal_payment(self, amount_toman, request):
        gateway = ZarinpalGateway.objects.first()
        if not gateway:
            return Response({"error": "Zarinpal gateway not configured"}, status=500)

        try:
            amount_riel = amount_toman * 10
            payment_link, authority = self._create_zarinpal_payment(gateway, amount_riel, request)
            self._store_session(request, wallet_amount=amount_toman, wallet_authority=authority, active_gateway="zarinpal")
            return Response({
                "gateway": "zarinpal",
                "amount": amount_toman,
                "payment_link": payment_link,
            })
        except Exception as e:
            return Response({"error": str(e)}, status=500)

    def _handle_iraniangateway_payment(self, amount_toman, request):
        gateway = IranianGateway.objects.first()
        if not gateway:
            return Response({"error": "Iranian gateway not configured"}, status=500)

        try:
            payment_link, order_id = self._create_iraniangateway_payment(gateway, amount_toman, request)
            self._store_session(request, wallet_amount=amount_toman, wallet_order_id=order_id, active_gateway="iraniangateway")
            return Response({
                "gateway": "iraniangateway",
                "amount": amount_toman,
                "payment_link": payment_link,
            })
        except Exception as e:
            return Response({"error": str(e)}, status=500)

    def _create_zarinpal_payment(self, gateway, amount_riel, request):
        base_url = request.build_absolute_uri('/')
        callback_url = urljoin(base_url, self.CALLBACK_PATH.lstrip('/'))

        data = {
            "merchant_id": gateway.merchant_code,
            "amount": amount_riel,
            "callback_url": callback_url,
            "description": "افزایش موجودی کیف پول",
        }

        url = "https://sandbox.zarinpal.com/pg/v4/payment/request.json" if gateway.mode == "sandbox" else "https://api.zarinpal.com/pg/v4/payment/request.json"
        base = "https://sandbox.zarinpal.com/pg/StartPay" if gateway.mode == "sandbox" else "https://www.zarinpal.com/pg/StartPay"

        resp = requests.post(url, json=data, headers={"Content-Type": "application/json", "Accept": "application/json"})
        if resp.status_code != 200:
            raise Exception("Zarinpal request failed")

        res = resp.json()
        if res.get("data", {}).get("code") != 100:
            raise Exception(f"Zarinpal error: {res}")

        authority = res["data"]["authority"]
        return f"{base}/{authority}", authority

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
            raise Exception(result.get('message', 'Unknown error'))

        return result.get("payment_url"), result.get("order_id")


# بقیه ویوها بدون تغییر
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
    

class DepositReceiptCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=DepositReceiptSerializer,
        operation_summary="ثبت فیش واریزی",
        responses={201: DepositReceiptSerializer, 400: "خطا در داده‌های ورودی"}
    )
    def post(self, request):
        serializer = DepositReceiptSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class WithdrawalRequestCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=WithdrawalRequestSerializer,
        operation_summary="ثبت درخواست برداشت از کیف پول",
        responses={201: WithdrawalRequestSerializer, 400: "خطا در داده‌های ورودی"}
    )
    def post(self, request):
        serializer = WithdrawalRequestSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CardToCardInstructionAPIView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(operation_summary="دریافت متن توضیحات کارت به کارت")
    def get(self, request):
        obj = CardToCardInstruction.objects.first()
        if not obj:
            return Response({"text": ""}, status=status.HTTP_200_OK)
        serializer = CardToCardInstructionSerializer(obj)
        return Response(serializer.data, status=status.HTTP_200_OK)


class FinancialOperationsListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(operation_summary="لیست عملیات مالی")
    def get(self, request):
        user = request.user
        page = int(request.GET.get('page', 1) or 1)
        page_size = int(request.GET.get('page_size', 18) or 18)
        if page_size <= 0:
            page_size = 18

        operations = []

        from .models import DepositReceipt
        import jdatetime

        def to_jalali(dt):
            try:
                return jdatetime.datetime.fromgregorian(datetime=dt).strftime('%Y/%m/%d')
            except Exception:
                return ''

        deposit_receipts = DepositReceipt.objects.filter(user=user)
        for receipt in deposit_receipts:
            operations.append({
                "type": "card_to_card",
                "service_type": "کارت به کارت",
                "amount": int(receipt.amount),
                "status": "success" if receipt.is_approved else "unsuccess",
                "status_display": "عملیات موفقیت آمیز بود" if receipt.is_approved else "عملیات ناموفق بود",
                "date": receipt.deposit_date_jalali,
                "created_at": receipt.created_at,
            })

        withdrawal_requests = WithdrawalRequest.objects.filter(user=user)
        for w in withdrawal_requests:
            success = w.status in ["approved", "completed"]
            operations.append({
                "type": "withdrawal",
                "service_type": "برداشت وجه",
                "amount": int(w.amount),
                "status": "success" if success else "unsuccess",
                "status_display": "عملیات موفقیت آمیز بود" if success else "عملیات ناموفق بود",
                "date": to_jalali(w.created_at),
                "created_at": w.created_at,
            })

        topups = WalletTopUpLog.objects.filter(user=user)
        for t in topups:
            operations.append({
                "type": "wallet_increase",
                "service_type": "افزایش کیف پول",
                "amount": int(t.amount),
                "status": "success",
                "status_display": "عملیات موفقیت آمیز بود",
                "date": to_jalali(t.created_at),
                "created_at": t.created_at,
            })

        operations.sort(key=lambda op: op['created_at'], reverse=True)
        
        for op in operations:
            del op['created_at']

        total_items = len(operations)
        total_pages = (total_items + page_size - 1) // page_size
        if page > total_pages and total_pages != 0:
            page = total_pages

        start = (page - 1) * page_size
        end = start + page_size
        page_items = operations[start:end]

        return Response({
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "total_items": total_items,
            "operations": page_items,
        }, status=status.HTTP_200_OK)