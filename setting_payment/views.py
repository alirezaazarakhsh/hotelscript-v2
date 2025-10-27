from django.shortcuts import get_object_or_404, reverse
from django.http import HttpResponseRedirect
from django.core.exceptions import ValidationError
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
    """
    دریافت اطلاعات درگاه از دیتابیس.
    برای زرین‌پال: مرچنت‌کد، URLها و حالت درگاه (سندباکس یا پروداکشن) را برمی‌گرداند.
    برای ایران‌درگاه: مرچنت‌کد و URLها را برمی‌گرداند.
    """
    if active_gateway == "zarinpal":
        gw = ZarinpalGateway.objects.first()
        if not gw:
            if gw.mode == 'sandbox':
                merchant_code = str(uuid.uuid4())  # UUID تصادفی برای سندباکس
                logger.info(f"مرچنت‌کد تصادفی برای سندباکس تولید شد: {merchant_code}")
                return (
                    merchant_code,
                    'https://sandbox.zarinpal.com/pg/v4/payment/request.json',
                    'https://sandbox.zarinpal.com/pg/StartPay',
                    'https://sandbox.zarinpal.com/pg/v4/payment/verify.json',
                    'sandbox'
                )
            else:
                raise ValueError("تنظیمات درگاه زرین‌پال برای پروداکشن یافت نشد. لطفاً مرچنت‌کد و URLها را در دیتابیس تنظیم کنید.")
        logger.info(f"مرچنت‌کد زرین‌پال: {gw.merchant_code}, حالت: {gw.mode}")
        return gw.merchant_code.strip(), gw.request_url, gw.payment_url, gw.verify_url, gw.mode
    elif active_gateway == "iraniangateway":
        gw = IranianGateway.objects.first()
        if not gw:
            # برای سندباکس ایران‌درگاه، از TEST استفاده می‌کنیم
            logger.info("تنظیمات ایران‌درگاه یافت نشد، استفاده از مقادیر پیش‌فرض سندباکس.")
            return (
                'TEST',
                'https://dargaah.ir/sandbox/payment',
                'https://dargaah.ir/sandbox/ird/startpay',
                'https://dargaah.ir/sandbox/verification',
                None
            )
        logger.info(f"مرچنت‌کد ایران‌درگاه: {gw.merchant_code}")
        return gw.merchant_code.strip(), gw.request_url, gw.payment_url, gw.verify_url, None
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
    resp = requests.post(url, json=data, headers=headers, timeout=10)  # کاهش timeout به 10 ثانیه
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
                        "payment_link": "https://dargaah.ir/ird/startpay/20230912094118ZY",
                        "ok": True
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
            merchant_code, request_url, payment_url, verify_url, mode = get_merchant_code(active_gateway)
        except ValueError as e:
            logger.error(f"خطا در دریافت درگاه یا مرچنت‌کد: {str(e)}")
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            final_price = int(reservation.final_price * 10)  # تبدیل تومان به ریال
            if final_price < 10000:  # حداقل مبلغ 10,000 ریال
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
                    "currency": "IRR",  # برای زرین‌پال از IRR استفاده می‌کنیم
                    "description": f"پرداخت رزرو {reservation.tracking_code}",
                    "callback_url": callback_url,
                    "metadata": {
                        "order_id": tracking_code
                    }
                }
                headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
                logger.info(f"ارسال درخواست به زرین‌پال (حالت: {mode}): {request_url}")
                resp = make_payment_request(request_url, data, headers)
                resp_data = resp.json()

                logger.info(f"پاسخ زرین‌پال برای تولید لینک: {resp_data}")
                if resp_data.get("data", {}).get("code") == 100:
                    authority = resp_data["data"]["authority"]
                    payment_link = f"{payment_url}/{authority}"
                    cache_payment_link(reservation.tracking_code, authority, payment_link)
                    logger.info(f"لینک پرداخت تولید شد: {payment_link}")
                    return Response({"payment_link": payment_link, "ok": True}, status=status.HTTP_200_OK)
                else:
                    with transaction.atomic():
                        reservation.payment_status = 'unpaid'
                        reservation.save(update_fields=['payment_status'])
                        logger.info(f"تولید لینک پرداخت برای رزرو {tracking_code} ناموفق بود. وضعیت به unpaid تغییر کرد.")
                    return Response({"detail": f"خطا در تولید لینک پرداخت: {resp_data.get('errors', 'Unknown error')}"}, status=status.HTTP_400_BAD_REQUEST)

            elif active_gateway == 'iraniangateway':
                order_id = reservation.tracking_code
                data = {
                    "merchantID": merchant_code,
                    "amount": final_price,
                    "callbackURL": urlencode({'url': callback_url})['url'],  # urlencode کردن callbackURL
                    "orderId": order_id,
                    "cardNumber": "1234123412341234" if mode is None else None,  # فقط برای سندباکس
                    "description": f"پرداخت رزرو {tracking_code}"
                }
                headers = {
                    "Content-Type": "application/json",
                    "Referer": settings.CALLBACK_REDIRECT_BASE_URL
                }
                logger.info(f"ارسال درخواست به ایران‌درگاه: {request_url}, داده‌ها: {data}")
                resp = make_payment_request(request_url, data, headers)
                resp_data = resp.json()

                logger.info(f"پاسخ ایران‌درگاه برای تولید لینک: {resp_data}")
                if resp_data.get("status") == 200:
                    authority = resp_data.get("authority")
                    payment_link = f"{payment_url}/{authority}"
                    cache_payment_link(order_id, authority, payment_link)
                    logger.info(f"لینک پرداخت تولید شد: {payment_link}")
                    return Response({"payment_link": payment_link, "ok": True}, status=status.HTTP_200_OK)
                else:
                    with transaction.atomic():
                        reservation.payment_status = 'unpaid'
                        reservation.save(update_fields=['payment_status'])
                        logger.info(f"تولید لینک پرداخت برای رزرو {tracking_code} ناموفق بود. وضعیت به unpaid تغییر کرد.")
                    return Response({"detail": f"خطا در تولید لینک پرداخت: {resp_data.get('message', 'Unknown error')}"}, status=status.HTTP_400_BAD_REQUEST)

        except requests.exceptions.RequestException as e:
            with transaction.atomic():
                reservation.payment_status = 'unpaid'
                reservation.save(update_fields=['payment_status'])
                logger.info(f"خطا در اتصال به درگاه برای رزرو {tracking_code}. وضعیت به unpaid تغییر کرد.")
            logger.exception(f"خطا در اتصال به درگاه: {str(e)}")
            return Response({"detail": f"خطا در اتصال به درگاه: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
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
        - اطلاعات تراکنش (مانند Status و Authority) از QueryString دریافت شده و در کش ذخیره می‌شود.
        - در صورت ناموفق بودن پرداخت، وضعیت رزرو به unpaid تغییر می‌کند.
        - کاربر به آدرس مناسب ریدایرکت می‌شود.
        """,
        manual_parameters=[
            openapi.Parameter('Authority', openapi.IN_QUERY, description="شناسه تراکنش", type=openapi.TYPE_STRING),
            openapi.Parameter('Status', openapi.IN_QUERY, description="وضعیت تراکنش (OK/NOK)", type=openapi.TYPE_STRING),
            openapi.Parameter('code', openapi.IN_QUERY, description="کد وضعیت تراکنش (برای ایران‌درگاه)", type=openapi.TYPE_INTEGER),
            openapi.Parameter('message', openapi.IN_QUERY, description="پیام وضعیت تراکنش (برای ایران‌درگاه)", type=openapi.TYPE_STRING),
            openapi.Parameter('amount', openapi.IN_QUERY, description="مبلغ تراکنش (برای ایران‌درگاه)", type=openapi.TYPE_INTEGER),
            openapi.Parameter('orderId', openapi.IN_QUERY, description="شناسه سفارش (برای ایران‌درگاه)", type=openapi.TYPE_STRING),
        ],
        responses={
            302: openapi.Response(
                description="ریدایرکت به صفحه مناسب با پارامترهای Authority، Status و tracking-code",
                examples={
                    "application/json": {
                        "redirect_url": "https://safarnameh24.com/payment/watcher-info?Authority=20230912094118ZY&Status=OK&tracking-code=sfa8921378734"
                    }
                }
            ),
            400: openapi.Response(
                description="تراکنش ناموفق یا نامعتبر",
                examples={
                    "application/json": {
                        "detail": "تراکنش نامعتبر"
                    }
                }
            )
        },
        tags=["reservation-api"]
    )
    def get(self, request):
        active_gateway = get_active_gateway()
        authority = request.query_params.get("Authority")
        tracking_code = get_tracking_by_authority(authority)
        if not tracking_code:
            logger.error(f"تراکنش نامعتبر: authority={authority} در کش یافت نشد")
            return Response({"detail": "تراکنش نامعتبر"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            reservation = get_object_or_404(Reservationhotel, tracking_code=tracking_code)
            if active_gateway == 'zarinpal':
                payment_status = request.query_params.get("Status")
                if payment_status == "NOK":
                    with transaction.atomic():
                        reservation.payment_status = 'unpaid'
                        reservation.save(update_fields=['payment_status'])
                        logger.info(f"پرداخت برای رزرو {tracking_code} ناموفق بود (Status=NOK). وضعیت به unpaid تغییر کرد.")
            elif active_gateway == 'iraniangateway':
                payment_code = request.query_params.get("code")
                if payment_code != "100":
                    with transaction.atomic():
                        reservation.payment_status = 'unpaid'
                        reservation.save(update_fields=['payment_status'])
                        logger.info(f"پرداخت برای رزرو {tracking_code} ناموفق بود (code={payment_code}). وضعیت به unpaid تغییر کرد.")

            cache.set(
                f"callback_{authority}",
                {
                    "status": payment_code if active_gateway == 'iraniangateway' else payment_status,
                    "tracking_code": tracking_code,
                    "payment_code": int(payment_code) if active_gateway == 'iraniangateway' else (100 if payment_status == "OK" else -2),
                    "authority": authority,
                    "amount": request.query_params.get("amount"),
                    "orderId": request.query_params.get("orderId")
                },
                timeout=1800
            )
            logger.info(f"Callback ذخیره شد: authority={authority}, status={payment_status or payment_code}, tracking_code={tracking_code}")

            query_params = {
                'Authority': authority,
                'Status': payment_status if active_gateway == 'zarinpal' else payment_code,
                'tracking-code': tracking_code
            }
            redirect_url = f"{settings.CALLBACK_REDIRECT_BASE_URL}/payment/watcher-info?{urlencode(query_params)}"
            logger.info(f"ریدایرکت به: {redirect_url}")
            return HttpResponseRedirect(redirect_url)

        except Exception as e:
            logger.exception(f"خطا در پردازش callback برای authority={authority}: {str(e)}")
            return Response({"detail": "خطا در پردازش تراکنش"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# -------------------------
# API: تأیید نهایی تراکنش
# -------------------------
class PaymentVerifyAPIView(APIView):
    permission_classes = []

    @swagger_auto_schema(
        operation_summary="تأیید نهایی تراکنش پرداخت",
        operation_description="""
        این API برای تأیید نهایی تراکنش پرداخت استفاده می‌شود.
        - نیازی به احراز هویت ندارد.
        - اطلاعات تراکنش (مانند authority و orderId) از بدنه درخواست دریافت شده و وضعیت پرداخت بررسی می‌شود.
        - در صورت موفقیت، وضعیت رزرو به 'paid' تغییر کرده و اطلاعات تراکنش ذخیره می‌شود.
        - در صورت عدم موفقیت، وضعیت رزرو به 'unpaid' تغییر می‌کند.
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
            200: openapi.Response(
                description="تراکنش با موفقیت تأیید شد",
                examples={
                    "application/json": {
                        "status": "success",
                        "refId": "1234567890",
                        "payment_status": "paid"
                    }
                }
            ),
            400: openapi.Response(
                description="تأیید تراکنش ناموفق یا داده‌های نامعتبر",
                examples={
                    "application/json": {
                        "status": "failed",
                        "detail": "تأیید تراکنش ناموفق بود: -1",
                        "payment_status": "unpaid"
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

        logger.info(f"درخواست تأیید تراکنش: authority={authority}, order_id={order_id}, amount={amount}")

        reservation = get_object_or_404(Reservationhotel, tracking_code=order_id)
        active_gateway = get_active_gateway()
        merchant_code, request_url, payment_url, verify_url, mode = get_merchant_code(active_gateway)

        callback_data = cache.get(f"callback_{authority}")
        logger.info(f"داده‌های کش برای authority={authority}: {callback_data}")
        if not callback_data or callback_data["tracking_code"] != order_id:
            logger.error(f"داده‌های callback نامعتبر: authority={authority}, order_id={order_id}")
            with transaction.atomic():
                reservation.payment_status = 'unpaid'
                reservation.save(update_fields=['payment_status'])
                logger.info(f"داده‌های callback برای رزرو {order_id} نامعتبر بود. وضعیت به unpaid تغییر کرد.")
            return Response(
                {"status": "failed", "detail": "داده‌های تراکنش نامعتبر است", "payment_status": "unpaid"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if active_gateway == 'zarinpal' and callback_data["status"] != "OK":
            logger.error(f"تراکنش زرین‌پال ناموفق: authority={authority}, status={callback_data['status']}")
            with transaction.atomic():
                reservation.payment_status = 'unpaid'
                reservation.save(update_fields=['payment_status'])
                logger.info(f"تراکنش برای رزرو {order_id} ناموفق بود. وضعیت به unpaid تغییر کرد.")
            return Response(
                {"status": "failed", "detail": "پرداخت ناموفق بود", "payment_status": "unpaid"},
                status=status.HTTP_400_BAD_REQUEST
            )
        elif active_gateway == 'iraniangateway' and callback_data["status"] != "100":
            logger.error(f"تراکنش ایران‌درگاه ناموفق: authority={authority}, code={callback_data['status']}")
            with transaction.atomic():
                reservation.payment_status = 'unpaid'
                reservation.save(update_fields=['payment_status'])
                logger.info(f"تراکنش برای رزرو {order_id} ناموفق بود. وضعیت به unpaid تغییر کرد.")
            return Response(
                {"status": "failed", "detail": f"پرداخت ناموفق بود: {callback_data['status']}", "payment_status": "unpaid"},
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
                resp_data = resp.json()

                logger.info(f"پاسخ تأیید زرین‌پال: {resp_data}")
                if resp_data.get("data", {}).get("code") in [100, 101]:
                    with transaction.atomic():
                        reservation.payment_status = 'paid'
                        reservation.ref_id = resp_data["data"].get("ref_id")
                        reservation.save(update_fields=['payment_status', 'ref_id'])
                        cache.delete(f"payment_link_{order_id}")
                        cache.delete(f"payment_link_authority_{authority}")
                        cache.delete(f"callback_{authority}")
                        logger.info(f"پرداخت برای رزرو {order_id} با موفقیت تأیید شد. وضعیت به paid تغییر کرد.")
                    return Response(
                        {"status": "success", "refId": resp_data["data"].get("ref_id"), "payment_status": "paid"},
                        status=status.HTTP_200_OK
                    )
                else:
                    with transaction.atomic():
                        reservation.payment_status = 'unpaid'
                        reservation.save(update_fields=['payment_status'])
                        logger.info(f"تأیید تراکنش برای رزرو {order_id} ناموفق بود. وضعیت به unpaid تغییر کرد.")
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
                    "Referer": settings.CALLBACK_REDIRECT_BASE_URL
                }
                logger.info(f"ارسال درخواست تأیید به ایران‌درگاه: {verify_url}, داده‌ها: {data}")
                resp = make_payment_request(verify_url, data, headers)
                resp_data = resp.json()

                logger.info(f"پاسخ تأیید ایران‌درگاه: {resp_data}")
                if resp_data.get("status") in [100, 101]:
                    with transaction.atomic():
                        reservation.payment_status = 'paid'
                        reservation.ref_id = resp_data.get("refId")
                        reservation.save(update_fields=['payment_status', 'ref_id'])
                        cache.delete(f"payment_link_{order_id}")
                        cache.delete(f"payment_link_authority_{authority}")
                        cache.delete(f"callback_{authority}")
                        logger.info(f"پرداخت برای رزرو {order_id} با موفقیت تأیید شد. وضعیت به paid تغییر کرد.")
                    return Response(
                        {"status": "success", "refId": resp_data.get("refId"), "payment_status": "paid"},
                        status=status.HTTP_200_OK
                    )
                else:
                    with transaction.atomic():
                        reservation.payment_status = 'unpaid'
                        reservation.save(update_fields=['payment_status'])
                        logger.info(f"تأیید تراکنش برای رزرو {order_id} ناموفق بود. وضعیت به unpaid تغییر کرد.")
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
        operation_description="""
        این API وضعیت پرداخت رزرو را بر اساس **tracking_code** که در URL ارائه می‌شود، برمی‌گرداند.
        فقط کاربر مالک رزرو می‌تواند به این اطلاعات دسترسی داشته باشد.

        **پارامتر ورودی:**
        - `tracking_code`: کد پیگیری رزرو (در مسیر URL)

        **فیلد خروجی:**
        - `payment_status`: وضعیت پرداخت رزرو (یکی از مقادیر: 'paid', 'unpaid', 'pending')

        **حالات خاص:**
        - اگر رزرو یافت نشود، خطای 404 برگردانده می‌شود.
        - اگر کاربر مالک رزرو نباشد، خطای 403 برگردانده می‌شود.
        """,
        responses={
            200: openapi.Response(
                description="وضعیت پرداخت رزرو با موفقیت بازگشت داده شد",
                examples={
                    "application/json": {
                        "payment_status": "paid"
                    }
                }
            ),
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
            "payment_status": reservation.payment_status
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