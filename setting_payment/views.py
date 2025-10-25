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
        """
        try:
            merchant_code = settings.PAYMENT_GATEWAY_CONFIG['ZARINPAL_MERCHANT_CODE']
            final_price = int(reservation.final_price)
            tracking_code = reservation.tracking_code
            # فرضاً لینک پرداخت تولید می‌شود (باید با API واقعی زرین‌پال جایگزین شود)
            payment_link = f"https://zarinpal.com/pg/StartPay/{tracking_code}?amount={final_price}&merchant={merchant_code}"
            logger.debug(f"لینک پرداخت زرین‌پال تولید شد: {payment_link}")
            return payment_link
        except KeyError:
            logger.error("مرچند کد زرین‌پال در تنظیمات یافت نشد.")
            raise ValidationError("تنظیمات درگاه زرین‌پال یافت نشد.")
        except Exception as e:
            logger.error(f"خطا در تولید لینک زرین‌پال برای رزرو {reservation.tracking_code}: {str(e)}")
            raise ValidationError("خطا در تولید لینک پرداخت زرین‌پال")

    def generate_iraniangateway_payment_link(self, reservation):
        """
        تولید لینک پرداخت ایران درگاه با استفاده از تنظیمات ثابت.
        """
        try:
            merchant_code = settings.PAYMENT_GATEWAY_CONFIG['IRANIAN_GATEWAY_MERCHANT_CODE']
            final_price = int(reservation.final_price)
            tracking_code = reservation.tracking_code
            # فرضاً لینک پرداخت تولید می‌شود (باید با API واقعی ایران درگاه جایگزین شود)
            payment_link = f"https://iraniangateway.ir/pay/{tracking_code}?amount={final_price}&merchant={merchant_code}"
            logger.debug(f"لینک پرداخت ایران درگاه تولید شد: {payment_link}")
            return payment_link
        except KeyError:
            logger.error("مرچند کد ایران درگاه در تنظیمات یافت نشد.")
            raise ValidationError("تنظیمات درگاه ایران درگاه یافت نشد.")
        except Exception as e:
            logger.error(f"خطا در تولید لینک ایران درگاه برای رزرو {reservation.tracking_code}: {str(e)}")
            raise ValidationError("خطا در تولید لینک پرداخت ایران درگاه")

    @swagger_auto_schema(
        operation_summary="دریافت لینک پرداخت رزرو",
        operation_description="""
        بررسی رزرو بر اساس **tracking_code** و تولید لینک پرداخت در صورت نیاز.

        **شرایط:**
        - اگر رزرو تأیید شده باشد (`capacity_status == 'confirmed'`) و `final_price == 0`، لینک پرداخت `null` خواهد بود.
        - اگر `final_price > 0`، لینک پرداخت بر اساس درگاه فعال (زرین‌پال یا ایران درگاه) تولید می‌شود.
        - درگاه فعال و مرچند کدها از تنظیمات ثابت خوانده می‌شوند.

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
            400: openapi.Response(description="خطای اعتبارسنجی (رزرو تأیید نشده یا تنظیمات درگاه موجود نیست)"),
            403: openapi.Response(description="عدم دسترسی به رزرو"),
            404: openapi.Response(description="رزرو یافت نشد"),
        },
        tags=["reservation-api"]
    )
    def get(self, request, tracking_code):
        # دریافت رزرو
        reservation = get_object_or_404(Reservationhotel, tracking_code=tracking_code)
        
        # بررسی دسترسی کاربر
        if reservation.buyer != request.user:
            logger.warning(f"کاربر {request.user.phone_number} به رزرو {tracking_code} دسترسی ندارد.")
            raise ValidationError("شما به این رزرو دسترسی ندارید.")

        # بررسی وضعیت تأیید رزرو
        if reservation.capacity_status != 'confirmed':
            logger.warning(f"رزرو {tracking_code} تأیید نشده است. وضعیت: {reservation.capacity_status}")
            raise ValidationError("رزرو هنوز تأیید نشده است.")

        # بررسی final_price
        if reservation.final_price == Decimal('0'):
            logger.info(f"رزرو {tracking_code} نیازی به پرداخت ندارد (final_price=0).")
            return Response({"payment_link": None}, status=status.HTTP_200_OK)

        # دریافت درگاه فعال از تنظیمات ثابت
        try:
            active_gateway = settings.PAYMENT_GATEWAY_CONFIG['ACTIVE_GATEWAY']
        except KeyError:
            logger.error("درگاه فعال در تنظیمات یافت نشد.")
            raise ValidationError("درگاه فعال در تنظیمات یافت نشد.")

        # تولید لینک پرداخت بر اساس درگاه فعال
        payment_link = None
        if active_gateway == 'zarinpal':
            payment_link = self.generate_zarinpal_payment_link(reservation)
        elif active_gateway == 'iraniangateway':
            payment_link = self.generate_iraniangateway_payment_link(reservation)
        else:
            logger.error(f"درگاه ناشناخته: {active_gateway}")
            raise ValidationError("درگاه فعال ناشناخته است.")

        logger.debug(f"پاسخ API برای رزرو {tracking_code}: {{'payment_link': {payment_link}}}")
        return Response({"payment_link": payment_link}, status=status.HTTP_200_OK)