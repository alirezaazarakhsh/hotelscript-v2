from django.http import HttpResponseRedirect
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .serializers import CreateTransactionSerializer, VerifyTransactionSerializer, TransactionResponseSerializer
from .payment_service import PaymentGatewayService
from .models import Reservationhotel
import logging

logger = logging.getLogger(__name__)

class CreateTransactionView(APIView):
    @swagger_auto_schema(
        operation_summary="ایجاد تراکنش پرداخت با ایران درگاه",
        operation_description="""
        این API یک تراکنش پرداخت جدید با استفاده از درگاه ایران درگاه ایجاد می‌کند. 
        پس از ایجاد موفقیت‌آمیز تراکنش، یک `authority` و لینک پرداخت (`payment_url`) برای هدایت کاربر به درگاه پرداخت بازگشت داده می‌شود.

        **ورودی‌ها (در body درخواست POST):**
        - `amount`: مبلغ تراکنش (تومان، حداقل ۱,۰۰۰ تومان)
        - `callback_url`: آدرس بازگشت پس از پرداخت (باید با SITE_URL تنظیم‌شده در پروژه شروع شود)
        - `order_id`: شناسه یکتای سفارش
        - `mobile`: شماره موبایل کاربر (اختیاری)
        - `description`: توضیحات تراکنش (اختیاری)

        **حالات خاص:**
        - اگر مرچنت کد درگاه تنظیم نشده باشد، خطا بازمی‌گردد.
        - اگر `callback_url` نامعتبر باشد (مثلاً با SITE_URL شروع نشود)، خطا بازمی‌گردد.
        - در صورت بروز خطا در اتصال به درگاه یا پاسخ نامعتبر، خطا با جزئیات بازمی‌گردد.

        **خروجی:**
        - در صورت موفقیت: `authority` و `payment_url` برای هدایت به درگاه.
        - در صورت خطا: پیام خطا با جزئیات.
        """,
        request_body=CreateTransactionSerializer,
        responses={
            200: TransactionResponseSerializer,
            400: openapi.Response(description="خطاهای اعتبارسنجی یا خطای درگاه (مثل مرچنت کد نامعتبر یا پاسخ نامعتبر)."),
        },
        tags=["payment-api"]
    )
    def post(self, request):
        serializer = CreateTransactionSerializer(data=request.data)
        if serializer.is_valid():
            try:
                # تنظیم درگاه به صورت دستی به ایران درگاه
                PaymentGatewayService.get_active_gateway = lambda: 'iraniangateway'
                authority = PaymentGatewayService.create_transaction(
                    amount=serializer.validated_data['amount'],
                    callback_url=serializer.validated_data['callback_url'],
                    order_id=serializer.validated_data['order_id'],
                    mobile=serializer.validated_data.get('mobile', None),
                    description=serializer.validated_data.get('description', None)
                )
                payment_url = PaymentGatewayService.get_payment_url(authority)
                response_data = {
                    'authority': authority,
                    'payment_url': payment_url
                }
                return Response(TransactionResponseSerializer(response_data).data, status=status.HTTP_200_OK)
            except ValueError as e:
                logger.error(f"خطا در ایجاد تراکنش: {str(e)}")
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VerifyTransactionView(APIView):
    @swagger_auto_schema(
        operation_summary="تأیید تراکنش پرداخت با ایران درگاه",
        operation_description="""
        این API یک تراکنش پرداخت را با استفاده از درگاه ایران درگاه تأیید می‌کند. 
        در صورت موفقیت، شناسه ارجاع (`ref_id`) تراکنش بازگشت داده می‌شود.

        **ورودی‌ها (در body درخواست POST):**
        - `authority`: شناسه تراکنش دریافت‌شده از درخواست ایجاد تراکنش
        - `amount`: مبلغ تراکنش (تومان، باید با مبلغ تراکنش اولیه مطابقت داشته باشد)
        - `order_id`: شناسه یکتای سفارش

        **حالات خاص:**
        - اگر مرچنت کد درگاه تنظیم نشده باشد، خطا بازمی‌گردد.
        - اگر `authority` یا مبلغ نامعتبر باشد، خطا بازمی‌گردد.
        - در صورت بروز خطا در اتصال به درگاه یا پاسخ نامعتبر، خطا با جزئیات بازمی‌گردد.

        **خروجی:**
        - در صورت موفقیت: `ref_id` تراکنش.
        - در صورت خطا: پیام خطا با جزئیات.
        """,
        request_body=VerifyTransactionSerializer,
        responses={
            200: openapi.Response(description="تأیید تراکنش با موفقیت انجام شد.", schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'ref_id': openapi.Schema(type=openapi.TYPE_STRING, description='شناسه ارجاع تراکنش')
                }
            )),
            400: openapi.Response(description="خطاهای اعتبارسنجی یا خطای درگاه (مثل authority نامعتبر یا پاسخ نامعتبر)."),
        },
        tags=["payment-api"]
    )
    def post(self, request):
        serializer = VerifyTransactionSerializer(data=request.data)
        if serializer.is_valid():
            try:
                # تنظیم درگاه به صورت دستی به ایران درگاه
                PaymentGatewayService.get_active_gateway = lambda: 'iraniangateway'
                ref_id = PaymentGatewayService.verify_transaction(
                    authority=serializer.validated_data['authority'],
                    amount=serializer.validated_data['amount'],
                    order_id=serializer.validated_data['order_id']
                )
                return Response({'ref_id': ref_id}, status=status.HTTP_200_OK)
            except ValueError as e:
                logger.error(f"خطا در تأیید تراکنش: {str(e)}")
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@swagger_auto_schema(
    operation_summary="مدیریت پاسخ بازگشتی (callback) از درگاه ایران درگاه",
    operation_description="""
    این API پاسخ بازگشتی از درگاه ایران درگاه را پس از انجام پرداخت توسط کاربر مدیریت می‌کند.
    درگاه ایران درگاه پارامترهای `Authority` و `Status` را از طریق query string ارسال می‌کند.
    این ویو تراکنش را تأیید می‌کند و در صورت موفقیت یا شکست، کاربر را به صفحه مناسب هدایت می‌کند.

    **پارامترهای ورودی (query string):**
    - `Authority`: شناسه تراکنش دریافت‌شده از درگاه.
    - `Status`: وضعیت تراکنش (مثلاً 'OK' یا 'NOK').

    **حالات خاص:**
    - اگر `Status` برابر با 'OK' باشد، تراکنش تأیید می‌شود و `ref_id` دریافت می‌شود.
    - اگر `Status` برابر با 'NOK' یا خطایی رخ دهد، کاربر به صفحه خطا هدایت می‌شود.
    - اگر رزرو یا تراکنش یافت نشود، خطا بازمی‌گردد.

    **خروجی:**
    - در صورت موفقیت: هدایت به صفحه موفقیت پرداخت (با `ref_id` و اطلاعات رزرو).
    - در صورت خطا: هدایت به صفحه خطا یا پیام خطا.
    """,
    manual_parameters=[
        openapi.Parameter('Authority', openapi.IN_QUERY, description="شناسه تراکنش", type=openapi.TYPE_STRING),
        openapi.Parameter('Status', openapi.IN_QUERY, description="وضعیت تراکنش (OK/NOK)", type=openapi.TYPE_STRING),
    ],
    responses={
        200: openapi.Response(description="پرداخت با موفقیت تأیید شد.", schema=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'ref_id': openapi.Schema(type=openapi.TYPE_STRING, description='شناسه ارجاع تراکنش'),
                'message': openapi.Schema(type=openapi.TYPE_STRING, description='پیام وضعیت')
            }
        )),
        400: openapi.Response(description="خطا در تأیید تراکنش یا پارامترهای نامعتبر."),
        404: openapi.Response(description="رزرو یا تراکنش یافت نشد.")
    },
    tags=["payment-api"]
)
def callback_view(request):
    authority = request.GET.get('Authority')
    status_param = request.GET.get('Status')

    # بررسی وجود پارامترها
    if not authority or not status_param:
        logger.error(f"پارامترهای نامعتبر در callback: Authority={authority}, Status={status_param}")
        return Response({'error': 'پارامترهای بازگشتی نامعتبر هستند.'}, status=status.HTTP_400_BAD_REQUEST)

    # پیدا کردن رزرو مرتبط با authority
    try:
        reservation = Reservationhotel.objects.get(payment_authority=authority)
    except Reservationhotel.DoesNotExist:
        logger.error(f"رزرو با authority {authority} یافت نشد.")
        return Response({'error': 'رزرو مرتبط با این تراکنش یافت نشد.'}, status=status.HTTP_404_NOT_FOUND)

    # بررسی وضعیت پرداخت
    if status_param != 'OK':
        logger.warning(f"تراکنش با authority {authority} لغو شد یا ناموفق بود: Status={status_param}")
        reservation.payment_status = 'failed'
        reservation.save()
        error_url = f"{settings.SITE_URL}/payment/error/?tracking_code={reservation.tracking_code}"
        return HttpResponseRedirect(error_url)

    # تأیید تراکنش
    try:
        PaymentGatewayService.get_active_gateway = lambda: 'iraniangateway'
        ref_id = PaymentGatewayService.verify_transaction(
            authority=authority,
            amount=reservation.final_price,
            order_id=reservation.tracking_code
        )
        reservation.payment_status = 'paid'
        reservation.payment_ref_id = ref_id
        reservation.save()
        logger.info(f"تراکنش با authority {authority} با موفقیت تأیید شد: ref_id={ref_id}")
        success_url = f"{settings.SITE_URL}/payment/success/?tracking_code={reservation.tracking_code}&ref_id={ref_id}"
        return HttpResponseRedirect(success_url)
    except ValueError as e:
        logger.error(f"خطا در تأیید تراکنش با authority {authority}: {str(e)}")
        reservation.payment_status = 'failed'
        reservation.save()
        error_url = f"{settings.SITE_URL}/payment/error/?tracking_code={reservation.tracking_code}"
        return HttpResponseRedirect(error_url)