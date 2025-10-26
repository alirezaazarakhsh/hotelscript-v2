from django.shortcuts import get_object_or_404, reverse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.core.cache import cache
from datetime import datetime, timedelta
from django.db import transaction
import logging
import requests
import uuid
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from safarname24 import settings
from .models import PaymentGatewayPreference, ZarinpalGateway, IranianGateway
from reservation.models import Reservationhotel

logger = logging.getLogger(__name__)

try:
    from zeep import Client
except Exception:
    Client = None
    logger.warning("پکیج 'zeep' نصب نشده است؛ فراخوانی زرین‌پال خطا خواهد داد.")

# -------------------------
# Helpers
# -------------------------
def get_active_gateway():
    pref = PaymentGatewayPreference.objects.first()
    if not pref:
        raise ValueError("هیچ درگاه فعالی تنظیم نشده است.")
    return pref.active_gateway

def get_merchant_code(active_gateway):
    if active_gateway == "zarinpal":
        gw = ZarinpalGateway.objects.first()
        if not gw:
            return str(uuid.uuid4())  # UUID تصادفی برای Sandbox
        return gw.merchant_code.strip()
    elif active_gateway == "iraniangateway":
        gw = IranianGateway.objects.first()
        if not gw:
            raise ValueError("مرچنت کد ایران‌درگاه تنظیم نشده است.")
        return gw.merchant_code.strip()
    else:
        raise ValueError(f"درگاه ناشناخته: {active_gateway}")

def cache_payment_link(tracking_code: str, authority: str, link: str, ttl_seconds: int = 1800):
    expires_at_ts = (datetime.now() + timedelta(seconds=ttl_seconds)).timestamp()
    cache.set(f"payment_link_{tracking_code}", {"link": link, "authority": authority, "expires_at": expires_at_ts}, timeout=ttl_seconds)
    cache.set(f"payment_link_authority_{authority}", tracking_code, timeout=ttl_seconds)

def get_tracking_by_authority(authority: str):
    return cache.get(f"payment_link_authority_{authority}")

