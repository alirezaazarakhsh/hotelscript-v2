from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from django.db.models import Q
from .models import CustomerClubPoint, RoomDiscountCode, ShoppingCenterDiscountCode
from .serializers import CustomerClubPointSerializer, RoomDiscountCodeSerializer, ShoppingCenterDiscountCodeSerializer
from bashgah_moshtarian.sms.sms import send_discount_code_sms  # اصلاح import به صورت مطلق




# ✅ ای‌پی‌آی دریافت کد تخفیف برای اتاق‌ها برای کاربر
class MyRoomDiscountCodeListView(ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = RoomDiscountCodeSerializer
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        return RoomDiscountCode.objects.filter(
            is_public=False,
            user=user
        ) | RoomDiscountCode.objects.filter(
            is_public=True
        ) | RoomDiscountCode.objects.filter(
            activated_users=user
        )

    @swagger_auto_schema(
        operation_summary="دریافت کدهای تخفیف اتاق برای کاربر",
        operation_description="""
این API کدهای تخفیف مرتبط با کاربر را بازمی‌گرداند:
- کدهای عمومی (is_public=True)
- کدهایی که فقط برای همین کاربر تعریف شده‌اند
- کدهایی که کاربر قبلاً آن‌ها را فعال کرده است.
""",
        tags=['discount-crm']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

# ✅ ای‌پی‌آی دریافت تخفیفات مراکز خرید کاربر
class MyShoppingCenterDiscountCodeListView(ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = ShoppingCenterDiscountCodeSerializer
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        return ShoppingCenterDiscountCode.objects.filter(
            is_public=False,
            user=user
        ) | ShoppingCenterDiscountCode.objects.filter(
            is_public=True
        ) | ShoppingCenterDiscountCode.objects.filter(
            activated_users=user
        )

    @swagger_auto_schema(
        operation_summary="دریافت کدهای تخفیف مراکز خرید برای کاربر",
        operation_description="""
این API کدهای تخفیف مربوط به مراکز خرید را بازمی‌گرداند که با کاربر مرتبط هستند:
- کدهای عمومی (is_public=True)
- کدهای اختصاصی مربوط به کاربر
- کدهایی که کاربر آن‌ها را فعال کرده است.
""",
        tags=['discount-crm']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)




# ✅ ای‌پی‌آی نمایش امتیاز باشگاه مشتریان کاربر
class MyCustomerClubPointView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="دریافت امتیاز باشگاه مشتریان",
        operation_description="""
این API امتیاز فعلی کاربر در باشگاه مشتریان را بازمی‌گرداند.
        """,
        tags=["discount-crm"]
    )
    def get(self, request, *args, **kwargs):
        try:
            instance = CustomerClubPoint.objects.get(user=request.user)
            serializer = CustomerClubPointSerializer(instance)
            return Response(serializer.data)
        except CustomerClubPoint.DoesNotExist:
            return Response({'points': 0}, status=200)




# ✅ ای‌پی‌آی ارسال پیامک برای کد تخفیف اتاق
class SendRoomDiscountCodeSMSView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="ارسال پیامک کد تخفیف اتاق",
        operation_description="""
        این API پیامک کد تخفیف اتاق را برای کاربر ارسال می‌کند.
        - کاربر باید احراز هویت شده باشد.
        - کد تخفیف باید برای کاربر قابل دسترس باشد (عمومی، اختصاصی یا فعال‌شده توسط کاربر).
        - پارامتر `discount_code_id` باید در بدنه درخواست ارسال شود.
        """,
        request_body=RoomDiscountCodeSerializer,
        responses={
            200: "پیامک با موفقیت ارسال شد.",
            400: "خطا در درخواست (مثلاً کد تخفیف نامعتبر یا عدم دسترسی کاربر).",
            500: "خطای سرور در ارسال پیامک."
        },
        tags=['discount-crm']
    )
    def post(self, request, *args, **kwargs):
        discount_code_id = request.data.get('discount_code_id')
        if not discount_code_id:
            return Response(
                {"error": "discount_code_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # بررسی وجود کد تخفیف و دسترسی کاربر
            discount_code = RoomDiscountCode.objects.filter(
                id=discount_code_id
            ).filter(
                is_public=True | Q(user=request.user) | Q(activated_users=request.user)
            ).first()

            if not discount_code:
                return Response(
                    {"error": "Discount code not found or not accessible"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # ارسال پیامک با استفاده از تابع موجود
            success = send_discount_code_sms(discount_code, pattern_section='discountcode')
            if success:
                return Response(
                    {"message": "SMS sent successfully"},
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {"error": "Failed to send SMS"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except RoomDiscountCode.DoesNotExist:
            return Response(
                {"error": "Discount code not found"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )




# ✅ ای‌پی‌آی ارسال پیامک برای کد تخفیف مرکز خرید
class SendShoppingCenterDiscountCodeSMSView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="ارسال پیامک کد تخفیف مرکز خرید",
        operation_description="""
        این API پیامک کد تخفیف مرکز خرید را برای کاربر ارسال می‌کند.
        - کاربر باید احراز هویت شده باشد.
        - کد تخفیف باید برای کاربر قابل دسترس باشد (عمومی، اختصاصی یا فعال‌شده توسط کاربر).
        - پارامتر `discount_code_id` باید در بدنه درخواست ارسال شود.
        """,
        request_body=ShoppingCenterDiscountCodeSerializer,
        responses={
            200: "پیامک با موفقیت ارسال شد.",
            400: "خطا در درخواست (مثلاً کد تخفیف نامعتبر یا عدم دسترسی کاربر).",
            500: "خطای سرور در ارسال پیامک."
        },
        tags=['discount-crm']
    )
    def post(self, request, *args, **kwargs):
        discount_code_id = request.data.get('discount_code_id')
        if not discount_code_id:
            return Response(
                {"error": "discount_code_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # بررسی وجود کد تخفیف و دسترسی کاربر
            discount_code = ShoppingCenterDiscountCode.objects.filter(
                id=discount_code_id
            ).filter(
                is_public=True | Q(user=request.user) | Q(activated_users=request.user)
            ).first()

            if not discount_code:
                return Response(
                    {"error": "Discount code not found or not accessible"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # ارسال پیامک با استفاده از تابع موجود
            success = send_discount_code_sms(discount_code, pattern_section='discountcode')
            if success:
                return Response(
                    {"message": "SMS sent successfully"},
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {"error": "Failed to send SMS"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except ShoppingCenterDiscountCode.DoesNotExist:
            return Response(
                {"error": "Discount code not found"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )