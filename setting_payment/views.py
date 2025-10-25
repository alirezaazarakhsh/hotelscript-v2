from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import logging
from django.conf import settings
from reservation.models import Reservationhotel
from decimal import Decimal

logger = logging.getLogger(__name__)

class ReservationPaymentCheckAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def generate_zarinpal_payment_link(self, reservation):
        """
        تولید لینک پرداخت زرین‌پال با استفاده از تنظیمات ثابت.
        باید با API واقعی زرین‌پال جایگزین شود.
        """
        try:
            merchant_code = settings.PAYMENT_GATEWAY_CONFIG['ZARINPAL_MERCHANT_CODE']
            final_price = int(reservation.final_price)
            tracking_code = reservation.tracking_code
            # لینک فرضی برای زرین‌پال (باید با API واقعی جایگزین شود)
            payment_link = f"https://zarinpal.com/pg/StartPay/{tracking_code}?amount={final_price}&merchant={merchant_code}"
            logger.debug(f"لینک پرداخت زرین‌پال تولید شد: {payment_link}")
            return payment_link
        except KeyError:
            logger.error("مرچند کد زرین‌پال در تنظیمات یافت نشد.")
            raise ValidationError({
                "detail": "تنظیمات درگاه زرین‌پال یافت نشد.",
                "error_code": "missing_zarinpal_config"
            })
        except Exception as e:
            logger.error(f"خطا در تولید لینک زرین‌پال برای رزرو {reservation.tracking_code}: {str(e)}")
            raise ValidationError({
                "detail": f"خطا در تولید لینک پرداخت زرین‌پال: {str(e)}",
                "error_code": "zarinpal_payment_error"
            })

    def generate_iraniangateway_payment_link(self, reservation):
        """
        تولید لینک پرداخت ایران درگاه با استفاده از تنظیمات ثابت.
        باید با API واقعی ایران درگاه جایگزین شود.
        """
        try:
            merchant_code = settings.PAYMENT_GATEWAY_CONFIG['IRANIAN_GATEWAY_MERCHANT_CODE']
            final_price = int(reservation.final_price)
            tracking_code = reservation.tracking_code
            # لینک فرضی برای ایران درگاه (باید با API واقعی جایگزین شود)
            payment_link = f"https://iraniangateway.ir/pay/{tracking_code}?amount={final_price}&merchant={merchant_code}"
            logger.debug(f"لینک پرداخت ایران درگاه تولید شد: {payment_link}")
            return payment_link
        except KeyError:
            logger.error("مرچند کد ایران درگاه در تنظیمات یافت نشد.")
            raise ValidationError({
                "detail": "تنظیمات درگاه ایران درگاه یافت نشد.",
                "error_code": "missing_iraniangateway_config"
            })
        except Exception as e:
            logger.error(f"خطا در تولید لینک ایران درگاه برای رزرو {reservation.tracking_code}: {str(e)}")
            raise ValidationError({
                "detail": f"خطا در تولید لینک پرداخت ایران درگاه: {str(e)}",
                "error_code": "iraniangateway_payment_error"
            })

    @swagger_auto_schema(
        operation_summary="دریافت لینک پرداخت رزرو",
        operation_description="""
        بررسی رزرو بر اساس **tracking_code** و تولید لینک پرداخت در صورت نیاز.

        **شرایط:**
        - کاربر باید مالک رزرو باشد.
        - رزرو باید در وضعیت 'confirmed' باشد.
        - اگر `final_price == 0`، لینک پرداخت `null` خواهد بود.
        - اگر `final_price > 0`، لینک پرداخت بر اساس درگاه فعال (زرین‌پال یا ایران درگاه) تولید می‌شود.
        - درگاه فعال و مرچند کدها از تنظیمات ثابت (settings.PAYMENT_GATEWAY_CONFIG) خوانده می‌شوند.

        **فیلدهای خروجی:**
        - `payment_link`: لینک پرداخت یا `null` در صورت عدم نیاز به پرداخت.

        **خطاها:**
        - 403: اگر کاربر به رزرو دسترسی نداشته باشد.
        - 404: اگر رزرو با `tracking_code` یافت نشود.
        - 400: اگر رزرو تأیید نشده باشد یا تنظیمات درگاه موجود نباشد.
        """,
        responses={
            200: openapi.Response(
                description="لینک پرداخت یا null",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'payment_link': openapi.Schema(type=openapi.TYPE_STRING, description="لینک پرداخت یا null", nullable=True)
                    }
                )
            ),
            400: openapi.Response(
                description="خطای اعتبارسنجی",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'detail': openapi.Schema(type=openapi.TYPE_STRING, description="پیام خطا"),
                        'error_code': openapi.Schema(type=openapi.TYPE_STRING, description="کد خطا", nullable=True),
                        'current_status': openapi.Schema(type=openapi.TYPE_STRING, description="وضعیت فعلی رزرو", nullable=True)
                    }
                )
            ),
            403: openapi.Response(
                description="عدم دسترسی به رزرو",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'detail': openapi.Schema(type=openapi.TYPE_STRING, description="پیام خطا"),
                        'error_code': openapi.Schema(type=openapi.TYPE_STRING, description="کد خطا")
                    }
                )
            ),
            404: openapi.Response(
                description="رزرو یافت نشد",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'detail': openapi.Schema(type=openapi.TYPE_STRING, description="پیام خطا")
                    }
                )
            ),
        },
        tags=["reservation-api"]
    )
    def get(self, request, tracking_code):
        # دریافت رزرو
        reservation = get_object_or_404(Reservationhotel, tracking_code=tracking_code)
        
        # بررسی دسترسی کاربر
        if reservation.buyer != request.user:
            logger.warning(f"کاربر {request.user.phone_number} به رزرو {tracking_code} دسترسی ندارد.")
            raise ValidationError({
                "detail": "شما به این رزرو دسترسی ندارید.",
                "error_code": "access_denied"
            })

        # بررسی وضعیت تأیید رزرو
        if reservation.capacity_status != 'confirmed':
            logger.warning(f"رزرو {tracking_code} تأیید نشده است. وضعیت: {reservation.capacity_status}")
            raise ValidationError({
                "detail": "رزرو هنوز تأیید نشده است.",
                "error_code": "reservation_not_confirmed",
                "current_status": reservation.capacity_status
            })

        # بررسی final_price
        if reservation.final_price == Decimal('0'):
            logger.info(f"رزرو {tracking_code} نیازی به پرداخت ندارد (final_price=0).")
            return Response({"payment_link": None}, status=status.HTTP_200_OK)

        # دریافت درگاه فعال از تنظیمات ثابت
        try:
            active_gateway = settings.PAYMENT_GATEWAY_CONFIG['ACTIVE_GATEWAY']
        except KeyError:
            logger.error("درگاه فعال در تنظیمات یافت نشد.")
            raise ValidationError({
                "detail": "درگاه فعال در تنظیمات یافت نشد.",
                "error_code": "missing_active_gateway"
            })

        # تولید لینک پرداخت بر اساس درگاه فعال
        payment_link = None
        if active_gateway == 'zarinpal':
            payment_link = self.generate_zarinpal_payment_link(reservation)
        elif active_gateway == 'iraniangateway':
            payment_link = self.generate_iraniangateway_payment_link(reservation)
        else:
            logger.error(f"درگاه ناشناخته: {active_gateway}")
            raise ValidationError({
                "detail": f"درگاه فعال ناشناخته است: {active_gateway}",
                "error_code": "unknown_gateway"
            })

        logger.debug(f"پاسخ API برای رزرو {tracking_code}: {{'payment_link': {payment_link}}}")
        return Response({"payment_link": payment_link}, status=status.HTTP_200_OK)