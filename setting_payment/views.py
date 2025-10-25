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
from django.core.cache import cache
from datetime import datetime, timedelta
from django.db import transaction
from zeep import Client  # برای API زرین‌پال

logger = logging.getLogger(__name__)


# =====================================================================
# دریافت لینک پرداخت رزرو
# =====================================================================
class ReservationPaymentCheckAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def generate_zarinpal_payment_link(self, reservation):
        """تولید لینک پرداخت زرین‌پال با استفاده از API واقعی."""
        try:
            merchant_code = settings.PAYMENT_GATEWAY_CONFIG['ZARINPAL_MERCHANT_CODE']
            final_price = int(reservation.final_price)
            tracking_code = reservation.tracking_code
            callback_url = settings.PAYMENT_GATEWAY_CONFIG['CALLBACK_URL']

            client = Client('https://www.zarinpal.com/pg/services/WebGate/wsdl')
            result = client.service.PaymentRequest(
                MerchantID=merchant_code,
                Amount=final_price,
                Description=f"پرداخت رزرو {tracking_code}",
                CallbackURL=callback_url,
            )

            if result.Status == 100:
                payment_link = f"https://www.zarinpal.com/pg/StartPay/{result.Authority}"
                cache.set(
                    f"payment_link_{tracking_code}",
                    {
                        'link': payment_link,
                        'authority': result.Authority,
                        'expires_at': (datetime.now() + timedelta(minutes=30)).timestamp()
                    },
                    timeout=1800
                )
                logger.debug(f"لینک پرداخت زرین‌پال تولید شد: {payment_link}")
                return payment_link
            else:
                raise ValidationError({
                    "detail": f"خطا در تولید لینک پرداخت زرین‌پال: کد وضعیت {result.Status}",
                    "error_code": "zarinpal_payment_error"
                })
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
        """تولید لینک پرداخت ایران درگاه (نمونه‌سازی‌شده)."""
        try:
            merchant_code = settings.PAYMENT_GATEWAY_CONFIG['IRANIAN_GATEWAY_MERCHANT_CODE']
            final_price = int(reservation.final_price)
            tracking_code = reservation.tracking_code
            payment_link = f"https://iraniangateway.ir/pay/{tracking_code}?amount={final_price}&merchant={merchant_code}"
            cache.set(
                f"payment_link_{tracking_code}",
                {
                    'link': payment_link,
                    'authority': tracking_code,
                    'expires_at': (datetime.now() + timedelta(minutes=30)).timestamp()
                },
                timeout=1800
            )
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
        tags=["reservation-api"]
    )
    def get(self, request, tracking_code):
        reservation = get_object_or_404(Reservationhotel, tracking_code=tracking_code)

        if reservation.buyer != request.user:
            raise ValidationError({
                "detail": "شما به این رزرو دسترسی ندارید.",
                "error_code": "access_denied"
            })

        if reservation.capacity_status != 'confirmed':
            raise ValidationError({
                "detail": "رزرو هنوز تأیید نشده است.",
                "error_code": "reservation_not_confirmed",
                "current_status": reservation.capacity_status
            })

        if reservation.final_price == Decimal('0'):
            return Response({"payment_link": None}, status=status.HTTP_200_OK)

        payment_data = cache.get(f"payment_link_{tracking_code}")
        if payment_data and payment_data['expires_at'] > datetime.now().timestamp():
            return Response({"payment_link": payment_data['link']}, status=status.HTTP_200_OK)
        elif payment_data:
            raise ValidationError({
                "detail": "لینک پرداخت منقضی شده است. لطفاً دوباره تلاش کنید.",
                "error_code": "payment_link_expired"
            })

        try:
            active_gateway = settings.PAYMENT_GATEWAY_CONFIG['ACTIVE_GATEWAY']
        except KeyError:
            raise ValidationError({
                "detail": "درگاه فعال در تنظیمات یافت نشد.",
                "error_code": "missing_active_gateway"
            })

        if active_gateway == 'zarinpal':
            payment_link = self.generate_zarinpal_payment_link(reservation)
        elif active_gateway == 'iraniangateway':
            payment_link = self.generate_iraniangateway_payment_link(reservation)
        else:
            raise ValidationError({
                "detail": f"درگاه فعال ناشناخته است: {active_gateway}",
                "error_code": "unknown_gateway"
            })

        return Response({"payment_link": payment_link}, status=status.HTTP_200_OK)


# =====================================================================
# بررسی نتیجه پرداخت (Callback)
# =====================================================================
class PaymentCallbackAPIView(APIView):
    permission_classes = []  # نیاز به احراز هویت ندارد (درگاه پرداخت صدا می‌زند)

    @swagger_auto_schema(
        operation_summary="بررسی نتیجه پرداخت",
        tags=["reservation-api"]
    )
    def get(self, request):
        authority = request.query_params.get('Authority')
        status_param = request.query_params.get('Status')
        active_gateway = settings.PAYMENT_GATEWAY_CONFIG.get('ACTIVE_GATEWAY')

        if not authority or not status_param:
            return Response({
                "detail": "پارامترهای مورد نیاز ارائه نشده‌اند.",
                "error_code": "missing_parameters"
            }, status=status.HTTP_400_BAD_REQUEST)

        payment_data = None
        for key in cache.iter_keys("payment_link_*"):
            data = cache.get(key)
            if data and data['authority'] == authority:
                payment_data = data
                tracking_code = key.replace("payment_link_", "")
                break

        if not payment_data:
            return Response({
                "detail": "تراکنش نامعتبر است.",
                "error_code": "invalid_transaction"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            reservation = Reservationhotel.objects.get(tracking_code=tracking_code)
        except Reservationhotel.DoesNotExist:
            return Response({
                "detail": "رزرو یافت نشد.",
                "error_code": "reservation_not_found"
            }, status=status.HTTP_400_BAD_REQUEST)

        if active_gateway == 'zarinpal':
            if status_param != 'OK':
                return Response({
                    "status": "failed",
                    "detail": "تراکنش لغو شد یا ناموفق بود."
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                merchant_code = settings.PAYMENT_GATEWAY_CONFIG['ZARINPAL_MERCHANT_CODE']
                client = Client('https://www.zarinpal.com/pg/services/WebGate/wsdl')
                result = client.service.PaymentVerification(
                    MerchantID=merchant_code,
                    Authority=authority,
                    Amount=int(reservation.final_price)
                )

                if result.Status in [100, 101]:
                    with transaction.atomic():
                        reservation.payment_status = 'paid'
                        reservation.save(update_fields=['payment_status'])
                        cache.delete(f"payment_link_{tracking_code}")
                    return Response({
                        "status": "success",
                        "detail": "پرداخت با موفقیت انجام شد."
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        "status": "failed",
                        "detail": f"تأیید تراکنش ناموفق بود: کد وضعیت {result.Status}",
                        "error_code": "zarinpal_verification_failed"
                    }, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                return Response({
                    "detail": f"خطا در تأیید پرداخت: {str(e)}",
                    "error_code": "zarinpal_verification_error"
                }, status=status.HTTP_400_BAD_REQUEST)

        elif active_gateway == 'iraniangateway':
            return Response({
                "detail": "API ایران درگاه پیاده‌سازی نشده است.",
                "error_code": "iraniangateway_not_implemented"
            }, status=status.HTTP_400_BAD_REQUEST)

        else:
            return Response({
                "detail": f"درگاه فعال ناشناخته است: {active_gateway}",
                "error_code": "unknown_gateway"
            }, status=status.HTTP_400_BAD_REQUEST)