# -------------------------
# API: ایجاد لینک پرداخت رزرو
# -------------------------
class ReservationPaymentCheckAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="دریافت لینک پرداخت برای رزرو هتل",
        operation_description="""
        این API لینک پرداخت برای رزرو هتل با کد رهگیری مشخص را برمی‌گرداند.
        - نیاز به احراز هویت دارد.
        - کد رهگیری (tracking_code) از URL دریافت می‌شود.
        - اگر رزرو معتبر باشد و لینک پرداخت در کش موجود باشد، همان لینک بازگشت داده می‌شود.
        - در غیر این صورت، لینک پرداخت جدید از درگاه فعال (زرین‌پال یا ایران‌درگاه) تولید می‌شود.
        """,
        responses={
            200: openapi.Response(
                description="لینک پرداخت با موفقیت بازگشت داده شد",
                examples={
                    "application/json": {
                        "payment_link": "https://sandbox.zarinpal.com/pg/StartPay/S123456789"
                    }
                }
            ),
            400: openapi.Response(
                description="خطا در درخواست، مانند رزرو نامعتبر یا درگاه ناشناخته",
                examples={
                    "application/json": {"detail": "رزرو تایید نشده است."}
                }
            ),
            403: openapi.Response(
                description="عدم دسترسی کاربر به رزرو",
                examples={
                    "application/json": {"detail": "شما به این رزرو دسترسی ندارید."}
                }
            ),
            404: openapi.Response(
                description="رزرو یافت نشد",
                examples={
                    "application/json": {"detail": "رزرو پیدا نشد."}
                }
            ),
            500: openapi.Response(
                description="خطای سرور، مانند مشکل در اتصال به درگاه",
                examples={
                    "application/json": {"detail": "خطا در اتصال به درگاه"}
                }
            )
        },
        tags=["reservation-api"]
    )
    def post(self, request, tracking_code):
        reservation = get_object_or_404(Reservationhotel, tracking_code=tracking_code)

        if reservation.buyer != request.user:
            return Response({"detail": "شما به این رزرو دسترسی ندارید."}, status=status.HTTP_403_FORBIDDEN)
        if reservation.capacity_status != 'confirmed':
            return Response({"detail": "رزرو تایید نشده است."}, status=status.HTTP_400_BAD_REQUEST)
        if reservation.final_price <= 0:
            return Response({"payment_link": None}, status=status.HTTP_200_OK)

        payment_data = cache.get(f"payment_link_{tracking_code}")
        if payment_data and payment_data.get("expires_at", 0) > datetime.now().timestamp():
            return Response({"payment_link": payment_data["link"]}, status=status.HTTP_200_OK)

        try:
            active_gateway = get_active_gateway()
            merchant_code = get_merchant_code(active_gateway)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            final_price = int(reservation.final_price)
            callback_url = request.build_absolute_uri(reverse('payment:payment-callback'))

            if active_gateway == 'zarinpal':
                if Client is None:
                    raise RuntimeError("پکیج 'zeep' نصب نشده است (pip install zeep)")
                client = Client('https://sandbox.zarinpal.com/pg/services/WebGate/wsdl')
                result = client.service.PaymentRequest(
                    MerchantID=merchant_code,
                    Amount=final_price,
                    Description=f"پرداخت رزرو {reservation.tracking_code}",
                    CallbackURL=callback_url,
                )
                if getattr(result, "Status", None) == 100:
                    authority = result.Authority
                    payment_link = f"https://sandbox.zarinpal.com/pg/StartPay/{authority}"
                    cache_payment_link(reservation.tracking_code, authority, payment_link)
                    return Response({"payment_link": payment_link}, status=status.HTTP_200_OK)
                else:
                    return Response({"detail": f"خطا در تولید لینک پرداخت (کد وضعیت {getattr(result, 'Status', None)})"}, status=status.HTTP_400_BAD_REQUEST)

            elif active_gateway == 'iraniangateway':
                order_id = reservation.tracking_code
                data = {
                    "merchantID": merchant_code,
                    "amount": final_price,
                    "callbackURL": callback_url,
                    "orderId": order_id
                }
                url = "https://dargaah.ir/payment"
                headers = {
                    "Content-Type": "application/json",
                    "Referer": "https://safarnameh24.com"
                }
                resp = requests.post(url, json=data, headers=headers, timeout=15)
                resp.raise_for_status()
                resp_data = resp.json()

                if resp_data.get("status") != 200:
                    return Response({"detail": resp_data.get("message")}, status=status.HTTP_400_BAD_REQUEST)

                authority = resp_data.get("authority")
                payment_link = f"https://dargaah.ir/ird/startpay/{authority}"
                cache_payment_link(order_id, authority, payment_link)
                return Response({"payment_link": payment_link}, status=status.HTTP_200_OK)

        except requests.exceptions.RequestException as e:
            logger.exception("خطا در اتصال به درگاه")
            return Response({"detail": f"خطا در اتصال به درگاه: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.exception("خطا در تولید لینک پرداخت")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# -------------------------
# API: callback تراکنش
# -------------------------
class PaymentCallbackAPIView(APIView):
    permission_classes = []

    @swagger_auto_schema(
        operation_summary="دریافت callback تراکنش پرداخت",
        operation_description="""
        این API توسط درگاه پرداخت (زرین‌پال یا ایران‌درگاه) برای اعلام نتیجه تراکنش فراخوانی می‌شود.
        - نیازی به احراز هویت ندارد.
        - اطلاعات تراکنش (مانند کد وضعیت و authority) ذخیره شده و نتیجه پرداخت اعلام می‌شود.
        """,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'code': openapi.Schema(type=openapi.TYPE_INTEGER, description='کد وضعیت تراکنش'),
                'authority': openapi.Schema(type=openapi.TYPE_STRING, description='شناسه تراکنش'),
                'orderId': openapi.Schema(type=openapi.TYPE_STRING, description='شناسه سفارش (tracking_code رزرو)'),
                'amount': openapi.Schema(type=openapi.TYPE_INTEGER, description='مبلغ تراکنش')
            }
        ),
        responses={
            200: openapi.Response(
                description="نتیجه تراکنش با موفقیت دریافت شد",
                examples={
                    "application/json": {
                        "status": "success",
                        "detail": "پرداخت موفق، برای تایید نهایی درخواست verification را ارسال کنید."
                    }
                }
            ),
            400: openapi.Response(
                description="تراکنش ناموفق یا نامعتبر",
                examples={
                    "application/json": {
                        "status": "failed",
                        "detail": "پرداخت ناموفق بود"
                    }
                }
            ),
            404: openapi.Response(
                description="رزرو یا تراکنش یافت نشد",
                examples={
                    "application/json": {"detail": "تراکنش نامعتبر"}
                }
            )
        },
        tags=["reservation-api"]
    )
    def post(self, request):
        code = int(request.data.get("code", -2))
        authority = request.data.get("authority")
        order_id = request.data.get("orderId")
        amount = int(request.data.get("amount", 0))

        tracking_code = get_tracking_by_authority(authority)
        if not tracking_code:
            return Response({"detail": "تراکنش نامعتبر"}, status=status.HTTP_400_BAD_REQUEST)

        reservation = get_object_or_404(Reservationhotel, tracking_code=tracking_code)
        reservation.temp_payment_code = code
        reservation.temp_authority = authority
        reservation.save(update_fields=['temp_payment_code', 'temp_authority'])

        if code != 100:
            return Response({"status": "failed", "detail": "پرداخت ناموفق بود"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"status": "success", "detail": "پرداخت موفق، برای تایید نهایی درخواست verification را ارسال کنید."})

