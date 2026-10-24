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
from django.utils import timezone
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
from reservation.models import Reservationhotel, Wallet, Passenger, ReservationRoomPassenger
from django.db.models import F

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
                'https://zarvantrip.com/payment/watcher-info'
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
                'https://zarvantrip.com/payment/watcher-info'
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
    if not authority:
        return None
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
                    "Referer": "https://zarvantrip.com"
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
                    authority = resp_data.get("authority") or resp_data.get("Authority")
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
        - درگاه زرین‌پال: اگر Status=OK باشد، پرداخت موفق است.
        - درگاه ایران‌درگاه: اگر code=100 باشد، پرداخت موفق است.
        - در هر حالت (موفق یا ناموفق)، کاربر به آدرس فرانت ریدایرکت می‌شود.
        """,
        manual_parameters=[
            openapi.Parameter('Authority', openapi.IN_QUERY, description="شناسه تراکنش (زرین‌پال)", type=openapi.TYPE_STRING),
            openapi.Parameter('authority', openapi.IN_QUERY, description="شناسه تراکنش (ایران‌درگاه)", type=openapi.TYPE_STRING),
            openapi.Parameter('Status', openapi.IN_QUERY, description="وضعیت تراکنش زرین‌پال (OK/NOK)", type=openapi.TYPE_STRING),
            openapi.Parameter('code', openapi.IN_QUERY, description="کد وضعیت تراکنش ایران‌درگاه", type=openapi.TYPE_STRING),
            openapi.Parameter('message', openapi.IN_QUERY, description="پیام وضعیت تراکنش ایران‌درگاه", type=openapi.TYPE_STRING),
            openapi.Parameter('amount', openapi.IN_QUERY, description="مبلغ تراکنش", type=openapi.TYPE_INTEGER),
            openapi.Parameter('orderId', openapi.IN_QUERY, description="شناسه سفارش", type=openapi.TYPE_STRING),
            openapi.Parameter('refId', openapi.IN_QUERY, description="شناسه ارجاع", type=openapi.TYPE_STRING),
        ],
        responses={302: "ریدایرکت به صفحه مناسب"},
        tags=["reservation-api"]
    )
    def get(self, request):
        try:
            active_gateway = get_active_gateway()
            merchant_code, request_url, payment_url, verify_url, mode, callback_redirect_url = get_merchant_code(active_gateway)

            # --- مهم: پشتیبانی از هر دو حالت Authority و authority ---
            authority = request.query_params.get("Authority") or request.query_params.get("authority")
            # -----------------------------------------------------------

            payment_status = request.query_params.get("Status")
            payment_code = request.query_params.get("code")
            ref_id = request.query_params.get("refId") or request.query_params.get("refid")
            amount = request.query_params.get("amount")
            message = request.query_params.get("message", "")
            order_id = request.query_params.get("orderId")

            logger.info(f"Callback دریافت شد: authority={authority}, Status={payment_status}, code={payment_code}, orderId={order_id}, refId={ref_id}")

            if not authority:
                logger.error("Authority در callback وجود ندارد (نه با A بزرگ و نه با a کوچک).")
                return Response({"detail": "تراکنش نامعتبر: authority وجود ندارد"}, status=status.HTTP_400_BAD_REQUEST)

            tracking_code = get_tracking_by_authority(authority)
            if not tracking_code:
                logger.error(f"تراکنش نامعتبر: authority={authority} در کش یافت نشد")
                return Response({"detail": "تراکنش نامعتبر"}, status=status.HTTP_400_BAD_REQUEST)

            reservation = get_object_or_404(Reservationhotel, tracking_code=tracking_code)

            if active_gateway == "zarinpal":
                if payment_status == "OK":
                    logger.info(f"پرداخت زرین‌پال برای رزرو {tracking_code} موفق بود.")
                    reservation.payment_status = "paid"
                else:
                    logger.info(f"پرداخت زرین‌پال ناموفق بود (Status={payment_status}).")
                    reservation.payment_status = "unpaid"

            elif active_gateway == "iraniangateway":
                if payment_code == "100":
                    logger.info(f"پرداخت ایران‌درگاه برای رزرو {tracking_code} موفق بود (code=100).")
                    reservation.payment_status = "paid"
                    reservation.ref_id = ref_id or f"iraniangateway_{authority}"
                else:
                    logger.info(f"پرداخت ایران‌درگاه ناموفق بود (code={payment_code}, message={message}).")
                    reservation.payment_status = "unpaid"

            with transaction.atomic():
                update_fields = ["payment_status"]
                if ref_id:
                    reservation.ref_id = ref_id
                    update_fields.append("ref_id")
                reservation.save(update_fields=update_fields)
                
                # ارسال نوتیف پرداخت به ادمین‌ها
                from hotel_bot.bot import send_payment_receipt_notification
                from asgiref.sync import async_to_sync
                if reservation.payment_status == 'paid':
                    # محاسبه امتیاز دریافتی
                    total_points = sum(
                        (rr.room.customer_club_points or 0) * rr.quantity
                        for rr in reservation.reservation_rooms.select_related('room').all()
                    )
                    
                    # دریافت امتیاز فعلی کاربر
                    from bashgah_moshtarian.models import CustomerClubPoint
                    try:
                        customer_points = CustomerClubPoint.objects.get(user=reservation.buyer)
                        current_points = customer_points.points
                    except CustomerClubPoint.DoesNotExist:
                        current_points = 0
                    
                    async_to_sync(send_payment_receipt_notification)(
                        reservation.tracking_code,
                        reservation.buyer.phone_number,
                        int(reservation.total_price),
                        int(reservation.total_half_day_charge),
                        int(reservation.wallet_withdrawal_amount),
                        int(reservation.discount),
                        int(reservation.final_price),
                        int(total_points),
                        int(current_points),
                        success=True
                    )
                else:
                    async_to_sync(send_payment_receipt_notification)(
                        reservation.tracking_code,
                        reservation.buyer.phone_number,
                        0, 0, 0, 0,
                        int(reservation.final_price),
                        0, 0,
                        success=False
                    )
                
                # اگر پرداخت موفق بود و کیف پول استفاده شده، آن را پردازش کن
                if reservation.payment_status == 'paid' and reservation.wallet_withdrawal_amount > 0 and not reservation.wallet_withdrawn:
                    try:
                        logger.info(f"🟢 شروع پردازش کیف پول برای رزرو {tracking_code}")
                        wallet = Wallet.objects.select_for_update().get(user=reservation.buyer)
                        withdrawal_amount = int(reservation.wallet_withdrawal_amount)
                        
                        if wallet.balance >= withdrawal_amount:
                            # کم کردن موجودی
                            wallet.balance = F('balance') - withdrawal_amount
                            wallet.save(update_fields=['balance'])
                            
                            # زدن تیک
                            Reservationhotel.objects.filter(pk=reservation.pk).update(wallet_withdrawn=True)
                            
                            logger.info(f"✅ کیف پول پردازش شد: مبلغ {withdrawal_amount} کسر شد و تیک wallet_withdrawn خورد")
                        else:
                            logger.warning(f"⚠️ موجودی کیف پول کافی نیست: {wallet.balance} < {withdrawal_amount}")
                    except Wallet.DoesNotExist:
                        logger.error(f"❌ کیف پول برای کاربر {reservation.buyer.phone_number} یافت نشد")
                    except Exception as e:
                        logger.error(f"❌ خطا در پردازش کیف پول: {e}")
                        import traceback
                        logger.error(traceback.format_exc())

            # ذخیره در کش برای verify
            cache_data = {
                "status": payment_status or payment_code,
                "tracking_code": tracking_code,
                "authority": authority,
                "amount": amount,
                "order_id": order_id,
                "ref_id": ref_id,
                "message": message,
            }
            cache.set(f"callback_{authority}", cache_data, timeout=1800)
            logger.info(f"داده callback ذخیره شد: {cache_data}")

            # ریدایرکت نهایی به فرانت
            query_params = {
                "Authority": authority,  # همیشه با A بزرگ برای فرانت
                "Status": payment_status if active_gateway == "zarinpal" else (payment_code or "NOK"),
                "tracking-code": tracking_code,
            }
            if active_gateway == "iraniangateway":
                query_params["message"] = message
                if ref_id:
                    query_params["refId"] = ref_id

            redirect_url = f"{callback_redirect_url}?{urlencode(query_params)}"
            logger.info(f"ریدایرکت نهایی: {redirect_url}")
            return HttpResponseRedirect(redirect_url)

        except Exception as e:
            logger.exception(f"خطا در پردازش callback: {e}")
            if 'reservation' in locals():
                with transaction.atomic():
                    reservation.payment_status = 'unpaid'
                    reservation.save(update_fields=['payment_status'])
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
            logger.info(f"رزرو {order_id} قبلاً به paid تنظیم شده است.")
            return Response(
                {"status": "success", "refId": reservation.ref_id, "payment_status": "paid"},
                status=status.HTTP_200_OK
            )

        active_gateway = get_active_gateway()
        merchant_code, request_url, payment_url, verify_url, mode, callback_redirect_url = get_merchant_code(active_gateway)

        callback_data = cache.get(f"callback_{authority}")
        logger.info(f"داده‌های کش برای authority={authority}: {callback_data}")
        if not callback_data or not isinstance(callback_data, dict) or callback_data.get("tracking_code") != order_id:
            logger.error(f"داده‌های callback نامعتبر: authority={authority}")
            with transaction.atomic():
                reservation.payment_status = 'unpaid'
                reservation.save(update_fields=['payment_status'])
            return Response(
                {"status": "failed", "detail": "داده‌های تراکنش نامعتبر است", "payment_status": "unpaid"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if active_gateway == 'zarinpal' and callback_data.get("status") != "OK":
            logger.error(f"تراکنش زرین‌پال ناموفق: status={callback_data.get('status')}")
            with transaction.atomic():
                reservation.payment_status = 'unpaid'
                reservation.save(update_fields=['payment_status'])
            return Response(
                {"status": "failed", "detail": f"پرداخت ناموفق بود: {callback_data.get('status')}", "payment_status": "unpaid"},
                status=status.HTTP_400_BAD_REQUEST
            )
        elif active_gateway == 'iraniangateway' and callback_data.get("status") not in ["100", "101"]:
            logger.error(f"تراکنش ایران‌درگاه ناموفق: code={callback_data.get('status')}")
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
                        reservation.ref_id = resp_data["data"].get("ref_id", f"zarinpal_{authority}")
                        reservation.save(update_fields=['payment_status', 'ref_id'])
                        
                        # اضافه کردن مسافران جدید به لیست مسافران کاربر
                        for res_room in reservation.reservation_rooms.all():
                            for passenger in res_room.passengers.filter(passenger_type__in=['primary', 'extra']):
                                if passenger.national_code and passenger.mobile_number:
                                    if not Passenger.objects.filter(user=reservation.buyer, identification_code=passenger.national_code).exists():
                                        try:
                                            Passenger.objects.create(
                                                user=reservation.buyer,
                                                first_name=passenger.first_name,
                                                last_name=passenger.last_name,
                                                identification_code=passenger.national_code,
                                                phone_number=passenger.mobile_number
                                            )
                                            logger.info(f"✅ مسافر {passenger.first_name} {passenger.last_name} به لیست اضافه شد.")
                                        except Exception as e:
                                            logger.error(f"❌ خطا در اضافه کردن مسافر {passenger.first_name} {passenger.last_name}: {e}")
                                    else:
                                        logger.info(f"ℹ️ مسافر {passenger.first_name} {passenger.last_name} قبلاً در لیست وجود دارد.")
                                else:
                                    logger.warning(f"⚠️ مسافر {passenger.first_name} {passenger.last_name} کد ملی یا موبایل ندارد، اضافه نشد.")
                        
                        # پردازش کیف پول
                        if reservation.wallet_withdrawal_amount > 0 and not reservation.wallet_withdrawn:
                            try:
                                logger.info(f"🟢 شروع پردازش کیف پول برای رزرو {reservation.tracking_code}")
                                wallet = Wallet.objects.select_for_update().get(user=reservation.buyer)
                                withdrawal_amount = int(reservation.wallet_withdrawal_amount)
                                
                                if wallet.balance >= withdrawal_amount:
                                    wallet.balance = F('balance') - withdrawal_amount
                                    wallet.save(update_fields=['balance'])
                                    Reservationhotel.objects.filter(pk=reservation.pk).update(wallet_withdrawn=True)
                                    logger.info(f"✅ کیف پول پردازش شد: مبلغ {withdrawal_amount} کسر شد")
                                else:
                                    logger.warning(f"⚠️ موجودی کیف پول کافی نیست")
                            except Exception as e:
                                logger.error(f"❌ خطا در پردازش کیف پول: {e}")
                        
                        cache.delete(f"payment_link_{order_id}")
                        cache.delete(f"payment_link_authority_{authority}")
                        cache.delete(f"callback_{authority}")
                    return Response(
                        {"status": "success", "refId": reservation.ref_id, "payment_status": "paid"},
                        status=status.HTTP_200_OK
                    )
                else:
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
                    "Referer": "https://zarvantrip.com"
                }
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
                        reservation.ref_id = resp_data.get("refId", f"iraniangateway_{authority}")
                        reservation.save(update_fields=['payment_status', 'ref_id'])
                        
                        # اضافه کردن مسافران جدید به لیست مسافران کاربر
                        for res_room in reservation.reservation_rooms.all():
                            for passenger in res_room.passengers.filter(passenger_type__in=['primary', 'extra']):
                                if passenger.national_code and passenger.mobile_number:
                                    if not Passenger.objects.filter(user=reservation.buyer, identification_code=passenger.national_code).exists():
                                        try:
                                            Passenger.objects.create(
                                                user=reservation.buyer,
                                                first_name=passenger.first_name,
                                                last_name=passenger.last_name,
                                                identification_code=passenger.national_code,
                                                phone_number=passenger.mobile_number
                                            )
                                            logger.info(f"✅ مسافر {passenger.first_name} {passenger.last_name} به لیست اضافه شد.")
                                        except Exception as e:
                                            logger.error(f"❌ خطا در اضافه کردن مسافر {passenger.first_name} {passenger.last_name}: {e}")
                                    else:
                                        logger.info(f"ℹ️ مسافر {passenger.first_name} {passenger.last_name} قبلاً در لیست وجود دارد.")
                                else:
                                    logger.warning(f"⚠️ مسافر {passenger.first_name} {passenger.last_name} کد ملی یا موبایل ندارد، اضافه نشد.")
                        
                        # پردازش کیف پول
                        if reservation.wallet_withdrawal_amount > 0 and not reservation.wallet_withdrawn:
                            try:
                                logger.info(f"🟢 شروع پردازش کیف پول برای رزرو {reservation.tracking_code}")
                                wallet = Wallet.objects.select_for_update().get(user=reservation.buyer)
                                withdrawal_amount = int(reservation.wallet_withdrawal_amount)
                                
                                if wallet.balance >= withdrawal_amount:
                                    wallet.balance = F('balance') - withdrawal_amount
                                    wallet.save(update_fields=['balance'])
                                    Reservationhotel.objects.filter(pk=reservation.pk).update(wallet_withdrawn=True)
                                    logger.info(f"✅ کیف پول پردازش شد: مبلغ {withdrawal_amount} کسر شد")
                                else:
                                    logger.warning(f"⚠️ موجودی کیف پول کافی نیست")
                            except Exception as e:
                                logger.error(f"❌ خطا در پردازش کیف پول: {e}")
                        
                        cache.delete(f"payment_link_{order_id}")
                        cache.delete(f"payment_link_authority_{authority}")
                        cache.delete(f"callback_{authority}")
                    return Response(
                        {"status": "success", "refId": reservation.ref_id, "payment_status": "paid"},
                        status=status.HTTP_200_OK
                    )
                else:
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
            logger.exception(f"خطا در اتصال به درگاه: {str(e)}")
            return Response(
                {"status": "failed", "detail": f"خطا در اتصال به درگاه: {str(e)}", "payment_status": "unpaid"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            with transaction.atomic():
                reservation.payment_status = 'unpaid'
                reservation.save(update_fields=['payment_status'])
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
def cancel_unpaid_reservations():
    logger.info("شروع کنسل رزروهای پرداخت نشده بعد از 15 دقیقه")
    fifteen_minutes_ago = timezone.now() - timedelta(minutes=15)
    reservations = Reservationhotel.objects.filter(
        capacity_status='confirmed',
        payment_status__in=['pending', 'unpaid'],
        created_at__lt=fifteen_minutes_ago
    )
    for reservation in reservations:
        with transaction.atomic():
            reservation.capacity_status = 'rejected'
            reservation.save(update_fields=['capacity_status'])
            logger.info(f"رزرو {reservation.tracking_code} به دلیل عدم پرداخت بعد از 15 دقیقه کنسل شد.")
            
            # ارسال نوتیف به ادمین‌ها
            from hotel_bot.config import SUPER_ADMINS, BOT_TOKEN
            notification_text = f"🚫 رزرو {reservation.tracking_code} به دلیل عدم پرداخت بعد از 15 دقیقه کنسل شد.\n👤 کاربر: {reservation.buyer.phone_number}"
            for admin_id in SUPER_ADMINS:
                try:
                    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                    data = {
                        "chat_id": admin_id,
                        "text": notification_text,
                        "parse_mode": "Markdown"
                    }
                    response = requests.post(url, data=data, timeout=10)
                    if response.status_code != 200:
                        logger.error(f"Failed to send notification to {admin_id}: {response.text}")
                except Exception as e:
                    logger.error(f"Error sending notification to {admin_id}: {e}")
    logger.info("پایان کنسل رزروهای پرداخت نشده")