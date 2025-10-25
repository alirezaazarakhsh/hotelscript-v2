import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.http import JsonResponse
from .payment_service import PaymentGatewayService
import json

logger = logging.getLogger(__name__)

class PaymentGatewayAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="ایجاد تراکنش پرداخت",
        operation_description="""
        این API به کاربر احراز هویت‌شده اجازه می‌دهد یک تراکنش پرداخت از طریق درگاه ایران درگاه ایجاد کند.
        کاربر به صفحه پرداخت هدایت می‌شود.

        **ورودی‌ها (در body درخواست POST):**
        - `amount`: مبلغ تراکنش (ریال، حداقل ۱۰,۰۰۰ ریال)
        - `order_id`: شناسه سفارش (رقم یکتا برای ردیابی)
        - `mobile`: شماره همراه (اختیاری)
        - `description`: توضیحات تراکنش (اختیاری)

        **حالات خاص:**
        - درگاه فعال باید ایران درگاه باشد (از تنظیمات ترجیحات درگاه).
        - مرچنت کد باید در ادمین تنظیم شده باشد.

        **خروجی:**
        - در صورت موفقیت: ریدایرکت به صفحه پرداخت.
        - در صورت خطا: پیام خطا با جزئیات.
        """,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'amount': openapi.Schema(type=openapi.TYPE_INTEGER, description='مبلغ تراکنش (ریال، حداقل ۱۰,۰۰۰)'),
                'order_id': openapi.Schema(type=openapi.TYPE_STRING, description='شناسه سفارش'),
                'mobile': openapi.Schema(type=openapi.TYPE_STRING, description='شماره همراه (اختیاری)'),
                'description': openapi.Schema(type=openapi.TYPE_STRING, description='توضیحات تراکنش (اختیاری)'),
            },
            required=['amount', 'order_id']
        ),
        responses={
            302: openapi.Response(description="ریدایرکت به صفحه پرداخت."),
            400: openapi.Response(description="خطاهای اعتبارسنجی (مثل مبلغ نامعتبر یا تنظیمات ناقص)."),
            403: openapi.Response(description="درگاه فعال ایران درگاه نیست."),
            500: openapi.Response(description="خطای سرور یا اتصال به درگاه."),
        },
        tags=["payment-api"]
    )
    def post(self, request):
        amount = request.data.get('amount')
        order_id = request.data.get('order_id')
        mobile = request.data.get('mobile')
        description = request.data.get('description')

        # اعتبارسنجی ورودی‌ها
        if not amount or not isinstance(amount, (int, float)) or amount < 10000:
            logger.error(f"مبلغ نامعتبر برای سفارش {order_id}: {amount}")
            return Response({"detail": "مبلغ باید حداقل ۱۰,۰۰۰ ریال باشد."}, status=status.HTTP_400_BAD_REQUEST)

        if not order_id:
            logger.error("شناسه سفارش خالی است.")
            return Response({"detail": "شناسه سفارش الزامی است."}, status=status.HTTP_400_BAD_REQUEST)

        # تنظیم callbackURL با دامنه فعلی
        callback_url = f"https://cps.safarnameh24.com/callback/"

        try:
            authority = PaymentGatewayService.create_transaction(
                amount=amount,
                callback_url=callback_url,
                order_id=order_id,
                mobile=mobile,
                description=description
            )
            payment_url = PaymentGatewayService.get_payment_url(authority)
            logger.info(f"تراکنش برای سفارش {order_id} با موفقیت ایجاد شد. Authority: {authority}")
            return HttpResponseRedirect(payment_url)  # ریدایرکت به درگاه
        except ValueError as e:
            logger.error(f"خطا در ایجاد تراکنش برای سفارش {order_id}: {str(e)}")
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"خطای سرور در ایجاد تراکنش برای سفارش {order_id}: {str(e)}")
            return Response({"detail": "خطا در اتصال به درگاه."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_summary="تأیید تراکنش پرداخت",
        operation_description="""
        این API تراکنش پرداخت را از طریق درگاه ایران درگاه تأیید می‌کند.
        این مرحله پس از بازگشت کاربر از درگاه و دریافت اطلاعات تراکنش انجام می‌شود.

        **ورودی‌ها (در body درخواست POST):**
        - `authority`: شناسه تراکنش دریافت‌شده از مرحله ایجاد
        - `amount`: مبلغ تراکنش (ریال)
        - `order_id`: شناسه سفارش

        **حالات خاص:**
        - فقط برای تراکنش‌های موفق (code=100) قابل انجام است.
        - مرچنت کد باید تنظیم شده باشد.

        **خروجی:**
        - در صورت موفقیت: شماره پیگیری (refId).
        - در صورت خطا: پیام خطا با جزئیات.
        """,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'authority': openapi.Schema(type=openapi.TYPE_STRING, description='شناسه تراکنش'),
                'amount': openapi.Schema(type=openapi.TYPE_INTEGER, description='مبلغ تراکنش (ریال)'),
                'order_id': openapi.Schema(type=openapi.TYPE_STRING, description='شناسه سفارش'),
            },
            required=['authority', 'amount', 'order_id']
        ),
        responses={
            200: openapi.Response(description="تراکنش تأیید شد.", 
                                  schema=openapi.Schema(
                                      type=openapi.TYPE_OBJECT,
                                      properties={
                                          'refId': openapi.Schema(type=openapi.TYPE_STRING, description='شماره پیگیری تراکنش')
                                      }
                                  )),
            400: openapi.Response(description="خطاهای اعتبارسنجی یا تراکنش ناموفق."),
            403: openapi.Response(description="درگاه فعال ایران درگاه نیست."),
            500: openapi.Response(description="خطای سرور یا اتصال به درگاه."),
        },
        tags=["payment-api"]
    )
    def post_verify(self, request):
        authority = request.data.get('authority')
        amount = request.data.get('amount')
        order_id = request.data.get('order_id')

        # اعتبارسنجی ورودی‌ها
        if not all([authority, amount, order_id]):
            logger.error(f"ورودی‌های ناقص برای تأیید تراکنش: {request.data}")
            return Response({"detail": "همه فیلدهای الزامی (authority, amount, order_id) باید پر شوند."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            ref_id = PaymentGatewayService.verify_transaction(authority, amount, order_id)
            logger.info(f"تراکنش برای سفارش {order_id} با موفقیت تأیید شد. RefID: {ref_id}")
            return Response({"refId": ref_id}, status=status.HTTP_200_OK)
        except ValueError as e:
            logger.error(f"خطا در تأیید تراکنش برای سفارش {order_id}: {str(e)}")
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"خطای سرور در تأیید تراکنش برای سفارش {order_id}: {str(e)}")
            return Response({"detail": "خطا در اتصال به درگاه."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)