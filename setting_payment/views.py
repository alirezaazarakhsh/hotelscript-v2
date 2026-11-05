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
from urllib.parse import urlencode

from safarname24 import settings
from .models import PaymentGatewayPreference, ZarinpalGateway, IranianGateway
from reservation.models import Reservationhotel, Wallet, Passenger, ReservationRoomPassenger
from django.db.models import F
from celery import shared_task

# ایمپورت متد تایید قطعی اسنپ‌تریپ
from reservation.snapptrip_service import confirm_snapptrip_booking

logger = logging.getLogger(__name__)

# -------------------------
# Helpers
# -------------------------
def get_active_gateway():
    pref = PaymentGatewayPreference.objects.first()
    if not pref:
        raise ValueError("هیچ درگاه فعالی در سامانه تنظیم نشده است.")
    return pref.active_gateway

def get_merchant_code(active_gateway):
    if active_gateway == "zarinpal":
        gw = ZarinpalGateway.objects.first()
        if not gw:
            logger.info("تنظیمات زرین‌پال در دیتابیس یافت نشد، استفاده از مقادیر پیش‌فرض پروداکشن.")
            return (
                'YOUR-ZARINPAL-MERCHANT-CODE',
                'https://payment.zarinpal.com/pg/v4/payment/request.json',
                'https://payment.zarinpal.com/pg/StartPay',
                'https://payment.zarinpal.com/pg/v4/payment/verify.json',
                'production',
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
            logger.info("تنظیمات ایران‌درگاه در دیتابیس یافت نشد.")
            return (
                'TEST',
                'https://dargaah.ir/payment',
                'https://dargaah.ir/ird/startpay',
                'https://dargaah.ir/verification',
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
    if not authority:
        return None
    tracking_code = cache.get(f"payment_link_authority_{authority}")
    logger.info(f"جستجوی tracking_code برای authority={authority}: {tracking_code}")
    return tracking_code

def make_payment_request(url, data, headers):
    logger.info(f"ارسال درخواست به درگاه: {url}, داده‌ها: {data}")
    resp = requests.post(url, json=data, headers=headers, timeout=12)
    logger.info(f"پاسخ درگاه (کد {resp.status_code}): {resp.text}")
    return resp

def save_passengers_for_buyer(reservation):
    """ذخیره خودکار مسافران رزرو در دفترچه مسافران کاربر"""
    if not reservation.buyer:
        return
    try:
        for res_room in reservation.reservation_rooms.all():
            for passenger in res_room.passengers.filter(passenger_type__in=['primary', 'extra']):
                if passenger.national_code and passenger.mobile_number:
                    if not Passenger.objects.filter(user=reservation.buyer, identification_code=passenger.national_code).exists():
                        Passenger.objects.create(
                            user=reservation.buyer,
                            first_name=passenger.first_name,
                            last_name=passenger.last_name,
                            identification_code=passenger.national_code,
                            phone_number=passenger.mobile_number
                        )
    except Exception as e:
        logger.warning(f"خطا در ثبت خودکار مسافر: {e}")

def send_telegram_notification_safely(reservation):
    """ارسال رسید پرداخت به بات تلگرام بدون ایجاد وقفه یا خطا در پرداخت"""
    try:
        from hotel_bot.bot import send_payment_receipt_notification
        from asgiref.sync import async_to_sync
        
        buyer_phone = (
            reservation.buyer.phone_number 
            if reservation.buyer 
            else reservation.reserver_phone_number or "نامشخص"
        )
        total_points = sum(
            (rr.room.customer_club_points or 0) * rr.quantity
            for rr in reservation.reservation_rooms.select_related('room').all()
        )
        current_points = 0
        if reservation.buyer:
            from bashgah_moshtarian.models import CustomerClubPoint
            try:
                customer_points = CustomerClubPoint.objects.get(user=reservation.buyer)
                current_points = customer_points.points
            except Exception:
                current_points = 0

        async_to_sync(send_payment_receipt_notification)(
            reservation.tracking_code,
            buyer_phone,
            int(reservation.total_price or 0),
            int(reservation.total_half_day_charge or 0),
            int(reservation.wallet_withdrawal_amount or 0),
            int(reservation.discount or 0),
            int(reservation.final_price or 0),
            int(total_points),
            int(current_points),
            success=(reservation.payment_status == 'paid')
        )
    except Exception as tg_err:
        logger.warning(f"عدم ارسال نوتیف تلگرام: {tg_err}")


# -------------------------
# API: ایجاد لینک پرداخت رزرو
# -------------------------
class ReservationPaymentCheckAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="دریافت لینک پرداخت برای رزرو هتل",
        responses={
            200: openapi.Response(description="لینک پرداخت با موفقیت تولید شد"),
            400: openapi.Response(description="خطا در مقادیر رزرو یا اتصال درگاه"),
            403: openapi.Response(description="عدم دسترسی به رزرو")
        },
        tags=["reservation-api"]
    )
    def post(self, request, tracking_code):
        reservation = get_object_or_404(Reservationhotel, tracking_code=tracking_code)

        # الصاق رزرو مهمان به کاربر جاری
        if reservation.buyer is None:
            reservation.buyer = request.user
            reservation.save(update_fields=['buyer'])
        elif reservation.buyer != request.user:
            return Response({"detail": "شما به این رزرو دسترسی ندارید."}, status=status.HTTP_403_FORBIDDEN)

        # تایید خودکار ظرفیت برای رزروهای اسنپ (چون در وب‌سرویس اسنپ پیش‌رزرو شده است)
        if getattr(reservation, 'is_snapptrip_reservation', False):
            if reservation.capacity_status != 'confirmed':
                reservation.capacity_status = 'confirmed'
                reservation.save(update_fields=['capacity_status'])
                logger.info(f"✅ ظرفیت رزرو اسنپ {tracking_code} به صورت خودکار تایید شد.")
        elif reservation.capacity_status != 'confirmed':
            return Response({"detail": "رزرو هنوز تایید ظرفیت نشده است."}, status=status.HTTP_400_BAD_REQUEST)

        # خواندن امن مبلغ
        raw_price = reservation.final_price if (reservation.final_price and reservation.final_price > 0) else reservation.total_price
        if not raw_price or raw_price <= 0:
            return Response({"detail": "مبلغ نهایی رزرو نامعتبر است.", "payment_link": None, "ok": False}, status=status.HTTP_400_BAD_REQUEST)

        # بررسی لینک کش شده معتبر
        payment_data = cache.get(f"payment_link_{tracking_code}")
        if payment_data:
            if payment_data.get("expires_at", 0) > datetime.now().timestamp():
                logger.info(f"استفاده از لینک معتبر موجود در کش برای {tracking_code}: {payment_data['link']}")
                return Response({"payment_link": payment_data["link"], "ok": True}, status=status.HTTP_200_OK)
            else:
                cache.delete(f"payment_link_{tracking_code}")
                cache.delete(f"payment_link_authority_{payment_data.get('authority', '')}")

        try:
            active_gateway = get_active_gateway()
            merchant_code, request_url, payment_url, verify_url, mode, callback_redirect_url = get_merchant_code(active_gateway)
        except ValueError as e:
            logger.error(f"خطا در درگاه انتخابی: {str(e)}")
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            final_price_irr = int(raw_price * 10)  # تبدیل تومان به ریال
            if final_price_irr < 10000:
                raise ValueError("مبلغ تراکنش کمتر از حداقل مجاز (۱۰,۰۰۰ ریال) است.")

            # تضمین HTTPS بودن آدرس کال‌بک در پروداکشن
            callback_url = request.build_absolute_uri(reverse('payment:payment-callback'))
            if not getattr(settings, 'DEBUG', False) and callback_url.startswith('http://'):
                callback_url = callback_url.replace('http://', 'https://', 1)

            with transaction.atomic():
                reservation.payment_status = 'pending'
                reservation.save(update_fields=['payment_status'])

            if active_gateway == 'zarinpal':
                data = {
                    "merchant_id": merchant_code,
                    "amount": final_price_irr,
                    "currency": "IRR",
                    "description": f"پرداخت رزرو {reservation.tracking_code}",
                    "callback_url": callback_url,
                    "metadata": {"order_id": str(tracking_code)}
                }
                headers = {"Content-Type": "application/json", "Accept": "application/json"}
                resp = make_payment_request(request_url, data, headers)
                
                try:
                    resp_data = resp.json()
                except Exception:
                    logger.error(f"پاسخ درگاه غیر JSON است: {resp.text}")
                    with transaction.atomic():
                        reservation.payment_status = 'unpaid'
                        reservation.save(update_fields=['payment_status'])
                    return Response({"detail": "پاسخ نامعتبر از درگاه زرین‌پال دریافت شد."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                if isinstance(resp_data, dict) and resp_data.get("data", {}).get("code") == 100:
                    authority = resp_data["data"].get("authority")
                    payment_link = f"{payment_url.rstrip('/')}/{authority}"
                    cache_payment_link(reservation.tracking_code, authority, payment_link)
                    return Response({"payment_link": payment_link, "ok": True}, status=status.HTTP_200_OK)
                else:
                    err_info = resp_data.get('errors') or resp_data
                    logger.error(f"تولید لینک زرین‌پال ناموفق بود: {err_info}")
                    with transaction.atomic():
                        reservation.payment_status = 'unpaid'
                        reservation.save(update_fields=['payment_status'])
                    return Response({"detail": f"خطا در ایجاد تراکنش زرین‌پال: {err_info}"}, status=status.HTTP_400_BAD_REQUEST)

            elif active_gateway == 'iraniangateway':
                order_id = str(reservation.tracking_code)
                data = {
                    "merchantID": merchant_code,
                    "amount": final_price_irr,
                    "callbackURL": callback_url,
                    "orderId": order_id,
                    "cardNumber": "1234123412341234" if mode is None and merchant_code == "TEST" else None,
                    "description": f"پرداخت رزرو {tracking_code}"
                }
                headers = {"Content-Type": "application/json", "Referer": "https://safarnameh24.com"}
                resp = make_payment_request(request_url, data, headers)
                
                try:
                    resp_data = resp.json()
                except Exception:
                    logger.error(f"پاسخ غیر JSON از ایران‌درگاه: {resp.text}")
                    with transaction.atomic():
                        reservation.payment_status = 'unpaid'
                        reservation.save(update_fields=['payment_status'])
                    return Response({"detail": "پاسخ نامعتبر از ایران‌درگاه دریافت شد."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                if isinstance(resp_data, dict) and resp_data.get("status") == 200:
                    authority = resp_data.get("authority") or resp_data.get("Authority")
                    payment_link = f"{payment_url.rstrip('/')}/{authority}"
                    cache_payment_link(order_id, authority, payment_link)
                    return Response({"payment_link": payment_link, "ok": True}, status=status.HTTP_200_OK)
                else:
                    err_info = resp_data.get('message') or resp_data
                    logger.error(f"خطای ایران‌درگاه: {err_info}")
                    with transaction.atomic():
                        reservation.payment_status = 'unpaid'
                        reservation.save(update_fields=['payment_status'])
                    return Response({"detail": f"خطا در ایجاد تراکنش ایران‌درگاه: {err_info}"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.exception(f"خطا در تولید لینک پرداخت: {str(e)}")
            with transaction.atomic():
                reservation.payment_status = 'unpaid'
                reservation.save(update_fields=['payment_status'])
            return Response({"detail": f"خطا در سیستم پرداخت: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# -------------------------
# API: Callback تراکنش
# -------------------------
class PaymentCallbackAPIView(APIView):
    permission_classes = []

    def get(self, request):
        try:
            active_gateway = get_active_gateway()
            merchant_code, request_url, payment_url, verify_url, mode, callback_redirect_url = get_merchant_code(active_gateway)

            authority = request.query_params.get("Authority") or request.query_params.get("authority")
            payment_status = request.query_params.get("Status")
            payment_code = request.query_params.get("code")
            ref_id = request.query_params.get("refId") or request.query_params.get("refid")
            amount = request.query_params.get("amount")
            message = request.query_params.get("message", "")
            order_id = request.query_params.get("orderId")

            logger.info(f"Callback دریافت شد: authority={authority}, Status={payment_status}, code={payment_code}, orderId={order_id}")

            if not authority:
                return Response({"detail": "تراکنش نامعتبر: authority وجود ندارد"}, status=status.HTTP_400_BAD_REQUEST)

            tracking_code = get_tracking_by_authority(authority)
            if not tracking_code:
                return Response({"detail": "تراکنش منقضی یا نامعتبر است"}, status=status.HTTP_400_BAD_REQUEST)

            reservation = get_object_or_404(Reservationhotel, tracking_code=tracking_code)

            is_success = False
            if active_gateway == "zarinpal" and payment_status == "OK":
                is_success = True
            elif active_gateway == "iraniangateway" and payment_code in ["100", "101"]:
                is_success = True

            with transaction.atomic():
                update_fields = ["payment_status"]
                if is_success:
                    reservation.payment_status = "paid"
                    if ref_id:
                        reservation.ref_id = ref_id
                        update_fields.append("ref_id")
                    elif not reservation.ref_id:
                        reservation.ref_id = f"{active_gateway}_{authority}"
                        update_fields.append("ref_id")
                else:
                    reservation.payment_status = "unpaid"

                reservation.save(update_fields=update_fields)

                if is_success:
                    # ۱. تایید قطعی در اسنپ‌تریپ
                    if getattr(reservation, 'is_snapptrip_reservation', False) and getattr(reservation, 'snapp_reservation_code', None):
                        try:
                            logger.info(f"🚀 در حال تایید قطعی رزرو اسنپ {reservation.snapp_reservation_code}...")
                            confirm_ok, final_snapp_status, confirm_msg = confirm_snapptrip_booking(reservation.snapp_reservation_code)
                            reservation.snapp_status = str(final_snapp_status)[:40]
                            reservation.save(update_fields=['snapp_status'])
                            logger.info(f"✅ نتیجه تایید در اسنپ: {confirm_msg} ({final_snapp_status})")
                        except Exception as snapp_err:
                            logger.error(f"❌ خطا در تایید رزرو اسنپ: {snapp_err}")

                    # ۲. کسر از کیف پول سایت
                    if (reservation.wallet_withdrawal_amount and reservation.wallet_withdrawal_amount > 0 
                        and not reservation.wallet_withdrawn and reservation.buyer):
                        try:
                            wallet = Wallet.objects.select_for_update().get(user=reservation.buyer)
                            withdrawal_amount = int(reservation.wallet_withdrawal_amount)
                            if wallet.balance >= withdrawal_amount:
                                wallet.balance = F('balance') - withdrawal_amount
                                wallet.save(update_fields=['balance'])
                                Reservationhotel.objects.filter(pk=reservation.pk).update(wallet_withdrawn=True)
                                logger.info(f"✅ کیف پول سایت کسر شد: {withdrawal_amount}")
                        except Exception as e:
                            logger.error(f"❌ خطا در کسر کیف پول: {e}")

                    # ۳. ثبت مسافران رزرو در دفترچه مسافرین کاربر
                    save_passengers_for_buyer(reservation)

                    # ۴. ارسال نوتیفیکیشن تلگرام
                    send_telegram_notification_safely(reservation)

            cache_data = {
                "status": payment_status or payment_code,
                "tracking_code": tracking_code,
                "authority": authority,
                "amount": amount,
                "order_id": order_id,
                "ref_id": ref_id or reservation.ref_id,
                "message": message,
            }
            cache.set(f"callback_{authority}", cache_data, timeout=1800)

            query_params = {
                "Authority": authority,
                "Status": "OK" if is_success else (payment_code or "NOK"),
                "tracking-code": tracking_code,
            }
            if active_gateway == "iraniangateway":
                query_params["message"] = message
            if ref_id or reservation.ref_id:
                query_params["refId"] = ref_id or reservation.ref_id

            redirect_url = f"{callback_redirect_url}?{urlencode(query_params)}"
            return HttpResponseRedirect(redirect_url)

        except Exception as e:
            logger.exception(f"خطا در پردازش Callback: {e}")
            if 'callback_redirect_url' in locals() and 'authority' in locals():
                err_query = urlencode({"Authority": authority or "", "Status": "NOK", "tracking-code": tracking_code or ""})
                return HttpResponseRedirect(f"{callback_redirect_url}?{err_query}")
            return Response({"detail": "خطا در پردازش تراکنش"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# -------------------------
# API: تأیید نهایی تراکنش (Verify در صورت فراخوانی از فرانت)
# -------------------------
class PaymentVerifyAPIView(APIView):
    permission_classes = []

    def post(self, request):
        authority = request.data.get("authority")
        order_id = request.data.get("orderId")
        amount = int(request.data.get("amount", 0))

        reservation = get_object_or_404(Reservationhotel, tracking_code=order_id)
        if reservation.payment_status == 'paid':
            return Response(
                {"status": "success", "refId": reservation.ref_id, "payment_status": "paid"},
                status=status.HTTP_200_OK
            )

        active_gateway = get_active_gateway()
        merchant_code, request_url, payment_url, verify_url, mode, callback_redirect_url = get_merchant_code(active_gateway)

        callback_data = cache.get(f"callback_{authority}")
        if not callback_data or callback_data.get("tracking_code") != order_id:
            with transaction.atomic():
                reservation.payment_status = 'unpaid'
                reservation.save(update_fields=['payment_status'])
            return Response(
                {"status": "failed", "detail": "داده‌های تراکنش نامعتبر است", "payment_status": "unpaid"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            if active_gateway == 'zarinpal':
                data = {
                    "merchant_id": merchant_code,
                    "amount": amount,
                    "authority": authority
                }
                headers = {"Content-Type": "application/json", "Accept": "application/json"}
                resp = make_payment_request(verify_url, data, headers)
                resp_data = resp.json()

                if isinstance(resp_data, dict) and resp_data.get("data", {}).get("code") in [100, 101]:
                    with transaction.atomic():
                        reservation.payment_status = 'paid'
                        reservation.ref_id = resp_data["data"].get("ref_id", f"zarinpal_{authority}")
                        reservation.save(update_fields=['payment_status', 'ref_id'])

                        # تایید اسنپ
                        if getattr(reservation, 'is_snapptrip_reservation', False) and getattr(reservation, 'snapp_reservation_code', None):
                            try:
                                _, final_stat, _ = confirm_snapptrip_booking(reservation.snapp_reservation_code)
                                reservation.snapp_status = str(final_stat)[:40]
                                reservation.save(update_fields=['snapp_status'])
                            except Exception:
                                pass

                        save_passengers_for_buyer(reservation)

                        if reservation.buyer and reservation.wallet_withdrawal_amount > 0 and not reservation.wallet_withdrawn:
                            try:
                                wallet = Wallet.objects.select_for_update().get(user=reservation.buyer)
                                withdrawal_amount = int(reservation.wallet_withdrawal_amount)
                                if wallet.balance >= withdrawal_amount:
                                    wallet.balance = F('balance') - withdrawal_amount
                                    wallet.save(update_fields=['balance'])
                                    Reservationhotel.objects.filter(pk=reservation.pk).update(wallet_withdrawn=True)
                            except Exception:
                                pass

                        cache.delete(f"payment_link_{order_id}")
                        cache.delete(f"payment_link_authority_{authority}")
                        cache.delete(f"callback_{authority}")

                    return Response({"status": "success", "refId": reservation.ref_id, "payment_status": "paid"}, status=status.HTTP_200_OK)
                else:
                    with transaction.atomic():
                        reservation.payment_status = 'unpaid'
                        reservation.save(update_fields=['payment_status'])
                    return Response({"status": "failed", "detail": "تأیید تراکنش زرین‌پال ناموفق بود", "payment_status": "unpaid"}, status=status.HTTP_400_BAD_REQUEST)

            elif active_gateway == 'iraniangateway':
                data = {
                    "merchantID": merchant_code,
                    "authority": authority,
                    "amount": amount,
                    "orderId": order_id
                }
                headers = {"Content-Type": "application/json", "Referer": "https://safarnameh24.com"}
                resp = make_payment_request(verify_url, data, headers)
                resp_data = resp.json()

                if isinstance(resp_data, dict) and resp_data.get("status") in [100, 101]:
                    with transaction.atomic():
                        reservation.payment_status = 'paid'
                        reservation.ref_id = resp_data.get("refId", f"iraniangateway_{authority}")
                        reservation.save(update_fields=['payment_status', 'ref_id'])

                        # تایید اسنپ
                        if getattr(reservation, 'is_snapptrip_reservation', False) and getattr(reservation, 'snapp_reservation_code', None):
                            try:
                                _, final_stat, _ = confirm_snapptrip_booking(reservation.snapp_reservation_code)
                                reservation.snapp_status = str(final_stat)[:40]
                                reservation.save(update_fields=['snapp_status'])
                            except Exception:
                                pass

                        save_passengers_for_buyer(reservation)

                        if reservation.buyer and reservation.wallet_withdrawal_amount > 0 and not reservation.wallet_withdrawn:
                            try:
                                wallet = Wallet.objects.select_for_update().get(user=reservation.buyer)
                                withdrawal_amount = int(reservation.wallet_withdrawal_amount)
                                if wallet.balance >= withdrawal_amount:
                                    wallet.balance = F('balance') - withdrawal_amount
                                    wallet.save(update_fields=['balance'])
                                    Reservationhotel.objects.filter(pk=reservation.pk).update(wallet_withdrawn=True)
                            except Exception:
                                pass

                        cache.delete(f"payment_link_{order_id}")
                        cache.delete(f"payment_link_authority_{authority}")
                        cache.delete(f"callback_{authority}")

                    return Response({"status": "success", "refId": reservation.ref_id, "payment_status": "paid"}, status=status.HTTP_200_OK)
                else:
                    with transaction.atomic():
                        reservation.payment_status = 'unpaid'
                        reservation.save(update_fields=['payment_status'])
                    return Response({"status": "failed", "detail": "تأیید تراکنش ایران‌درگاه ناموفق بود", "payment_status": "unpaid"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.exception(f"خطا در تأیید تراکنش: {str(e)}")
            with transaction.atomic():
                reservation.payment_status = 'unpaid'
                reservation.save(update_fields=['payment_status'])
            return Response({"status": "failed", "detail": str(e), "payment_status": "unpaid"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# -------------------------
# API: وضعیت پرداخت رزرو
# -------------------------
class ReservationPaymentStatusAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, tracking_code):
        reservation = get_object_or_404(Reservationhotel, tracking_code=tracking_code)

        if reservation.buyer is None:
            reservation.buyer = request.user
            reservation.save(update_fields=['buyer'])
        elif reservation.buyer != request.user:
            logger.warning(f"کاربر {request.user.phone_number} به رزرو {tracking_code} دسترسی ندارد.")
            raise ValidationError("شما به این رزرو دسترسی ندارید.")

        return Response({
            "payment_status": reservation.payment_status,
            "ref_id": reservation.ref_id
        }, status=status.HTTP_200_OK)


# -------------------------
# Celery Task: کنسل کردن رزروهای پرداخت نشده بعد از ۱۵ دقیقه
# -------------------------
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
            
            try:
                from hotel_bot.config import SUPER_ADMINS, BOT_TOKEN
                buyer_phone = (
                    reservation.buyer.phone_number 
                    if reservation.buyer 
                    else reservation.reserver_phone_number or "مهمان"
                )
                notification_text = f"🚫 رزرو {reservation.tracking_code} به دلیل عدم پرداخت بعد از 15 دقیقه کنسل شد.\n👤 کاربر: {buyer_phone}"
                for admin_id in SUPER_ADMINS:
                    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                    data = {
                        "chat_id": admin_id,
                        "text": notification_text,
                        "parse_mode": "Markdown"
                    }
                    requests.post(url, data=data, timeout=5)
            except Exception as e:
                logger.warning(f"عدم ارسال پیام تلگرام برای کنسلی رزرو: {e}")
    logger.info("پایان کنسل رزروهای پرداخت نشده")