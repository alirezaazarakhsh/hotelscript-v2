import traceback
from venv import logger
import jdatetime
from rest_framework.views import APIView
from django.db import transaction
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics
from drf_yasg import openapi
from django.db.models import Count, Q, F
from authentication.models import NaturalProfile
from .models import (
    CustomerClubPoint,
    DiscountActivationRecord,
    HotelDiscountCode,
    RoomDiscountCode,
    ShoppingCenterDiscountCode
)
from .serializers import (
    CustomerClubPointSerializer,
    DiscountActivationRecordSerializer,
    RoomDiscountCodeSerializer,
    ShoppingCenterDiscountCodeSerializer,
    HotelDiscountCodeSerializer
)


# ✅ API کدهای تخفیف اتاق و هتل
class MyRoomDiscountCodeListView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        today_jalali = jdatetime.date.today()

        try:
            user_level = user.natural_profile.level
        except (AttributeError, NaturalProfile.DoesNotExist):
            user_level = None

        # لیست کدهای فعال شده توسط کاربر
        activated_room_codes = DiscountActivationRecord.objects.filter(
            user=user,
            discount_type='room'
        ).values_list('room_discount_code_id', flat=True)

        activated_hotel_codes = DiscountActivationRecord.objects.filter(
            user=user,
            discount_type='hotel'
        ).values_list('hotel_discount_code_id', flat=True)

        # کوئری برای کدهای تخفیف اتاق
        room_discounts = RoomDiscountCode.objects.annotate(
            activated_count=Count('activated_users', distinct=True)
        ).filter(
            ~Q(id__in=activated_room_codes),
            Q(users=user) | (Q(user_level=user_level) if user_level else Q()),
            Q(expires_at__isnull=True) | Q(expires_at__gte=today_jalali),
            remaining_uses__gt=0  # اضافه کردن شرط remaining_uses > 0
        ).select_related('room__hotel')

        # کوئری برای کدهای تخفیف هتل
        hotel_discounts = HotelDiscountCode.objects.annotate(
            activated_count=Count('activated_users', distinct=True)
        ).filter(
            ~Q(id__in=activated_hotel_codes),
            Q(users=user) | (Q(user_level=user_level) if user_level else Q()),
            Q(expires_at__isnull=True) | Q(expires_at__gte=today_jalali),
            remaining_uses__gt=0  # اضافه کردن شرط remaining_uses > 0
        ).select_related('hotel')

        # ترکیب دو کوئری‌ست با استفاده از chain
        from itertools import chain
        return list(chain(room_discounts, hotel_discounts))

    def get_serializer_class(self):
        # Return a default serializer for Swagger documentation
        return RoomDiscountCodeSerializer

    def list(self, request, *args, **kwargs):
        """
        Custom list method to serialize each object with the appropriate serializer.
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serialized_data = []

        if page is not None:
            for obj in page:
                if isinstance(obj, RoomDiscountCode):
                    serializer = RoomDiscountCodeSerializer(obj, context=self.get_serializer_context())
                elif isinstance(obj, HotelDiscountCode):
                    serializer = HotelDiscountCodeSerializer(obj, context=self.get_serializer_context())
                else:
                    continue  # Skip invalid objects
                serialized_data.append(serializer.data)
            return self.get_paginated_response(serialized_data)

        # Non-paginated response
        for obj in queryset:
            if isinstance(obj, RoomDiscountCode):
                serializer = RoomDiscountCodeSerializer(obj, context=self.get_serializer_context())
            elif isinstance(obj, HotelDiscountCode):
                serializer = HotelDiscountCodeSerializer(obj, context=self.get_serializer_context())
            else:
                continue  # Skip invalid objects
            serialized_data.append(serializer.data)

        return Response(serialized_data)

    @swagger_auto_schema(
        operation_summary="دریافت کدهای تخفیف اتاق و هتل برای کاربر",
        operation_description="""
        این API کدهای معتبر اتاق و هتل را برمی‌گرداند که:
        - به کاربر اختصاص داده شده یا با سطح کاربری او مطابقت دارند.
        - کاربر قبلاً آن‌ها را فعال نکرده است.
        - تاریخ انقضای آن‌ها نگذشته.
        - تعداد استفاده‌شان به سقف نرسیده.
        """,
        tags=['discount-crm'],
        responses={
            200: openapi.Response(
                description="لیست کدهای تخفیف",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'discount_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['room', 'hotel']),
                            'code': openapi.Schema(type=openapi.TYPE_STRING),
                            'discount_value': openapi.Schema(type=openapi.TYPE_STRING),
                            'usage_limit': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'remaining_uses': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'required_points': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'user_level': openapi.Schema(type=openapi.TYPE_INTEGER, nullable=True),
                            'created_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                            'expires_at': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                            'activation_rules': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                            'room': openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'title': openapi.Schema(type=openapi.TYPE_STRING),
                                    'hotel_name': openapi.Schema(type=openapi.TYPE_STRING),
                                    'hotel_main_image': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                },
                                nullable=True
                            ),
                            'hotel': openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'hotel_name': openapi.Schema(type=openapi.TYPE_STRING),
                                    'main_image': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                },
                                nullable=True
                            ),
                        }
                    )
                ),
                examples={
                    'application/json': [
                        {
                            'id': 1,
                            'discount_type': 'room',
                            'room': {
                                'id': 1,
                                'title': 'تویین 2',
                                'hotel_name': 'پارسیان آزادی',
                                'hotel_main_image': 'http://example.com/media/hotel_images/image.jpg'
                            },
                            'discount_value': '100000',
                            'code': 'ABC12345',
                            'usage_limit': 10,
                            'remaining_uses': 8,
                            'required_points': 500,
                            'user_level': None,
                            'created_at': '2025-08-13T04:40:00+04:00',
                            'expires_at': '1404-06-22',
                            'activation_rules': None
                        },
                        {
                            'id': 2,
                            'discount_type': 'hotel',
                            'hotel': {
                                'id': 1,
                                'hotel_name': 'پارسیان آزادی',
                                'main_image': 'http://example.com/media/hotel_images/image.jpg'
                            },
                            'discount_value': '200000',
                            'code': 'HOTEL123',
                            'usage_limit': 5,
                            'remaining_uses': 4,
                            'required_points': 1000,
                            'user_level': None,
                            'created_at': '2025-08-11T10:00:00+04:00',
                            'expires_at': '1404-06-20',
                            'activation_rules': None
                        }
                    ]
                }
            ),
            500: openapi.Response(
                description="خطای سرور داخلی",
                examples={
                    'application/json': {
                        'error': 'An error occurred',
                        'exception_type': 'Exception',
                        'trace': 'Traceback...'
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
            


# ✅ API کدهای تخفیف مراکز خرید
class MyShoppingCenterDiscountCodeListView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = ShoppingCenterDiscountCodeSerializer

    def get_queryset(self):
        user = self.request.user
        today_jalali = jdatetime.date.today()

        try:
            user_level = user.natural_profile.level
        except (AttributeError, NaturalProfile.DoesNotExist):
            user_level = None

        activated_codes = DiscountActivationRecord.objects.filter(
            user=user,
            discount_type='shopping_center'
        ).values_list('shopping_discount_code_id', flat=True)

        return ShoppingCenterDiscountCode.objects.filter(
            ~Q(id__in=activated_codes),
            Q(users=user) | (Q(user_level=user_level) if user_level else Q()),
            Q(expires_at__isnull=True) | Q(expires_at__gte=today_jalali)
        ).distinct()

    @swagger_auto_schema(
        operation_summary="دریافت کدهای تخفیف مراکز خرید برای کاربر",
        operation_description="""
        این API فقط کدهای معتبر مراکز خرید را برمی‌گرداند که:
        - به کاربر اختصاص داده شده یا با سطح کاربری او مطابقت دارند.
        - کاربر قبلاً آن‌ها را فعال نکرده است.
        - تاریخ انقضای آن‌ها نگذشته.
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
        ورودی شامل کد تخفیف و نوع آن (اتاق، مرکز خرید یا هتل) است.
        در صورت موفقیت، رکورد فعال‌سازی در سیستم ثبت می‌شود و امتیاز مورد نیاز از حساب مشتری کسر می‌شود.
        """,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'code': openapi.Schema(type=openapi.TYPE_STRING, description='کد تخفیف ۸ رقمی'),
                'discount_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['room', 'shopping_center', 'hotel'], description='نوع کد تخفیف')
            },
            required=['code', 'discount_type']
        ),
        responses={
            200: "کد تخفیف با موفقیت فعال شد",
            400: "ورودی نامعتبر یا کد تخفیف موجود نیست",
            403: "کاربر قبلاً این کد را فعال کرده یا مجاز به فعال‌سازی نیست یا امتیاز کافی ندارد یا پروفایل کاربری ندارد",
            500: "خطای سرور داخلی"
        },
        tags=['discount-crm']
    )
    def post(self, request, *args, **kwargs):
        user = request.user
        code = request.data.get('code', '').strip().upper()
        discount_type = request.data.get('discount_type')

        if not code or not discount_type:
            return Response({"error": "کد تخفیف و نوع آن الزامی است"}, status=status.HTTP_400_BAD_REQUEST)

        logger.info(f"درخواست فعال‌سازی کد تخفیف: کد={code}, نوع={discount_type}, کاربر={user.phone_number}")

        try:
            with transaction.atomic():
                # بررسی پروفایل کاربری
                try:
                    natural_profile = NaturalProfile.objects.get(base_user=user)
                    logger.info(f"پروفایل کاربری یافت شد: سطح={natural_profile.level}")
                except NaturalProfile.DoesNotExist:
                    logger.warning(f"پروفایل کاربری برای کاربر {user.phone_number} یافت نشد")
                    return Response({"error": "پروفایل کاربری برای این کاربر یافت نشد"}, status=status.HTTP_403_FORBIDDEN)

                # دریافت یا ایجاد امتیاز باشگاه مشتریان
                customer_points, created = CustomerClubPoint.objects.get_or_create(
                    user=user,
                    defaults={'points': 0}
                )
                logger.info(f"امتیاز کاربر: {customer_points.points}")

                # پیدا کردن کد تخفیف
                discount_code = None
                error_message = ""
                
                if discount_type == 'room':
                    logger.info(f"جستجوی کد تخفیف اتاق: {code}")
                    try:
                        discount_code = RoomDiscountCode.objects.select_for_update().get(code=code)
                        logger.info(f"کد تخفیف اتاق یافت شد: {discount_code.code}")
                    except RoomDiscountCode.DoesNotExist:
                        error_message = "کد تخفیف اتاق یافت نشد"
                        # لاگ تمام کدهای موجود برای دیباگ
                        all_room_codes = RoomDiscountCode.objects.values_list('code', flat=True)
                        logger.info(f"کدهای تخفیف اتاق موجود: {list(all_room_codes)}")
                
                elif discount_type == 'shopping_center':
                    logger.info(f"جستجوی کد تخفیف مرکز خرید: {code}")
                    try:
                        discount_code = ShoppingCenterDiscountCode.objects.select_for_update().get(code=code)
                        logger.info(f"کد تخفیف مرکز خرید یافت شد: {discount_code.code}")
                    except ShoppingCenterDiscountCode.DoesNotExist:
                        error_message = "کد تخفیف مرکز خرید یافت نشد"
                        # لاگ تمام کدهای موجود برای دیباگ
                        all_shopping_codes = ShoppingCenterDiscountCode.objects.values_list('code', flat=True)
                        logger.info(f"کدهای تخفیف مرکز خرید موجود: {list(all_shopping_codes)}")
                
                elif discount_type == 'hotel':
                    logger.info(f"جستجوی کد تخفیف هتل: {code}")
                    try:
                        discount_code = HotelDiscountCode.objects.select_for_update().get(code=code)
                        logger.info(f"کد تخفیف هتل یافت شد: {discount_code.code}, هتل: {discount_code.hotel.name}")
                    except HotelDiscountCode.DoesNotExist:
                        error_message = "کد تخفیف هتل یافت نشد"
                        # لاگ تمام کدهای موجود برای دیباگ
                        all_hotel_codes = HotelDiscountCode.objects.values_list('code', flat=True)
                        logger.info(f"کدهای تخفیف هتل موجود: {list(all_hotel_codes)}")
                
                else:
                    return Response({"error": "نوع تخفیف نامعتبر است"}, status=status.HTTP_400_BAD_REQUEST)

                # اگر کد تخفیف پیدا نشد
                if not discount_code and error_message:
                    logger.warning(f"کد تخفیف {code} از نوع {discount_type} یافت نشد")
                    return Response({"error": error_message}, status=status.HTTP_400_BAD_REQUEST)

                # بررسی اینکه آیا کاربر قبلاً این کد را فعال کرده است - روش اصلاح شده
                existing_activation = None
                if discount_type == 'room':
                    existing_activation = DiscountActivationRecord.objects.filter(
                        user=user, 
                        room_discount_code=discount_code
                    ).first()
                elif discount_type == 'shopping_center':
                    existing_activation = DiscountActivationRecord.objects.filter(
                        user=user, 
                        shopping_discount_code=discount_code
                    ).first()
                elif discount_type == 'hotel':
                    existing_activation = DiscountActivationRecord.objects.filter(
                        user=user, 
                        hotel_discount_code=discount_code
                    ).first()

                if existing_activation:
                    logger.warning(f"کاربر {user.phone_number} قبلاً کد {discount_code.code} را فعال کرده است. رکورد ID: {existing_activation.id}")
                    logger.info(f"وضعیت reward_claimed: {existing_activation.reward_claimed}")
                    return Response(
                        {"error": "شما قبلاً این کد تخفیف را فعال کرده‌اید و فقط یک‌بار می‌توانید از آن استفاده کنید."},
                        status=status.HTTP_403_FORBIDDEN
                    )

                # بررسی مجوز کاربر - روش ساده‌تر
                if discount_code.users.exists():
                    user_in_targeted = discount_code.users.filter(id=user.id).exists()
                    logger.info(f"کاربر در لیست هدف: {user_in_targeted}")
                    if not user_in_targeted:
                        logger.warning(f"کاربر {user.phone_number} مجاز به فعال‌سازی کد {discount_code.code} نیست")
                        return Response({"error": "شما مجاز به فعال‌سازی این کد نیستید"}, status=status.HTTP_403_FORBIDDEN)
                else:
                    logger.info("کد تخفیف برای همه کاربران قابل استفاده است")

                # بررسی سطح کاربری
                if discount_code.user_level:
                    user_level_match = natural_profile.level == discount_code.user_level
                    logger.info(f"سطح کاربری: کاربر={natural_profile.level}, کد={discount_code.user_level}, مطابقت={user_level_match}")
                    if not user_level_match:
                        logger.warning(f"سطح کاربری {user.phone_number} با کد {discount_code.code} مطابقت ندارد")
                        return Response({"error": "سطح کاربری شما با این کد تخفیف مطابقت ندارد"}, status=status.HTTP_403_FORBIDDEN)
                else:
                    logger.info("کد تخفیف برای همه سطوح کاربری قابل استفاده است")

                # بررسی تاریخ انقضا
                today_jalali = jdatetime.datetime.now().date()
                logger.info(f"تاریخ امروز: {today_jalali}, تاریخ انقضای کد: {discount_code.expires_at}")
                
                if discount_code.expires_at and today_jalali > discount_code.expires_at:
                    logger.warning(f"کد {discount_code.code} منقضی شده است")
                    return Response({"error": "این کد منقضی شده است"}, status=status.HTTP_400_BAD_REQUEST)

                # بررسی دفعات باقی‌مانده
                if hasattr(discount_code, 'remaining_uses'):
                    logger.info(f"دفعات باقی‌مانده کد {discount_code.code}: {discount_code.remaining_uses}")
                    if discount_code.remaining_uses <= 0:
                        logger.warning(f"دفعات استفاده از کد {discount_code.code} به پایان رسیده است")
                        return Response({"error": "دفعات استفاده از این کد به پایان رسیده است"}, status=status.HTTP_400_BAD_REQUEST)

                # بررسی امتیاز مورد نیاز
                logger.info(f"امتیاز مورد نیاز: {discount_code.required_points}, امتیاز کاربر: {customer_points.points}")
                if discount_code.required_points > 0:
                    if customer_points.points < discount_code.required_points:
                        logger.warning(f"امتیاز کاربر {user.phone_number} کافی نیست")
                        return Response(
                            {"error": f"امتیاز کافی برای فعال‌سازی ندارید. امتیاز مورد نیاز: {discount_code.required_points}, امتیاز شما: {customer_points.points}"},
                            status=status.HTTP_403_FORBIDDEN
                        )

                    # کسر امتیاز
                    customer_points.points -= discount_code.required_points
                    customer_points.save(update_fields=['points'])
                    logger.info(f"امتیاز {discount_code.required_points} از کاربر {user.phone_number} برای کد تخفیف {discount_code.code} کسر شد")

                # ایجاد رکورد فعال‌سازی
                activation_data = {
                    "user": user,
                    "discount_type": discount_type,
                    "reward_claimed": False
                }
                
                if discount_type == "room":
                    activation_data["room_discount_code"] = discount_code
                elif discount_type == "shopping_center":
                    activation_data["shopping_discount_code"] = discount_code
                elif discount_type == "hotel":
                    activation_data["hotel_discount_code"] = discount_code

                activation_record = DiscountActivationRecord.objects.create(**activation_data)
                
                logger.info(f"کد تخفیف {discount_code.code} توسط کاربر {user.phone_number} فعال شد. رکورد ID: {activation_record.id}")

                # اطلاعات هتل برای پاسخ
                hotel_info = None
                if discount_type == 'hotel' and hasattr(discount_code, 'hotel'):
                    hotel_info = {
                        'hotel_id': discount_code.hotel.id,
                        'hotel_name': discount_code.hotel.name
                    }
                elif discount_type == 'room' and hasattr(discount_code, 'room'):
                    hotel_info = {
                        'hotel_id': discount_code.room.hotel.id,
                        'hotel_name': discount_code.room.hotel.name
                    }

                return Response({
                    "message": "کد تخفیف با موفقیت فعال شد",
                    "activation_id": activation_record.id,
                    "discount_code": discount_code.code,
                    "discount_type": discount_type,
                    "discount_value": str(discount_code.discount_value),
                    "required_points": discount_code.required_points,
                    "expires_at": discount_code.expires_at.strftime('%Y/%m/%d') if discount_code.expires_at else None,
                    "hotel_info": hotel_info,
                    "remaining_uses": getattr(discount_code, 'remaining_uses', None)
                }, status=status.HTTP_200_OK)

        except Exception as exc:
            logger.error(f"خطا در فعال‌سازی کد تخفیف {code} (نوع: {discount_type}): {str(exc)}")
            logger.error(f"جزئیات خطا: {traceback.format_exc()}")
            return Response({
                "error": "خطا در فعال‌سازی کد تخفیف",
                "exception_type": exc.__class__.__name__,
                "details": str(exc)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ای پی ای جوایز دریافتی کاربران 
class DiscountActivationRecordListView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = DiscountActivationRecordSerializer

    def get_queryset(self):
        user = self.request.user
        return DiscountActivationRecord.objects.filter(user=user).select_related(
            'room_discount_code__room',
            'shopping_discount_code',
            'hotel_discount_code__hotel'
        ).order_by('-activated_at')

    @swagger_auto_schema(
        operation_summary="دریافت لیست جوایز فعال شده کاربر برای مرکز خرید و اتاق‌ها و هتل‌ها",
        operation_description="""
        این API لیست جوایز فعال شده توسط کاربر را بازمی‌گرداند که شامل:
        - کدهای تخفیف اتاق
        - کدهای تخفیف مرکز خرید
        - کدهای تخفیف هتل
        - `expires_at`: تاریخ انقضای کد
        نتایج بر اساس تاریخ فعال‌سازی به ترتیب نزولی مرتب شده‌اند.
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
                            "expires_at": "2025-09-13T04:40:00+04:00",
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
                            "expires_at": "2025-09-12T10:00:00+04:00",
                            "reward_claimed": True,
                            "related_info": {
                                "shopping_center_name": "مرکز خرید پالادیوم"
                            }
                        },
                        {
                            "id": 3,
                            "user": "user@example.com",
                            "discount_type": "hotel",
                            "code": "HOTEL123",
                            "discount_value": "200,000",
                            "required_points": 1000,
                            "activated_at": "2025-08-11T10:00:00+04:00",
                            "expires_at": "2025-09-11T10:00:00+04:00",
                            "reward_claimed": False,
                            "related_info": {
                                "hotel_id": 1,
                                "hotel_name": "هتل پارسیان آزادی"
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