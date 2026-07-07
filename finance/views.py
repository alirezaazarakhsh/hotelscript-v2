from urllib.parse import urljoin
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.conf import settings
import requests
import logging
import jdatetime
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from setting_payment.models import IranianGateway, PaymentGatewayPreference, ZarinpalGateway
from .models import AdminCardSettings, Wallet, WalletPack, WithdrawalRequest, WalletTopUpLog, CardToCardInstruction, DepositReceipt
from .serializers import (
    AdminCardSettingsSerializer, DepositReceiptSerializer, WalletPackSerializer, 
    WalletSerializer, WalletTopUpSerializer, WithdrawalRequestSerializer, 
    CardToCardInstructionSerializer
)

logger = logging.getLogger(__name__)

# ===================== ای پی ای دریافت موجودی کیف پول =====================
class WalletRetrieveAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="دریافت موجودی کیف پول",
        operation_description="نمایش موجودی کیف پول کاربر جاری.",
        responses={200: WalletSerializer()}
    )
    def get(self, request):
        try:
            wallet = Wallet.objects.get(user=request.user)
        except Wallet.DoesNotExist:
            return Response({"detail": "کیف پول یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

        serializer = WalletSerializer(wallet)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

# ===================== ای پی ای لیست بسته های کیف پول =====================
class WalletPackListAPIView(APIView):
    @swagger_auto_schema(
        operation_summary="دریافت مبالغ پکیج‌های کیف پول",
        responses={200: WalletPackSerializer(many=True)}
    )
    def get(self, request):
        packs = WalletPack.objects.all()
        if not packs.exists():
            return Response({"detail": "هیچ پکیجی ثبت نشده است."}, status=status.HTTP_404_NOT_FOUND)

        serializer = WalletPackSerializer(packs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ===================== ای پی ای افزایش موجودی کیف پول (اصلی) =====================
class CreatePaymentLinkAPIView(APIView):
    permission_classes = [IsAuthenticated]

    REDIRECT_BASE_URL = getattr(settings, 'CALLBACK_REDIRECT_BASE_URL', 'https://safarnameh24.com') + "/dashboard/financial/wallet"
    CALLBACK_PATH = "/api/v1/finance/wallet/payment-callback/"
    
    MIN_TOPUP = 1_000_000
    MAX_TOPUP = 100_000_000

    STATUS_SUCCESS = "success"
    STATUS_FAILURE = "unsuccessfull"

    def get_permissions(self):
        if self.request.method == 'GET' or any(key in self.request.query_params for key in ['Authority', 'order_id', 'status']):
            return [AllowAny()]
        return [IsAuthenticated()]

    def post(self, request, *args, **kwargs):
        logger.info("=" * 100)
        logger.info("=== CREATE PAYMENT REQUEST ===")
        logger.info(f"Content-Type: {request.content_type}")
        logger.info(f"request.data: {dict(request.data) if hasattr(request.data, 'keys') else str(request.data)}")
        logger.info("=" * 100)

        amount = self._extract_amount_robust(request)

        if amount:
            logger.info(f"✅ Amount detected: {amount}")
            return self._handle_create_payment_request(request, amount)
        else:
            logger.warning("No amount → treating as callback")
            return self._handle_payment_callback(request)

    def get(self, request, *args, **kwargs):
        return self._handle_payment_callback(request)

    def _extract_amount_robust(self, request):
        # JSON
        if hasattr(request.data, 'get'):
            val = request.data.get('amount')
            if val is not None:
                try:
                    return int(str(val).strip())
                except:
                    pass
        # Form data
        if hasattr(request.POST, 'get'):
            val = request.POST.get('amount')
            if val is not None:
                try:
                    return int(str(val).strip())
                except:
                    pass
        return None

    def _handle_create_payment_request(self, request, amount_toman):
        serializer = WalletTopUpSerializer(data={'amount': amount_toman})
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        try:
            self._validate_amount(amount_toman)
        except ValidationError as ve:
            return Response(ve.detail, status=400)

        self._store_session(request, wallet_user_id=request.user.id, wallet_amount=amount_toman)

        pref = PaymentGatewayPreference.objects.first()
        if not pref:
            return Response({"error": "Gateway not configured"}, status=500)

        if pref.active_gateway == "zarinpal":
            return self._handle_zarinpal_payment(amount_toman, request)
        elif pref.active_gateway == "iraniangateway":
            return self._handle_iraniangateway_payment(amount_toman, request)

        return Response({"error": "No active gateway found"}, status=500)

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

    def _get_redirect_url(self, status_key, amount=0):
        """ساخت URL ریدایرکت مطابق درخواست شما"""
        return f"{self.REDIRECT_BASE_URL}?payment_status={status_key}&amount={amount}"

    def _handle_payment_callback(self, request):
        authority = request.GET.get("Authority") or request.data.get("Authority")
        status_param = request.GET.get("Status") or request.GET.get("status") or request.data.get("status")
        order_id = request.GET.get("order_id") or request.data.get("order_id")

        logger.info(f"CALLBACK - Authority={authority}, Status={status_param}, Order={order_id}")

        saved_amount = request.session.get("wallet_amount", 0)
        user = self._get_user(request)

        if not user:
            logger.error("User not found in session")
            return HttpResponseRedirect(self._get_redirect_url(self.STATUS_FAILURE, saved_amount))

        # بررسی موفقیت پرداخت
        if authority and str(status_param).upper() == "OK":
            if self._verify_zarinpal(request, user, authority, saved_amount):
                return HttpResponseRedirect(self._get_redirect_url(self.STATUS_SUCCESS, saved_amount))

        if order_id and str(status_param).lower() in ["success", "ok", "1"]:
            if self._verify_iraniangateway(request, user, order_id, saved_amount):
                return HttpResponseRedirect(self._get_redirect_url(self.STATUS_SUCCESS, saved_amount))

        # ناموفق
        self._clear_session(request)
        return HttpResponseRedirect(self._get_redirect_url(self.STATUS_FAILURE, saved_amount))

    def _get_user(self, request):
        if request.user and request.user.is_authenticated:
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

    def _verify_zarinpal(self, request, user, authority, amount_toman):
        try:
            gateway = ZarinpalGateway.objects.first()
            if not gateway:
                return False

            resp = requests.post(
                gateway.verify_url,
                json={
                    "merchant_id": gateway.merchant_code,
                    "amount": amount_toman * 10,
                    "authority": authority
                },
                timeout=20
            )
            data = resp.json().get("data", {})
            if resp.status_code == 200 and data.get("code") == 100:
                self._update_wallet_and_log(user, amount_toman, 'zarinpal', authority)
                self._clear_session(request)
                return True
        except Exception as e:
            logger.error(f"Zarinpal verify error: {e}")
        return False

    def _verify_iraniangateway(self, request, user, order_id, amount_toman):
        try:
            gateway = IranianGateway.objects.first()
            resp = requests.post(
                gateway.verify_url,
                json={"merchant_id": gateway.merchant_code, "order_id": order_id},
                timeout=20
            )
            if resp.status_code == 200 and resp.json().get("success"):
                self._update_wallet_and_log(user, amount_toman, 'iraniangateway', order_id)
                self._clear_session(request)
                return True
        except Exception as e:
            logger.error(f"IranianGateway verify error: {e}")
        return False

    def _update_wallet_and_log(self, user, amount, gateway_name, authority_or_order):
        wallet, _ = Wallet.objects.get_or_create(user=user)
        wallet.balance += amount
        wallet.save()
        WalletTopUpLog.objects.create(
            user=user, amount=amount, gateway=gateway_name, authority_or_order=authority_or_order
        )

    def _handle_zarinpal_payment(self, amount_toman, request):
        gateway = ZarinpalGateway.objects.first()
        try:
            payment_link, authority = self._create_zarinpal_payment(gateway, amount_toman * 10, request)
            return Response({
                "gateway": "zarinpal",
                "amount": amount_toman,
                "payment_link": payment_link
            })
        except Exception as e:
            logger.error(f"Zarinpal create error: {e}")
            return Response({"error": str(e)}, status=500)

    def _create_zarinpal_payment(self, gateway, amount_riel, request):
        base_url = request.build_absolute_uri('/')
        callback_url = urljoin(base_url, self.CALLBACK_PATH.lstrip('/'))

        resp = requests.post(
            gateway.request_url,
            json={
                "merchant_id": gateway.merchant_code,
                "amount": amount_riel,
                "callback_url": callback_url,
                "description": "شارژ کیف پول"
            },
            timeout=30
        )
        res = resp.json()

        if res.get("data") and res["data"].get("authority"):
            auth = res["data"]["authority"]
            return f"{gateway.payment_url}/{auth}", auth

        raise Exception(f"Zarinpal error: {res.get('errors', res)}")

    def _handle_iraniangateway_payment(self, amount_toman, request):
        gateway = IranianGateway.objects.first()
        try:
            payment_link, order_id = self._create_iraniangateway_payment(gateway, amount_toman, request)
            return Response({
                "gateway": "iraniangateway",
                "amount": amount_toman,
                "payment_link": payment_link
            })
        except Exception as e:
            logger.error(f"IranianGateway create error: {e}")
            return Response({"error": str(e)}, status=500)

    def _create_iraniangateway_payment(self, gateway, amount_toman, request):
        base_url = request.build_absolute_uri('/')
        callback_url = urljoin(base_url, self.CALLBACK_PATH.lstrip('/'))

        data = {
            "merchant_id": gateway.merchant_code,
            "amount": amount_toman,
            "callback_url": callback_url,
            "description": "شارژ کیف پول"
        }
        resp = requests.post(gateway.request_url, json=data, timeout=30)
        result = resp.json()

        if result.get("success"):
            return result.get("payment_url"), result.get("order_id")
        raise Exception(result.get('message', 'Iranian gateway error'))

# ===================== سایر ویوها =====================

class AdminCardSettingsAPIView(APIView):
    @swagger_auto_schema(
        operation_summary="دریافت تنظیمات شماره کارت ادمین",
        responses={200: AdminCardSettingsSerializer}
    )
    def get(self, request):
        try:
            setting = AdminCardSettings.objects.get()
        except AdminCardSettings.DoesNotExist:
            return Response({"detail": "تنظیمات یافت نشد."}, status=status.HTTP_404_NOT_FOUND)
        return Response(AdminCardSettingsSerializer(setting).data, status=status.HTTP_200_OK)

class DepositReceiptCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(request_body=DepositReceiptSerializer, operation_summary="ثبت فیش واریزی")
    def post(self, request):
        serializer = DepositReceiptSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class WithdrawalRequestCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(request_body=WithdrawalRequestSerializer, operation_summary="ثبت درخواست برداشت")
    def post(self, request):
        serializer = WithdrawalRequestSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CardToCardInstructionAPIView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        obj = CardToCardInstruction.objects.first()
        if not obj: return Response({"text": ""}, status=status.HTTP_200_OK)
        return Response(CardToCardInstructionSerializer(obj).data, status=status.HTTP_200_OK)

class FinancialOperationsListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(operation_summary="لیست عملیات مالی")
    def get(self, request):
        user = request.user
        page = int(request.GET.get('page', 1) or 1)
        page_size = int(request.GET.get('page_size', 18) or 18)
        
        operations = []
        def to_jalali(dt):
            try: return jdatetime.datetime.fromgregorian(datetime=dt).strftime('%Y/%m/%d')
            except: return ''

        # فیش ها
        for receipt in DepositReceipt.objects.filter(user=user):
            operations.append({
                "type": "card_to_card", "service_type": "کارت به کارت", "amount": int(receipt.amount),
                "status": "success" if receipt.is_approved else "unsuccess",
                "status_display": "موفق" if receipt.is_approved else "ناموفق",
                "date": receipt.deposit_date_jalali, "created_at": receipt.created_at,
            })
        # برداشت ها
        for w in WithdrawalRequest.objects.filter(user=user):
            success = w.status in ["approved", "completed"]
            operations.append({
                "type": "withdrawal", "service_type": "برداشت وجه", "amount": int(w.amount),
                "status": "success" if success else "unsuccess",
                "status_display": "موفق" if success else "ناموفق",
                "date": to_jalali(w.created_at), "created_at": w.created_at,
            })
        # شارژها
        for t in WalletTopUpLog.objects.filter(user=user):
            operations.append({
                "type": "wallet_increase", "service_type": "افزایش کیف پول", "amount": int(t.amount),
                "status": "success", "status_display": "موفق",
                "date": to_jalali(t.created_at), "created_at": t.created_at,
            })

        operations.sort(key=lambda op: op['created_at'], reverse=True)
        for op in operations: del op['created_at']

        total_items = len(operations)
        total_pages = (total_items + page_size - 1) // page_size
        start = (page - 1) * page_size
        return Response({
            "page": page, "page_size": page_size, "total_pages": total_pages,
            "total_items": total_items, "operations": operations[start:start+page_size],
        }, status=status.HTTP_200_OK)