# -------------------------
# API: تایید نهایی تراکنش
# -------------------------
class PaymentVerifyAPIView(APIView):
    permission_classes = []

    @swagger_auto_schema(
        operation_summary="تایید نهایی تراکنش پرداخت",
        operation_description="""
        این API برای تایید نهایی تراکنش پرداخت استفاده می‌شود.
        - نیازی به احراز هویت ندارد.
        - اطلاعات تراکنش (مانند authority و orderId) از بدنه درخواست دریافت شده و وضعیت پرداخت بررسی می‌شود.
        - در صورت موفقیت، وضعیت رزرو به 'paid' تغییر کرده و اطلاعات تراکنش ذخیره می‌شود.
        """,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'authority': openapi.Schema(type=openapi.TYPE_STRING, description='شناسه تراکنش'),
                'orderId': openapi.Schema(type=openapi.TYPE_STRING, description='شناسه سفارش (tracking_code رزرو)'),
                'amount': openapi.Schema(type=openapi.TYPE_INTEGER, description='مبلغ تراکنش')
            },
            required=['authority', 'orderId', 'amount']
        ),
        responses={
            200: openapi.Response(
                description="تراکنش با موفقیت تایید شد",
                examples={
                    "application/json": {
                        "status": "success",
                        "refId": "123456789"
                    }
                }
            ),
            400: openapi.Response(
                description="تایید تراکنش ناموفق یا داده‌های نامعتبر",
                examples={
                    "application/json": {
                        "status": "failed",
                        "detail": "تایید تراکنش ناموفق بود: -1"
                    }
                }
            ),
            404: openapi.Response(
                description="رزرو یافت نشد",
                examples={
                    "application/json": {"detail": "رزرو پیدا نشد."}
                }
            ),
            500: openapi.Response(
                description="خطای سرور، مانند مشکل در اتصال به درگاه",
                examples={
                    "application/json": {"detail": "خطا در اتصال به درگاه"}
                }
            )
        },
        tags=["reservation-api"]
    )
    def post(self, request):
        authority = request.data.get("authority")
        order_id = request.data.get("orderId")
        amount = int(request.data.get("amount", 0))

        reservation = get_object_or_404(Reservationhotel, tracking_code=order_id)
        active_gateway = get_active_gateway()
        merchant_code = get_merchant_code(active_gateway)

        try:
            if active_gateway == 'zarinpal':
                if Client is None:
                    return Response({"detail": "پکیج zeep نصب نشده است"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                client = Client('https://sandbox.zarinpal.com/pg/services/WebGate/wsdl')
                result = client.service.PaymentVerification(
                    MerchantID=merchant_code,
                    Authority=authority,
                    Amount=amount
                )
                if getattr(result, "Status", None) in [100, 101]:
                    with transaction.atomic():
                        reservation.payment_status = 'paid'
                        reservation.ref_id = getattr(result, "RefID", None)
                        reservation.save(update_fields=['payment_status', 'ref_id'])
                        cache.delete(f"payment_link_{order_id}")
                        cache.delete(f"payment_link_authority_{authority}")
                    return Response({"status": "success", "refId": getattr(result, "RefID", None)})
                else:
                    return Response({"status": "failed", "detail": f"تایید تراکنش ناموفق بود: {getattr(result, 'Status', None)}"}, status=status.HTTP_400_BAD_REQUEST)

            elif active_gateway == 'iraniangateway':
                data = {
                    "merchantID": merchant_code,
                    "authority": authority,
                    "amount": amount,
                    "orderId": order_id
                }
                url = "https://dargaah.ir/verification"
                headers = {
                    "Content-Type": "application/json",
                    "Referer": getattr(settings, "IRANIANGATEWAY_REFERER", "https://safarnameh24.com")
                }
                resp = requests.post(url, json=data, headers=headers, timeout=15)
                resp.raise_for_status()
                resp_data = resp.json()

                if resp_data.get("status") in [100, 101]:
                    with transaction.atomic():
                        reservation.payment_status = 'paid'
                        reservation.ref_id = resp_data.get("refId")
                        reservation.save(update_fields=['payment_status', 'ref_id'])
                        cache.delete(f"payment_link_{order_id}")
                        cache.delete(f"payment_link_authority_{authority}")
                    return Response({"status": "success", "refId": resp_data.get("refId")})
                else:
                    return Response({"status": "failed", "detail": resp_data.get("message")}, status=status.HTTP_400_BAD_REQUEST)

        except requests.exceptions.RequestException as e:
            logger.exception("خطا در اتصال به درگاه")
            return Response({"detail": f"خطا در اتصال به درگاه: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.exception("خطا در تایید تراکنش")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)