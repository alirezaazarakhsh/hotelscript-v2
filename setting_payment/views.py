# setting_payment/views.py
from django.shortcuts import get_object_or_404, reverse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import logging
from reservation.models import Reservationhotel
from decimal import Decimal
from django.core.cache import cache
from datetime import datetime, timedelta
from django.db import transaction

# مدل‌های درگاه شما
from .models import PaymentGatewayPreference, ZarinpalGateway, IranianGateway

logger = logging.getLogger(__name__)

# تلاش برای import zeep با پیام مفید
try:
    from zeep import Client  # SOAP client برای زرین‌پال
except Exception as e:
    Client = None
    logger.warning("پکیج 'zeep' نصب نشده است؛ فراخوانی زرین‌پال خطا خواهد داد. نصب با: pip install zeep")


# -------------------------
# Helpers
# -------------------------
def get_active_gateway():
    """
    برمی‌گرداند: رشتهٔ نام درگاه فعال: 'zarinpal' یا 'iraniangateway'
    درصورت نبودنِ تنظیم مناسب ValidationError برمی‌گرداند.
    """
    pref = PaymentGatewayPreference.objects.first()
    if not pref:
        raise ValidationError({"detail": "هیچ درگاه فعالی تنظیم نشده است.", "error_code": "no_active_gateway"})
    return pref.active_gateway


def get_merchant_code(active_gateway):
    """
    از روی active_gateway مرچنت کد متناظر را از جدول مربوطه برمی‌دارد.
    """
    if active_gateway == "zarinpal":
        gw = ZarinpalGateway.objects.first()
        if not gw:
            raise ValidationError({"detail": "مرچنت کد زرین‌پال تنظیم نشده است.", "error_code": "missing_merchant"})
        return gw.merchant_code
    elif active_gateway == "iraniangateway":
        gw = IranianGateway.objects.first()
        if not gw:
            raise ValidationError({"detail": "مرچنت کد ایران درگاه تنظیم نشده است.", "error_code": "missing_merchant"})
        return gw.merchant_code
    else:
        raise ValidationError({"detail": f"درگاه ناشناخته: {active_gateway}", "error_code": "unknown_gateway"})


def cache_payment_link(tracking_code: str, authority: str, link: str, ttl_seconds: int = 1800):
    """
    ذخیرهٔ دو کلید در کش:
    - payment_link_<tracking_code> -> {link, authority, expires_at}
    - payment_link_authority_<authority> -> tracking_code
    این کار باعث می‌شود که هنگام callback نیازی به پیمایش کل کش نباشد.
    """
    expires_at_ts = (datetime.now() + timedelta(seconds=ttl_seconds)).timestamp()
    cache.set(f"payment_link_{tracking_code}", {
        "link": link,
        "authority": authority,
        "expires_at": expires_at_ts
    }, timeout=ttl_seconds)
    cache.set(f"payment_link_authority_{authority}", tracking_code, timeout=ttl_seconds)


def get_tracking_by_authority(authority: str):
    """
    مستقیم از کش می‌خواند که برای این authority چه tracking_code‌ای ثبت شده.
    """
    return cache.get(f"payment_link_authority_{authority}")


