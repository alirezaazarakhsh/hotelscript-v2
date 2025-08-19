import traceback
import jdatetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics
from drf_yasg import openapi
from django.db.models import Count, Q, F
from .models import (
    CustomerClubPoint,
    DiscountActivationRecord,
    RoomDiscountCode,
    ShoppingCenterDiscountCode,
    NaturalProfile
)
from .serializers import (
    CustomerClubPointSerializer,
    DiscountActivationRecordSerializer,
    RoomDiscountCodeSerializer,
    ShoppingCenterDiscountCodeSerializer
)


# ✅ API کدهای تخفیف اتاق
class MyRoomDiscountCodeListView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = RoomDiscountCodeSerializer

    def get_queryset(self):
        user = self.request.user
        today_jalali = jdatetime.date.today()

        # دسترسی به سطح کاربر از مدل NaturalProfile
        try:
            user_level = user.natural_profile.level  # دسترسی به سطح کاربر
        except (AttributeError, NaturalProfile.DoesNotExist):
            user_level = None  # در صورتی که پروفایل یا سطح وجود نداشته باشد

        return (
            RoomDiscountCode.objects.annotate(
                activated_count=Count('activated_users', distinct=True)
            )
            .filter(
                Q(users=user) | 
                Q(activated_users=user) | 
                Q(user_level=user_level) if user_level else Q(),
                Q(expires_at__isnull=True) | Q(expires_at__gte=today_jalali),
                Q(activated_count__lt=F('usage_limit'))
            )
            .distinct()
        )

    @swagger_auto_schema(
        operation_summary="دریافت کدهای تخفیف اتاق برای کاربر",
        operation_description="""
        این API فقط کدهای معتبر اتاق را برمی‌گرداند:
        - به کاربر اختصاص داده شده یا فعال کرده است.
        - برای سطح کاربر (از پروفایل حقیقی) در دسترس است.
        - تاریخ انقضای آن‌ها نگذشته.
        - تعداد استفاده‌شان به سقف نرسیده.
        """,
        tags=['discount-crm']
    )
    def get(self, request, *args, **kwargs):
        try:
            return super().get(request, *args, **kwargs)
        except Exception as exc:
            return Response({
                "error": str(exc),
                "exception_type": exc.__class__.__name__,
                "trace": traceback.format_exc(limit=2)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ✅ API کدهای تخفیف مراکز خرید
class MyShoppingCenterDiscountCodeListView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = ShoppingCenterDiscountCodeSerializer

    def get_queryset(self):
        user = self.request.user
        today_jalali = jdatetime.date.today()

        # دسترسی به سطح کاربر از مدل NaturalProfile
        try:
            user_level = user.natural_profile.level  # دسترسی به سطح کاربر
        except (AttributeError, NaturalProfile.DoesNotExist):
            user_level = None  # در صورتی که پروفایل یا سطح وجود نداشته باشد

        return (
            ShoppingCenterDiscountCode.objects.annotate(
                activated_count=Count('activated_users', distinct=True)
            )
            .filter(
                Q(users=user) | 
                Q(activated_users=user) | 
                Q(user_level=user_level) if user_level else Q(),
                Q(expires_at__isnull=True) | Q(expires_at__gte=today_jalali),
                Q(activated_count__lt=F('usage_limit'))
            )
            .distinct()
        )

    @swagger_auto_schema(
        operation_summary="دریافت کدهای تخفیف مراکز خرید برای کاربر",
        operation_description="""
        این API فقط کدهای معتبر مراکز خرید را برمی‌گرداند:
        - به کاربر اختصاص داده شده یا فعال کرده است.
        - برای سطح کاربر (از پروفایل حقیقی) در دسترس است.
        - تاریخ انقضای آن‌ها نگذشته.
        - تعداد استفاده‌شان به سقف نرسیده.
        """,
        tags=['discount-crm']
    )
    def get(self, request, *args, **kwargs):
        try:
            return super().get(request, *args, **kwargs)
        except Exception as exc:
            return Response({
                "error": str(exc),
                "exception_type": exc.__class__.__name__,
                "trace": traceback.format_exc(limit=2)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ای پی ای فعال سازی کد تخفیف
class ActivateDiscountCodeView(APIView):
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(
        operation_summary="فعال‌سازی کد تخفیف",
        operation_description="""
        این API برای فعال‌سازی یک کد تخفیف توسط کاربر استفاده می‌شود.
        ورودی شامل کد تخفیف و نوع آن (اتاق یا مرکز خرید) است.
        در صورت موفقیت، رکورد فعال‌سازی در سیستم ثبت می‌شود و امتیاز مورد نیاز از حساب مشتری کسر می‌شود.
        """,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'code': openapi.Schema(type=openapi.TYPE_STRING, description='کد تخفیف ۸ رقمی'),
                'discount_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['room', 'shopping_center'], description='نوع کد تخفیف')
            },
            required=['code', 'discount_type']
        ),
        responses={
            200: "کد تخفیف با موفقیت فعال شد",
            400: "ورودی نامعتبر یا کد تخفیف موجود نیست",
            403: "کاربر مجاز به فعال‌سازی نیست یا امتیاز کافی ندارد یا پروفایل کاربری ندارد",
            500: "خطای سرور داخلی"
        },
        tags=['discount-crm']
    )
    def post(self, request, *args, **kwargs):
        user = request.user
        code = request.data.get('code')
        discount_type = request.data.get('discount_type')

        if not code or not discount_type:
            return Response({"error": "کد تخفیف و نوع آن الزامی است"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # بررسی وجود پروفایل کاربر
            try:
                natural_profile = NaturalProfile.objects.get(base_user=user)
            except NaturalProfile.DoesNotExist:
                return Response({"error": "پروفایل کاربری برای این کاربر یافت نشد"}, status=status.HTTP_403_FORBIDDEN)

            # دریافت اطلاعات امتیاز کاربر
            try:
                customer_points = CustomerClubPoint.objects.get(user=user)
            except CustomerClubPointsidesNotExist:
                return Response({"error": "امتیاز باشگاه مشتریان برای این کاربر یافت نشد"}, status=status.HTTP_400_BAD_REQUEST)

            # تابع کمکی برای ایجاد رکورد فعال‌سازی
            def create_activation_record(discount_code):
                kwargs = {
                    "user": user,
                    "discount_type": discount_type,
                    "reward_claimed": True
                }
                if discount_type == "room":
                    kwargs["room_discount_code"] = discount_code
                else:
                    kwargs["shopping_discount_code"] = discount_code
                DiscountActivationRecord.objects.create(**kwargs)

            # منطق فعال‌سازی برای هر نوع کد
            if discount_type == 'room':
                discount_code = RoomDiscountCode.objects.get(code=code)

                # شرط 2: هر کاربر فقط یکبار بتونه استفاده کنه
                if user in discount_code.activated_users.all():
                    return Response({"error": "شما قبلاً از این کد استفاده کرده‌اید"}, status=status.HTTP_403_FORBIDDEN)

                # شرط 1: بررسی تعداد دفعات باقی‌مانده
                if discount_code.usage_limit <= 0:
                    return Response({"error": "حداکثر دفعات استفاده از این کد به پایان رسیده است"}, status=status.HTTP_400_BAD_REQUEST)

                # بررسی مجوز فعال‌سازی (کاربر، کاربران فعال‌شده یا سطح کاربری)
                if (user not in discount_code.users.all() and 
                    user not in discount_code.activated_users.all() and
                    (not discount_code.user_level or natural_profile.level != discount_code.user_level)):
                    return Response({"error": "شما مجاز به فعال‌سازی این کد نیستید"}, status=status.HTTP_403_FORBIDDEN)

                # بقیه چک‌ها
                if discount_code.required_points > 0 and customer_points.points < discount_code.required_points:
                    return Response({"error": "امتیاز کافی برای فعال‌سازی ندارید"}, status=status.HTTP_403_FORBIDDEN)
                if discount_code.expires_at and jdatetime.datetime.now().date() > discount_code.expires_at:
                    return Response({"error": "این کد منقضی شده است"}, status=status.HTTP_400_BAD_REQUEST)

                # کسر امتیاز
                if discount_code.required_points > 0:
                    customer_points.points -= discount_code.required_points
                    customer_points.save()

                # کم کردن تعداد دفعات مجاز
                discount_code.usage_limit -= 1
                discount_code.save()

                # ثبت فعال‌سازی
                discount_code.activated_users.add(user)
                create_activation_record(discount_code)

            elif discount_type == 'shopping_center':
                discount_code = ShoppingCenterDiscountCode.objects.get(code=code)

                if user in discount_code.activated_users.all():
                    return Response({"error": "شما قبلاً از این کد استفاده کرده‌اید"}, status=status.HTTP_403_FORBIDDEN)

                if discount_code.usage_limit <= 0:
                    return Response({"error": "حداکثر دفعات استفاده از این کد به پایان رسیده است"}, status=status.HTTP_400_BAD_REQUEST)

                # بررسی مجوز فعال‌سازی (کاربر، کاربران فعال‌شده یا سطح کاربری)
                if (user not in discount_code.users.all() and 
                    user not in discount_code.activated_users.all() and
                    (not discount_code.user_level or natural_profile.level != discount_code.user_level)):
                    return Response({"error": "شما مجاز به فعال‌سازی این کد نیستید"}, status=status.HTTP_403_FORBIDDEN)

                if discount_code.required_points > 0 and customer_points.points < discount_code.required_points:
                    return Response({"error": "امتیاز کافی برای فعال‌سازی ندارید"}, status=status.HTTP_403_FORBIDDEN)
                if discount_code.expires_at and jdatetime.datetime.now().date() > discount_code.expires_at:
                    return Response({"error": "این کد منقضی شده است"}, status=status.HTTP_400_BAD_REQUEST)

                if discount_code.required_points > 0:
                    customer_points.points -= discount_code.required_points
                    customer_points.save()

                discount_code.usage_limit -= 1
                discount_code.save()

                discount_code.activated_users.add(user)
                create_activation_record(discount_code)

            else:
                return Response({"error": "نوع تخفیف نامعتبر است"}, status=status.HTTP_400_BAD_REQUEST)

            return Response({"message": "کد تخفیف با موفقیت فعال شد"}, status=status.HTTP_200_OK)

        except RoomDiscountCode.DoesNotExist:
            return Response({"error": "کد تخفیف اتاق یافت نشد"}, status=status.HTTP_400_BAD_REQUEST)
        except ShoppingCenterDiscountCode.DoesNotExist:
            return Response({"error": "کد تخفیف مرکز خرید یافت نشد"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({
                "error": str(exc),
                "exception_type": exc.__class__.__name__,
                "trace": traceback.format_exc(limit=2)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ای پی ای جوایز دریافتی کاربران 
class DiscountActivationRecordListView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = DiscountActivationRecordSerializer

    def get_queryset(self):
        user = self.request.user
        return DiscountActivationRecord.objects.filter(user=user).select_related(
            'room_discount_code__room',
            'shopping_discount_code'
        ).order_by('-activated_at')

    @swagger_auto_schema(
        operation_summary="دریافت لیست جوایز فعال شده کاربر برای مرکز خرید و اتاق‌ها",
        operation_description="""
        این API لیست جوایز فعال شده توسط کاربر را بازمی‌گرداند که شامل:
        - کدهای تخفیف اتاق
        - کدهای تخفیف مرکز خرید
        می‌باشد. نتایج بر اساس تاریخ فعال‌سازی به ترتیب نزولی مرتب شده‌اند.
        """,
        tags=['discount-crm'],
        responses={
            200: openapi.Response(
                description="لیست جوایز فعال شده",
                schema=DiscountActivationRecordSerializer(many=True),
                examples={
                    "application/json": [
                        {
                            "id": 1,
                            "user": "user@example.com",
                            "discount_type": "room",
                            "code": "ABC12345",
                            "discount_value": "100,000",
                            "required_points": 500,
                            "activated_at": "2025-08-13T04:40:00+04:00",
                            "reward_claimed": False,
                            "related_info": {
                                "room_id": 1,
                                "room_name": "هتل پارسیان آزادی - اتاق تویین 2"
                            }
                        },
                        {
                            "id": 2,
                            "user": "user@example.com",
                            "discount_type": "shopping_center",
                            "code": "XYZ67890",
                            "discount_value": "50,000",
                            "required_points": 300,
                            "activated_at": "2025-08-12T10:00:00+04:00",
                            "reward_claimed": True,
                            "related_info": {
                                "shopping_center_name": "مرکز خرید پالادیوم"
                            }
                        }
                    ]
                }
            ),
            500: openapi.Response(
                description="خطای سرور داخلی",
                examples={
                    "application/json": {
                        "error": "An error occurred",
                        "exception_type": "Exception",
                        "trace": "Traceback..."
                    }
                }
            )
        }
    )
    def get(self, request, *args, **kwargs):
        try:
            return super().get(request, *args, **kwargs)
        except Exception as exc:
            return Response({
                "error": str(exc),
                "exception_type": exc.__class__.__name__,
                "trace": traceback.format_exc(limit=2)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
            return Response({'points': 0}, status=status.HTTP_200_OK)