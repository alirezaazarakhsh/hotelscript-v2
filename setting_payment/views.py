from django.shortcuts import get_object_or_404, reverse
from django.http import HttpResponseRedirect
from django.core.exceptions import ValidationError
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.core.cache import cache
from django.db import transaction
from datetime import datetime, timedelta
import logging
import requests
import uuid
import json
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from urllib.parse import urlencode

from safarname24 import settings
from .models import PaymentGatewayPreference, ZarinpalGateway, IranianGateway
from reservation.models import Reservationhotel

logger = logging.getLogger(__name__)

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
            logger.info("تنظیمات زرین‌پال یافت نشد، استفاده از مقادیر پیش‌فرض سندباکس.")
            merchant_code = str(uuid.uuid4())
            return (
                merchant_code,
                'https://sandbox.zarinpal.com/pg/v4/payment/request.json',
                'https://sandbox.zarinpal.com/pg/StartPay',
                'https://sandbox.zarinpal.com/pg/v4/payment/verify.json',
                'sandbox',
                'https://safarnameh24.com/payment/watcher-info'
            )
        logger.info(f"مرچنت‌کد زرین‌پال: {gw.merchant_code}, حالت: {gw.mode}")
        return (
            gw.merchant_code.strip(),
            gw.request_url,
            gw.payment_url,
            gw.verify_url,
            gw.mode,
            gw.callback_redirect_url
        )
    elif active_gateway == "iraniangateway":
        gw = IranianGateway.objects.first()
        if not gw:
            logger.info("تنظیمات ایران‌درگاه یافت نشد، استفاده از مقادیر پیش‌فرض سندباکس.")
            return (
                'TEST',
                'https://dargaah.ir/sandbox/payment',
                'https://dargaah.ir/sandbox/ird/startpay',
                'https://dargaah.ir/sandbox/verification',
                None,
                'https://safarnameh24.com/payment/watcher-info'
            )
        logger.info(f"مرچنت‌کد ایران‌درگاه: {gw.merchant_code}")
        return (
            gw.merchant_code.strip(),
            gw.request_url,
            gw.payment_url,
            gw.verify_url,
            None,
            gw.callback_redirect_url
        )
    else:
        raise ValueError(f"درگاه ناشناخته: {active_gateway}")

def cache_payment_link(tracking_code: str, authority: str, link: str, ttl_seconds: int = 1800):
    expires_at_ts = (datetime.now() + timedelta(seconds=ttl_seconds)).timestamp()
    cache.set(f"payment_link_{tracking_code}", {"link": link, "authority": authority, "expires_at": expires_at_ts}, timeout=ttl_seconds)
    cache.set(f"payment_link_authority_{authority}", tracking_code, timeout=ttl_seconds)
    logger.info(f"لینک پرداخت در کش ذخیره شد: tracking_code={tracking_code}, authority={authority}")

def get_tracking_by_authority(authority: str):
    tracking_code = cache.get(f"payment_link_authority_{authority}")
    logger.info(f"جستجوی tracking_code برای authority={authority}: {tracking_code}")
    return tracking_code

# -------------------------
# Retry-enabled request function
# -------------------------
@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(5),
    retry=retry_if_exception_type(requests.exceptions.RequestException)
)
def make_payment_request(url, data, headers):
    logger.info(f"ارسال درخواست به درگاه: {url}, داده‌ها: {data}")
    resp = requests.post(url, json=data, headers=headers, timeout=10)
    logger.info(f"پاسخ خام از درگاه: {resp.text}")
    resp.raise_for_status()
    return resp

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
        - اگر لینک پرداخت منقضی شده باشد، وضعیت رزرو به unpaid تغییر می‌کند.
        - پاسخ شامل پراپرتی `ok` است که نشان‌دهنده وضعیت معتبر بودن لینک پرداخت است.
        """,
        responses={
            200: openapi.Response(
                description="لینک پرداخت با موفقیت بازگشت داده شد",
                examples={
                    "application/json": {
                        "payment_link": "https://dargaah.ir/sandbox/ird/startpay/20230912094118ZY",
                        "ok": True
                    }
                }
            ),
            400: openapi.Response(description="خطا در درخواست، مانند رزرو نامعتبر یا درگاه ناشناخته"),
            403: openapi.Response(description="عدم دسترسی کاربر به رزرو"),
            404: openapi.Response(description="رزرو یافت نشد"),
            500: openapi.Response(description="خطای سرور، مانند مشکل در اتصال به درگاه")
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
            return Response({"payment_link": None, "ok": False}, status=status.HTTP_200_OK)

        payment_data = cache.get(f"payment_link_{tracking_code}")
        if payment_data:
            if payment_data.get("expires_at", 0) > datetime.now().timestamp():
                logger.info(f"لینک پرداخت معتبر از کش برای {tracking_code}: {payment_data['link']}")
                return Response({"payment_link": payment_data["link"], "ok": True}, status=status.HTTP_200_OK)
            else:
                with transaction.atomic():
                    reservation.payment_status = 'unpaid'
                    reservation.save(update_fields=['payment_status'])
                    logger.info(f"لینک پرداخت برای رزرو {tracking_code} منقضی شده است. وضعیت به unpaid تغییر کرد.")
                cache.delete(f"payment_link_{tracking_code}")
                cache.delete(f"payment_link_authority_{payment_data['authority']}")

        try:
            active_gateway = get_active_gateway()
            merchant_code, request_url, payment_url, verify_url, mode, callback_redirect_url = get_merchant_code(active_gateway)
        except ValueError as e:
            logger.error(f"خطا در دریافت درگاه یا مرچنت‌کد: {str(e)}")
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            final_price = int(reservation.final_price * 10)  # تبدیل تومان به ریال
            if final_price < 10000:
                raise ValueError("مبلغ تراکنش کمتر از 10,000 ریال است.")
            callback_url = request.build_absolute_uri(reverse('payment:payment-callback'))
            logger.info(f"Callback URL: {callback_url}")

            with transaction.atomic():
                reservation.payment_status = 'pending'
                reservation.save(update_fields=['payment_status'])
                logger.info(f"وضعیت رزرو {tracking_code} به pending تغییر کرد برای تولید لینک پرداخت.")

            if active_gateway == 'zarinpal':
                data = {
                    "merchant_id": merchant_code,
                    "amount": final_price,
                    "currency": "IRR",
                    "description": f"پرداخت رزرو {reservation.tracking_code}",
                    "callback_url": callback_url,
                    "metadata": {"order_id": tracking_code}
                }
                headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
                logger.info(f"ارسال درخواست به زرین‌پال (حالت: {mode}): {request_url}")
                resp = make_payment_request(request_url, data, headers)
                try:
                    resp_data = resp.json()
                    logger.info(f"پاسخ زرین‌پال برای تولید لینک: {resp_data}")
                except ValueError:
                    logger.error(f"پاسخ غیر JSON از زرین‌پال: {resp.text}")
                    with transaction.atomic():
                        reservation.payment_status = 'unpaid'
                        reservation.save(update_fields=['payment_status'])
                    return Response(
                        {"detail": f"پاسخ غیر JSON از زرین‌پال: {resp.text}"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )

                if isinstance(resp_data, dict) and resp_data.get("data", {}).get("code") == 100:
                    authority = resp_data["data"].get("authority")
                    if not authority:
                        logger.error(f"پاسخ زرین‌پال فاقد authority است: {resp_data}")
                        with transaction.atomic():
                            reservation.payment_status = 'unpaid'
                            reservation.save(update_fields=['payment_status'])
                        return Response(
                            {"detail": "پاسخ درگاه فاقد authority است"},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    payment_link = f"{payment_url}/{authority}"
                    cache_payment_link(reservation.tracking_code, authority, payment_link)
                    logger.info(f"لینک پرداخت تولید شد: {payment_link}")
                    return Response({"payment_link": payment_link, "ok": True}, status=status.HTTP_200_OK)
                else:
                    logger.error(f"تولید لینک پرداخت زرین‌پال ناموفق: {resp_data}")
                    with transaction.atomic():
                        reservation.payment_status = 'unpaid'
                        reservation.save(update_fields=['payment_status'])
                    return Response(
                        {"detail": f"خطا در تولید لینک پرداخت: {resp_data.get('errors', 'Unknown error')}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            elif active_gateway == 'iraniangateway':
                order_id = reservation.tracking_code
                data = {
                    "merchantID": merchant_code,
                    "amount": final_price,
                    "callbackURL": callback_url,
                    "orderId": order_id,
                    "cardNumber": "1234123412341234" if mode is None and merchant_code == "TEST" else None,
                    "description": f"پرداخت رزرو {tracking_code}"
                }
                headers = {
                    "Content-Type": "application/json",
                    "Referer": "https://safarnameh24.com"
                }
                logger.info(f"ارسال درخواست به ایران‌درگاه: {request_url}, داده‌ها: {data}")
                resp = make_payment_request(request_url, data, headers)
                try:
                    resp_data = resp.json()
                    logger.info(f"پاسخ ایران‌درگاه برای تولید لینک: {resp_data}")
                except ValueError:
                    logger.error(f"پاسخ غیر JSON از ایران‌درگاه: {resp.text}")
                    with transaction.atomic():
                        reservation.payment_status = 'unpaid'
                        reservation.save(update_fields=['payment_status'])
                    return Response(
                        {"detail": f"پاسخ غیر JSON از ایران‌درگاه: {resp.text}"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )

                if isinstance(resp_data, dict) and resp_data.get("status") == 200:
                    authority = resp_data.get("authority")
                    if not authority:
                        logger.error(f"پاسخ ایران‌درگاه فاقد authority است: {resp_data}")
                        with transaction.atomic():
                            reservation.payment_status = 'unpaid'
                            reservation.save(update_fields=['payment_status'])
                        return Response(
                            {"detail": "پاسخ درگاه فاقد authority است"},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    payment_link = f"{payment_url}/{authority}"
                    cache_payment_link(order_id, authority, payment_link)
                    logger.info(f"لینک پرداخت تولید شد: {payment_link}")
                    return Response({"payment_link": payment_link, "ok": True}, status=status.HTTP_200_OK)
                else:
                    logger.error(f"تولید لینک پرداخت ایران‌درگاه ناموفق: {resp_data}")
                    with transaction.atomic():
                        reservation.payment_status = 'unpaid'
                        reservation.save(update_fields=['payment_status'])
                    return Response(
                        {"detail": f"خطا در تولید لینک پرداخت: {resp_data.get('message', 'Unknown error')}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

        except requests.exceptions.RequestException as e:
            with transaction.atomic():
                reservation.payment_status = 'unpaid'
                reservation.save(update_fields=['payment_status'])
            logger.info(f"خطا در اتصال به درگاه برای رزرو {tracking_code}. وضعیت به unpaid تغییر کرد.")
            logger.exception(f"خطا در اتصال به درگاه: {str(e)}")
            return Response(
                {"detail": f"خطا در اتصال به درگاه: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            with transaction.atomic():
                reservation.payment_status = 'unpaid'
                reservation.save(update_fields=['payment_status'])
            logger.info(f"خطا در تولید لینک پرداخت برای رزرو {tracking_code}. وضعیت به unpaid تغییر کرد.")
            logger.exception(f"خطا در تولید لینک پرداخت: {str(e)}")
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
        - برای ایران‌درگاه، اگر code=100 باشد، وضعیت به paid تنظیم می‌شود.
        - در صورت انصراف یا ناموفق بودن پرداخت، وضعیت به unpaid تنظیم می‌شود.
        - اطلاعات تراکنش در کش ذخیره شده و کاربر به آدرس مناسب ریدایرکت می‌شود.
        """,
        manual_parameters=[
            openapi.Parameter('Authority', openapi.IN_QUERY, description="شناسه تراکنش", type=openapi.TYPE_STRING),
            openapi.Parameter('Status', openapi.IN_QUERY, description="وضعیت تراکنش زرین‌پال (OK/NOK)", type=openapi.TYPE_STRING),
            openapi.Parameter('code', openapi.IN_QUERY, description="کد وضعیت تراکنش ایران‌درگاه", type=openapi.TYPE_STRING),
            openapi.Parameter('message', openapi.IN_QUERY, description="پیام وضعیت تراکنش ایران‌درگاه", type=openapi.TYPE_STRING),
            openapi.Parameter('amount', openapi.IN_QUERY, description="مبلغ تراکنش به ریال", type=openapi.TYPE_INTEGER),
            openapi.Parameter('orderId', openapi.IN_QUERY, description="شناسه سفارش", type=openapi.TYPE_STRING),
            openapi.Parameter('refId', openapi.IN_QUERY, description="شناسه ارجاع تراکنش ایران‌درگاه", type=openapi.TYPE_STRING),
        ],
        responses={
            302: openapi.Response(description="ریدایرکت به صفحه مناسب"),
            400: openapi.Response(description="تراکنش ناموفق یا نامعتبر")
        },
        tags=["reservation-api"]
    )
    def get(self, request):
        active_gateway = get_active_gateway()
        merchant_code, request_url, payment_url, verify_url, mode, callback_redirect_url = get_merchant_code(active_gateway)
        authority = request.query_params.get("Authority")
        tracking_code = get_tracking_by_authority(authority)
        if not tracking_code:
            logger.error(f"تراکنش نامعتبر: authority={authority} در کش یافت نشد")
            return Response({"detail": "تراکنش نامعتبر"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            reservation = get_object_or_404(Reservationhotel, tracking_code=tracking_code)
            payment_status = None
            payment_code = None
            ref_id = None

            if active_gateway == 'zarinpal':
                payment_status = request.query_params.get("Status")
                ref_id = request.query_params.get("ref_id")
                if payment_status == "OK":
                    logger.info(f"پرداخت زرین‌پال برای رزرو {tracking_code} موفق بود (Status=OK). انتظار برای تأیید نهایی.")
                else:
                    with transaction.atomic():
                        reservation.payment_status = 'unpaid'
                        reservation.save(update_fields=['payment_status'])
                        logger.info(f"پرداخت زرین‌پال برای رزرو {tracking_code} ناموفق بود یا انصراف داده شد (Status={payment_status}). وضعیت به unpaid تغییر کرد.")

            elif active_gateway == 'iraniangateway':
                payment_code = request.query_params.get("code")
                ref_id = request.query_params.get("refId")
                amount = request.query_params.get("amount")
                message = request.query_params.get("message", "No message provided")
                logger.info(f"Callback ایران‌درگاه: authority={authority}, code={payment_code}, refId={ref_id}, amount={amount}, message={message}")

                if payment_code == "100":
                    with transaction.atomic():
                        reservation.payment_status = 'paid'
                        reservation.ref_id = ref_id if ref_id else f"iraniangateway_{authority}"
                        reservation.save(update_fields=['payment_status', 'ref_id'])
                        logger.info(f"پرداخت ایران‌درگاه برای رزرو {tracking_code} موفق بود (code=100). وضعیت به paid تغییر کرد.")
                else:
                    with transaction.atomic():
                        reservation.payment_status = 'unpaid'
                        reservation.save(update_fields=['payment_status'])
                        logger.info(f"پرداخت ایران‌درگاه برای رزرو {tracking_code} ناموفق بود یا انصراف داده شد (code={payment_code}, message={message}). وضعیت به unpaid تغییر کرد.")

            cache_data = {
                "status": payment_code if active_gateway == 'iraniangateway' else payment_status,
                "tracking_code": tracking_code,
                "payment_code": int(payment_code) if active_gateway == 'iraniangateway' and payment_code and payment_code.isdigit() else (100 if payment_status == "OK" else -2),
                "authority": authority,
                "amount": amount,
                "orderId": request.query_params.get("orderId"),
                "ref_id": ref_id,
                "message": message
            }
            cache.set(f"callback_{authority}", cache_data, timeout=1800)
            logger.info(f"Callback ذخیره شد: {cache_data}")

            query_params = {
            "Authority": authority,
            "Status": payment_status if active_gateway == "zarinpal" else payment_code,
            "tracking-code": tracking_code,
            }
            redirect_url = f"https://safarnameh24.com/payment/watcher-info?{urlencode(query_params)}"
            logger.info(f"ریدایرکت نهایی به: {redirect_url}")
            return HttpResponseRedirect(redirect_url)


        except Exception as e:
            logger.exception(f"خطا در پردازش callback برای authority={authority}: {str(e)}")
            with transaction.atomic():
                reservation.payment_status = 'unpaid'
                reservation.save(update_fields=['payment_status'])
            logger.info(f"خطا در پردازش callback برای رزرو {tracking_code}. وضعیت به unpaid تغییر کرد.")
            return Response({"detail": "خطا در پردازش تراکنش"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# -------------------------
# API: تأیید نهایی تراکنش (اختیاری)
# -------------------------
class PaymentVerifyAPIView(APIView):
    permission_classes = []

    @swagger_auto_schema(
        operation_summary="تأیید نهایی تراکنش پرداخت (اختیاری)",
        operation_description="""
        این API برای تأیید نهایی تراکنش پرداخت استفاده می‌شود و اختیاری است.
        - نیازی به احراز هویت ندارد.
        - اطلاعات تراکنش (مانند authority و orderId) از بدنه درخواست دریافت شده و وضعیت پرداخت بررسی می‌شود.
        - اگر رزرو قبلاً به paid تنظیم شده باشد، همان وضعیت برگردانده می‌شود.
        - در صورت عدم موفقیت، وضعیت رزرو به unpaid تغییر می‌کند.
        """,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'authority': openapi.Schema(type=openapi.TYPE_STRING, description='شناسه تراکنش'),
                'orderId': openapi.Schema(type=openapi.TYPE_STRING, description='شناسه سفارش (tracking_code رزرو)'),
                'amount': openapi.Schema(type=openapi.TYPE_INTEGER, description='مبلغ تراکنش به ریال')
            },
            required=['authority', 'orderId', 'amount']
        ),
        responses={
            200: openapi.Response(description="تراکنش با موفقیت تأیید شد یا قبلاً تأیید شده"),
            400: openapi.Response(description="تأیید تراکنش ناموفق یا داده‌های نامعتبر"),
            404: openapi.Response(description="رزرو یافت نشد"),
            500: openapi.Response(description="خطای سرور، مانند مشکل در اتصال به درگاه")
        },
        tags=["reservation-api"]
    )
    def post(self, request):
        authority = request.data.get("authority")
        order_id = request.data.get("orderId")
        amount = int(request.data.get("amount", 0))

        logger.info(f"درخواست تأیید تراکنش: authority={authority}, order_id={order_id}, amount={amount}")

        reservation = get_object_or_404(Reservationhotel, tracking_code=order_id)
        if reservation.payment_status == 'paid':
            logger.info(f"رزرو {order_id} قبلاً به paid تنظیم شده است. تأیید اضافی لازم نیست.")
            return Response(
                {"status": "success", "refId": reservation.ref_id, "payment_status": "paid"},
                status=status.HTTP_200_OK
            )

        active_gateway = get_active_gateway()
        merchant_code, request_url, payment_url, verify_url, mode, callback_redirect_url = get_merchant_code(active_gateway)

        callback_data = cache.get(f"callback_{authority}")
        logger.info(f"داده‌های کش برای authority={authority}: {callback_data}")
        if not callback_data or not isinstance(callback_data, dict) or callback_data.get("tracking_code") != order_id:
            logger.error(f"داده‌های callback نامعتبر: authority={authority}, order_id={order_id}, callback_data={callback_data}")
            with transaction.atomic():
                reservation.payment_status = 'unpaid'
                reservation.save(update_fields=['payment_status'])
            return Response(
                {"status": "failed", "detail": "داده‌های تراکنش نامعتبر است", "payment_status": "unpaid"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if active_gateway == 'zarinpal' and callback_data.get("status") != "OK":
            logger.error(f"تراکنش زرین‌پال ناموفق: authority={authority}, status={callback_data.get('status')}")
            with transaction.atomic():
                reservation.payment_status = 'unpaid'
                reservation.save(update_fields=['payment_status'])
            return Response(
                {"status": "failed", "detail": f"پرداخت ناموفق بود: {callback_data.get('status')}", "payment_status": "unpaid"},
                status=status.HTTP_400_BAD_REQUEST
            )
        elif active_gateway == 'iraniangateway' and callback_data.get("status") != "100":
            logger.error(f"تراکنش ایران‌درگاه ناموفق: authority={authority}, code={callback_data.get('status')}, message={callback_data.get('message')}")
            with transaction.atomic():
                reservation.payment_status = 'unpaid'
                reservation.save(update_fields=['payment_status'])
            return Response(
                {"status": "failed", "detail": f"پرداخت ناموفق بود: {callback_data.get('status')}", "payment_status": "unpaid"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            if active_gateway == 'zarinpal':
                data = {
                    "merchant_id": merchant_code,
                    "amount": amount,
                    "authority": authority
                }
                headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
                logger.info(f"ارسال درخواست تأیید به زرین‌پال (حالت: {mode}): {verify_url}")
                resp = make_payment_request(verify_url, data, headers)
                try:
                    resp_data = resp.json()
                    logger.info(f"پاسخ تأیید زرین‌پال: {resp_data}")
                except ValueError:
                    logger.error(f"پاسخ غیر JSON از زرین‌پال: {resp.text}")
                    with transaction.atomic():
                        reservation.payment_status = 'unpaid'
                        reservation.save(update_fields=['payment_status'])
                    return Response(
                        {"status": "failed", "detail": f"پاسخ غیر JSON از زرین‌پال: {resp.text}", "payment_status": "unpaid"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                if isinstance(resp_data, dict) and resp_data.get("data", {}).get("code") in [100, 101]:
                    with transaction.atomic():
                        reservation.payment_status = 'paid'
                        reservation.ref_id = resp_data["data"].get("ref_id", callback_data.get("ref_id", f"zarinpal_{authority}"))
                        reservation.save(update_fields=['payment_status', 'ref_id'])
                        cache.delete(f"payment_link_{order_id}")
                        cache.delete(f"payment_link_authority_{authority}")
                        cache.delete(f"callback_{authority}")
                        logger.info(f"پرداخت برای رزرو {order_id} با موفقیت تأیید شد. وضعیت به paid تغییر کرد.")
                    return Response(
                        {"status": "success", "refId": reservation.ref_id, "payment_status": "paid"},
                        status=status.HTTP_200_OK
                    )
                else:
                    logger.error(f"تأیید تراکنش زرین‌پال ناموفق: {resp_data}")
                    with transaction.atomic():
                        reservation.payment_status = 'unpaid'
                        reservation.save(update_fields=['payment_status'])
                    return Response(
                        {"status": "failed", "detail": f"تأیید تراکنش ناموفق بود: {resp_data.get('errors', 'Unknown error')}", "payment_status": "unpaid"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            elif active_gateway == 'iraniangateway':
                data = {
                    "merchantID": merchant_code,
                    "authority": authority,
                    "amount": amount,
                    "orderId": order_id
                }
                headers = {
                    "Content-Type": "application/json",
                    "Referer": "https://safarnameh24.com"
                }
                logger.info(f"ارسال درخواست تأیید به ایران‌درگاه: {verify_url}, داده‌ها: {data}")
                resp = make_payment_request(verify_url, data, headers)
                try:
                    resp_data = resp.json()
                    logger.info(f"پاسخ تأیید ایران‌درگاه: {resp_data}")
                except ValueError:
                    logger.error(f"پاسخ غیر JSON از ایران‌درگاه: {resp.text}")
                    with transaction.atomic():
                        reservation.payment_status = 'unpaid'
                        reservation.save(update_fields=['payment_status'])
                    return Response(
                        {"status": "failed", "detail": f"پاسخ غیر JSON از ایران‌درگاه: {resp.text}", "payment_status": "unpaid"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )

                if isinstance(resp_data, dict) and resp_data.get("status") in [100, 101]:
                    with transaction.atomic():
                        reservation.payment_status = 'paid'
                        reservation.ref_id = resp_data.get("refId", callback_data.get("ref_id", f"iraniangateway_{authority}"))
                        reservation.save(update_fields=['payment_status', 'ref_id'])
                        cache.delete(f"payment_link_{order_id}")
                        cache.delete(f"payment_link_authority_{authority}")
                        cache.delete(f"callback_{authority}")
                        logger.info(f"پرداخت برای رزرو {order_id} با موفقیت تأیید شد. وضعیت به paid تغییر کرد.")
                    return Response(
                        {"status": "success", "refId": reservation.ref_id, "payment_status": "paid"},
                        status=status.HTTP_200_OK
                    )
                else:
                    logger.error(f"تأیید تراکنش ایران‌درگاه ناموفق: {resp_data}")
                    with transaction.atomic():
                        reservation.payment_status = 'unpaid'
                        reservation.save(update_fields=['payment_status'])
                    return Response(
                        {"status": "failed", "detail": f"تأیید تراکنش ناموفق بود: {resp_data.get('message', 'Unknown error')}", "payment_status": "unpaid"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

        except requests.exceptions.RequestException as e:
            with transaction.atomic():
                reservation.payment_status = 'unpaid'
                reservation.save(update_fields=['payment_status'])
            logger.info(f"خطا در اتصال به درگاه برای رزرو {order_id}. وضعیت به unpaid تغییر کرد.")
            logger.exception(f"خطا در اتصال به درگاه: {str(e)}")
            return Response(
                {"status": "failed", "detail": f"خطا در اتصال به درگاه: {str(e)}", "payment_status": "unpaid"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            with transaction.atomic():
                reservation.payment_status = 'unpaid'
                reservation.save(update_fields=['payment_status'])
            logger.info(f"خطا در تأیید تراکنش برای رزرو {order_id}. وضعیت به unpaid تغییر کرد.")
            logger.exception(f"خطا در تأیید تراکنش: {str(e)}")
            return Response(
                {"status": "failed", "detail": str(e), "payment_status": "unpaid"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# -------------------------
# API: وضعیت پرداخت رزرو
# -------------------------
class ReservationPaymentStatusAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="دریافت وضعیت پرداخت رزرو با tracking_code",
        operation_description="این API وضعیت پرداخت رزرو را بر اساس tracking_code برمی‌گرداند.",
        responses={
            200: openapi.Response(description="وضعیت پرداخت رزرو با موفقیت بازگشت داده شد"),
            403: openapi.Response(description="عدم دسترسی به رزرو"),
            404: openapi.Response(description="رزرو یافت نشد")
        },
        tags=["reservation-api"]
    )
    def get(self, request, tracking_code):
        reservation = get_object_or_404(Reservationhotel, tracking_code=tracking_code)

        if reservation.buyer != request.user:
            logger.warning(f"کاربر {request.user.phone_number} به رزرو {tracking_code} دسترسی ندارد.")
            raise ValidationError("شما به این رزرو دسترسی ندارید.")

        response_data = {
            "payment_status": reservation.payment_status,
            "ref_id": reservation.ref_id
        }
        logger.debug(f"ReservationPaymentStatusAPIView response: {response_data}")
        return Response(response_data, status=status.HTTP_200_OK)

# -------------------------
# Celery Task: بررسی لینک‌های پرداخت منقضی‌شده
# -------------------------
from celery import shared_task

@shared_task
def cleanup_expired_payment_links():
    logger.info("شروع بررسی لینک‌های پرداخت منقضی‌شده")
    for key in cache.iter_keys("payment_link_*"):
        payment_data = cache.get(key)
        if payment_data and payment_data.get("expires_at", 0) < datetime.now().timestamp():
            tracking_code = key.replace("payment_link_", "")
            try:
                with transaction.atomic():
                    reservation = Reservationhotel.objects.get(tracking_code=tracking_code)
                    if reservation.payment_status != 'paid':
                        reservation.payment_status = 'unpaid'
                        reservation.save(update_fields=['payment_status'])
                        logger.info(f"رزرو {tracking_code} به دلیل منقضی شدن لینک پرداخت به unpaid تغییر کرد.")
                cache.delete(key)
                cache.delete(f"payment_link_authority_{payment_data['authority']}")
            except Reservationhotel.DoesNotExist:
                logger.warning(f"رزرو با کد {tracking_code} یافت نشد.")
                cache.delete(key)
                cache.delete(f"payment_link_authority_{payment_data['authority']}")
    logger.info("پایان بررسی لینک‌های پرداخت منقضی‌شده")