# -------------------------
# API: دریافت لینک پرداخت رزرو
# -------------------------
class ReservationPaymentCheckAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="دریافت لینک پرداخت رزرو",
        operation_description="""
بررسی رزرو بر اساس tracking_code و تولید لینک پرداخت (زرین‌پال یا ایران‌درگاه) در صورت نیاز.
- لینک پس از 30 دقیقه منقضی می‌شود.
- کاربر باید مالک رزرو باشد، رزرو باید confirmed باشد.
""",
        manual_parameters=[
            openapi.Parameter('tracking_code', openapi.IN_PATH, description="کد پیگیری رزرو", type=openapi.TYPE_STRING),
        ],
        responses={
            200: openapi.Response(
                description="لینک پرداخت یا null",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'payment_link': openapi.Schema(type=openapi.TYPE_STRING, nullable=True)
                    }
                )
            ),
            400: openapi.Response(description="خطا در درخواست"),
            403: openapi.Response(description="دسترسی مجاز نیست"),
            404: openapi.Response(description="رزرو یافت نشد")
        },
        tags=["reservation-api"]
    )
    def get(self, request, tracking_code):
        # 1. پیدا کردن رزرو
        reservation = get_object_or_404(Reservationhotel, tracking_code=tracking_code)

        # 2. بررسی مالکیت
        if reservation.buyer != request.user:
            logger.warning(f"User {getattr(request.user, 'id', request.user)} tried to access reservation {tracking_code}")
            return Response({"detail": "شما به این رزرو دسترسی ندارید.", "error_code": "access_denied"}, status=status.HTTP_403_FORBIDDEN)

        # 3. بررسی وضعیت
        if reservation.capacity_status != 'confirmed':
            return Response({
                "detail": "رزرو هنوز تأیید نشده است.",
                "error_code": "reservation_not_confirmed",
                "current_status": reservation.capacity_status
            }, status=status.HTTP_400_BAD_REQUEST)

        # 4. اگر قیمت صفر است
        if reservation.final_price == Decimal('0'):
            return Response({"payment_link": None}, status=status.HTTP_200_OK)

        # 5. بررسی کش (اگر لینک قبلا ساخته شده و هنوز معتبر است)
        payment_data = cache.get(f"payment_link_{tracking_code}")
        if payment_data and payment_data.get("expires_at", 0) > datetime.now().timestamp():
            return Response({"payment_link": payment_data["link"]}, status=status.HTTP_200_OK)
        elif payment_data:
            # لینک وجود دارد اما منقضی شده
            cache.delete(f"payment_link_{tracking_code}")
            # هرچند cache_payment_link_authority هم حذف شده باشد، سعی می‌کنیم آن را هم پاک کنیم:
            if "authority" in payment_data:
                cache.delete(f"payment_link_authority_{payment_data['authority']}")
            return Response({"detail": "لینک پرداخت منقضی شده است. لطفاً دوباره تلاش کنید.", "error_code": "payment_link_expired"}, status=status.HTTP_400_BAD_REQUEST)

        # 6. خواندن درگاه فعال و مرچنت از دیتابیس
        try:
            active_gateway = get_active_gateway()
            merchant_code = get_merchant_code(active_gateway)
        except ValidationError as e:
            # e ممکن است dict داشته باشد
            payload = e.message_dict if hasattr(e, "message_dict") else {"detail": str(e)}
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

        # 7. تولید لینک براساس درگاه
        try:
            if active_gateway == 'zarinpal':
                # برای زرین‌پال از SOAP API استفاده می‌شود (zeep)
                if Client is None:
                    raise RuntimeError("پکیج 'zeep' نصب نشده است (pip install zeep)")

                final_price = int(reservation.final_price)
                # callback را با استفاده از reverse بسازیم تا همیشه درست باشد
                callback_path = reverse('payment:payment-callback')  # نیازمند app_name='payment' در urls.py
                callback_url = request.build_absolute_uri(callback_path)

                client = Client('https://www.zarinpal.com/pg/services/WebGate/wsdl')
                result = client.service.PaymentRequest(
                    MerchantID=merchant_code,
                    Amount=final_price,
                    Description=f"پرداخت رزرو {reservation.tracking_code}",
                    CallbackURL=callback_url,
                )

                if getattr(result, "Status", None) == 100:
                    authority = result.Authority
                    payment_link = f"https://www.zarinpal.com/pg/StartPay/{authority}"
                    cache_payment_link(reservation.tracking_code, authority, payment_link, ttl_seconds=1800)
                    logger.info(f"Zarinpal link created for {reservation.tracking_code} authority={authority}")
                    return Response({"payment_link": payment_link}, status=status.HTTP_200_OK)
                else:
                    logger.error(f"Zarinpal PaymentRequest failed: {getattr(result, 'Status', None)}")
                    return Response({"detail": f"خطا در تولید لینک پرداخت (کد وضعیت {getattr(result, 'Status', None)})"}, status=status.HTTP_400_BAD_REQUEST)

            elif active_gateway == 'iraniangateway':
                # نمونهٔ ساده: (در عمل باید API واقعی ایران درگاه را پیاده کنید)
                final_price = int(reservation.final_price)
                # در ایران‌درگاه فرض می‌کنیم authority همان tracking_code است (یا شناسه تراکنش برمی‌گردد)
                authority = reservation.tracking_code
                payment_link = f"https://iraniangateway.ir/pay/{reservation.tracking_code}?amount={final_price}&merchant={merchant_code}"
                cache_payment_link(reservation.tracking_code, authority, payment_link, ttl_seconds=1800)
                logger.info(f"IranianGateway (mock) link created for {reservation.tracking_code}")
                return Response({"payment_link": payment_link}, status=status.HTTP_200_OK)

            else:
                return Response({"detail": f"درگاه فعال ناشناخته است: {active_gateway}"}, status=status.HTTP_400_BAD_REQUEST)

        except ValidationError as e:
            payload = e.message_dict if hasattr(e, "message_dict") else {"detail": str(e)}
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("خطا در تولید لینک پرداخت")
            return Response({"detail": f"خطا در تولید لینک پرداخت: {str(e)}", "error_code": "payment_generation_error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# -------------------------
# API: callback بررسی نتیجه پرداخت
# -------------------------
class PaymentCallbackAPIView(APIView):
    permission_classes = []  # درگاه پرداخت این endpoint را فراخوانی می‌کند؛ نیازی به auth نیست

    @swagger_auto_schema(
        operation_summary="بررسی نتیجه پرداخت (callback)",
        operation_description="""
درگاه پس از پرداخت کاربر را به این endpoint هدایت می‌کند با پارامترهای query:
- Authority: شناسه تراکنش (زرین‌پال) یا هر شناسهٔ مورد استفاده
- Status: وضعیت عملیات (مثلا 'OK' یا مقدار دیگر)
""",
        manual_parameters=[
            openapi.Parameter('Authority', openapi.IN_QUERY, description="شناسه تراکنش", type=openapi.TYPE_STRING),
            openapi.Parameter('Status', openapi.IN_QUERY, description="وضعیت تراکنش", type=openapi.TYPE_STRING),
        ],
        responses={
            200: openapi.Response(description="نتیجه پرداخت موفق یا پیغام"),
            400: openapi.Response(description="خطا در تراکنش یا پارامترها")
        },
        tags=["reservation-api"]
    )
    def get(self, request):
        authority = request.query_params.get('Authority')
        status_param = request.query_params.get('Status')

        if not authority or not status_param:
            return Response({"detail": "پارامترهای مورد نیاز ارائه نشده‌اند.", "error_code": "missing_parameters"}, status=status.HTTP_400_BAD_REQUEST)

        # 1) از کش مستقیماً tracking_code را بر اساس authority می‌گیریم
        tracking_code = get_tracking_by_authority(authority)
        if not tracking_code:
            logger.error(f"Authority {authority} not found in cache")
            return Response({"detail": "تراکنش نامعتبر است.", "error_code": "invalid_transaction"}, status=status.HTTP_400_BAD_REQUEST)

        # 2) پیدا کردن رزرو
        try:
            reservation = Reservationhotel.objects.get(tracking_code=tracking_code)
        except Reservationhotel.DoesNotExist:
            return Response({"detail": "رزرو یافت نشد.", "error_code": "reservation_not_found"}, status=status.HTTP_400_BAD_REQUEST)

        # 3) درگاه فعال و merchant
        try:
            active_gateway = get_active_gateway()
            merchant_code = get_merchant_code(active_gateway)
        except ValidationError as e:
            payload = e.message_dict if hasattr(e, "message_dict") else {"detail": str(e)}
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

        # 4) پردازش بر اساس درگاه
        if active_gateway == 'zarinpal':
            # برای زرین‌پال، Status باید OK باشد و سپس PaymentVerification صدا زده شود
            if status_param != 'OK':
                logger.warning(f"Payment status not OK for {tracking_code}: {status_param}")
                return Response({"status": "failed", "detail": "تراکنش لغو شد یا ناموفق بود."}, status=status.HTTP_400_BAD_REQUEST)

            if Client is None:
                return Response({"detail": "پکیج zeep نصب نشده است.", "error_code": "zeep_missing"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            try:
                client = Client('https://www.zarinpal.com/pg/services/WebGate/wsdl')
                result = client.service.PaymentVerification(
                    MerchantID=merchant_code,
                    Authority=authority,
                    Amount=int(reservation.final_price)
                )

                if getattr(result, "Status", None) in [100, 101]:
                    with transaction.atomic():
                        reservation.payment_status = 'paid'
                        reservation.save(update_fields=['payment_status'])
                        # پاک کردن کش مربوطه
                        cache.delete(f"payment_link_{tracking_code}")
                        cache.delete(f"payment_link_authority_{authority}")
                    logger.info(f"Payment successful for {tracking_code} authority={authority}")
                    return Response({"status": "success", "detail": "پرداخت با موفقیت انجام شد."}, status=status.HTTP_200_OK)
                else:
                    logger.error(f"Zarinpal verification failed for {tracking_code}: {getattr(result, 'Status', None)}")
                    return Response({"status": "failed", "detail": f"تأیید تراکنش ناموفق بود: کد وضعیت {getattr(result, 'Status', None)}", "error_code": "zarinpal_verification_failed"}, status=status.HTTP_400_BAD_REQUEST)

            except Exception as e:
                logger.exception("Error verifying zarinpal payment")
                return Response({"detail": f"خطا در تأیید پرداخت: {str(e)}", "error_code": "zarinpal_verification_error"}, status=status.HTTP_400_BAD_REQUEST)

        elif active_gateway == 'iraniangateway':
            # فعلاً نمونهٔ ساده — اینجا باید API رسمی ایران‌درگاه را پیاده کنید
            # فرض می‌کنیم callback نشان‌دهندهٔ موفقیت/عدم موفقیت است.
            logger.warning("Iranian gateway callback handling not implemented")
            return Response({"detail": "API ایران درگاه هنوز پیاده‌سازی نشده است.", "error_code": "iraniangateway_not_implemented"}, status=status.HTTP_400_BAD_REQUEST)

        else:
            return Response({"detail": f"درگاه فعال ناشناخته است: {active_gateway}", "error_code": "unknown_gateway"}, status=status.HTTP_400_BAD_REQUEST)
