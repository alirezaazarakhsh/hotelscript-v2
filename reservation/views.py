from collections import defaultdict
import itertools
from datetime import datetime, timedelta
import logging
import sys
import json
import traceback
import jdatetime
from rest_framework.views import APIView
from rest_framework.generics import RetrieveUpdateDestroyAPIView
from rest_framework.exceptions import PermissionDenied
from safarname24.pagination import FacilitiesPaginator, RoomFacilitiesPaginator
from .utils import Round
from rest_framework.generics import CreateAPIView
from rest_framework.generics import ListCreateAPIView
from rest_framework import generics


from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from rest_framework import (
    status,
)
from rest_framework.response import Response
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticatedOrReadOnly,
    IsAuthenticated,
)
from rest_framework.generics import (
    ListAPIView,
    RetrieveAPIView,
    ListCreateAPIView,
)
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from django.db import (
    transaction,
)
from django.db.models import (
    Q,
    F,
    Sum,
    Count,
    Avg,
    Case,
    When,
    PositiveBigIntegerField,
)
from django.db.models.functions import Round
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import (
    BestHotels,
    ClosedDate,
    CommentPoint,
    CommentPointItem,
    Hotel,
    Room,
    RoomDate,
    City,
    HotelType,
    Facilities,
    RoomDatePrice,
    RoomFacilities,
    RoomService,
    HotelFAQ,
    NearbyPlace,
    Passenger,
    Comment,
    SuggestedCommentItem,
)
from .serializers import (
    CitySerializer,
    BestHotelsSerializer,
    ClosedDateSerializer,
    CommentSerializer,
    HotelDescriptionSerializer,
    HotelFacilitiesSerializer,
    HotelFurtherDescriptionSerializer,
    HotelGallerySerializer,
    HotelImagesSerializer,
    HotelIntroductionSerializer,
    HotelListSerializer,
    CitySerializer,
    HotelRulesSerializer,
    HotelSearchSerializer,
    HotelTagSerializer,
    HotelTypeSerializer,
    RoomFacilitiesSerializer,
    RoomSerializer,
    RoomServiceSerializer,
    HotelFAQListSerializer,
    NearbyPlaceListSerializer,
    PassengerSerializer,
    FacilitiesSerializer,
    HotelCommentListSerializer,   # اینجا اضافه شد
)


# ای پی ای لیست هتل ها 
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q, Avg, F, Sum, Count
from collections import defaultdict
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import Hotel, RoomDate
from .serializers import HotelListSerializer
from .utils import Round 
from datetime import datetime




# ای پی ای لیست شهر های مربوط یه صفحه اصلی 
class HomePageCityListView(generics.ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = CitySerializer
    pagination_class = None  

    def get_queryset(self):
        return City.objects.filter(show_in_homepage=True).select_related('province')

    @swagger_auto_schema(
        operation_summary="دریافت لیست شهرهای مخصوص صفحه اصلی",
        operation_description="این API فقط شهرهایی را باز می‌گرداند که گزینه 'نمایش در صفحه اصلی' آن‌ها فعال است، همراه با تعداد اقامتگاه‌ها، اسلاگ و تصویر شهر (با URL کامل).",
        responses={
            200: openapi.Response(
                description="لیست شهرهای صفحه اصلی با تعداد اقامتگاه‌ها، اسلاگ و تصویر (با URL کامل)",
                schema=CitySerializer(many=True)
            )
        },
        tags=["home"]
    )
    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        cities_data = [
            {
                "id": city.id,
                 "image": request.build_absolute_uri(city.image.url) if city.image else None,
                "name": city.name,
                "province": city.province.name,
                "slug": city.slug,
                "hotels_number": city.hotels.count(),
               
            }
            for city in queryset
        ]
        return Response(cities_data)

    
    
    
#ای پی ای نوع اقامتگاه
class HotelTypeListView(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = HotelTypeSerializer
    pagination_class = None  
    queryset = HotelType.objects.all()
    # pagination_class = None

    @swagger_auto_schema(
        operation_summary="دریافت لیست نوع اقامتگاه",
        operation_description="این API لیستی از انواع اقامتگاه را بدون صفحه‌بندی باز می‌گرداند.",
        tags=['hotel-filter']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    

 
 

# API دریافت لیست امکانات هتل  و اتاق بر اساس یه هتل خاص 
class HotelFacilitiesView(RetrieveAPIView):
    permission_classes = (AllowAny,)
    serializer_class = HotelFacilitiesSerializer
    lookup_field = 'slug'
    queryset = Hotel.objects.prefetch_related('facilities', 'room_facilities')

    @swagger_auto_schema(
        operation_summary="دریافت امکانات هتل بر اساس اسلاگ",
        operation_description="این API امکانات رفاهی و امکانات داخل اتاق را برای یک هتل خاص (با استفاده از slug) باز می‌گرداند.",
        tags=['hotel']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
 




# ای پی ای لیست خدمات اتاق ها 
class RoomServiceListView(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = RoomServiceSerializer
    queryset = RoomService.objects.all()
    pagination_class = None

    @swagger_auto_schema(
        operation_summary="دریافت لیست خدمات اتاق‌ها",
        operation_description="این API لیستی از خدمات ارائه شده در اتاق‌ها را بدون صفحه‌بندی باز می‌گرداند.",
        tags=['hotel-room']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)





# ای پی ای اتاق ها بر اساس اسلاگ 
# تنظیم لاگ برای دیباگ (با fallback برای جلوگیری از خطا)
try:
    logger = logging.getLogger(__name__)
except Exception:
    def logger_fallback(*args, **kwargs):
        print(*args, file=sys.stderr)
    logger = type('Logger', (), {'info': logger_fallback, 'warning': logger_fallback, 'debug': logger_fallback})()

class HotelRoomsView(generics.RetrieveAPIView):
    permission_classes = (AllowAny,)
    serializer_class = RoomSerializer
    queryset = Hotel.objects.all()
    lookup_field = 'slug'
    lookup_url_kwarg = 'slug'

    def calculate_discount(self, price_data, date, fixed_discount_applied=False):
        """محاسبه مقدار تخفیف و قیمت پس از تخفیف"""
        discount_amount = 0
        price_after_discount = price_data.price if price_data else None
        discount_percentage = None
        discount_date = None

        if price_data and price_data.discount_type != 'none':
            if price_data.discount_type == 'percentage':
                if not price_data.discount_date:
                    logger.error(f"Room {price_data.room.id} on {date}: Percentage discount requires a discount_date")
                    raise ValueError("تخفیف درصدی باید تاریخ انقضا داشته باشد. لطفاً تاریخ انقضا را مشخص کنید.")
                if price_data.discount_date >= date:
                    discount_amount = int(price_data.price * price_data.discount_value / 100)
                    discount_percentage = price_data.discount_value
                    discount_date = price_data.discount_date.strftime('%Y/%m/%d')
                    price_after_discount = int(max(price_data.price - discount_amount, 0))
                else:
                    logger.warning(f"Room {price_data.room.id} on {date}: Discount ignored due to expired discount_date {price_data.discount_date}")
                    price_after_discount = int(price_data.price)
                    discount_percentage = None
                    discount_date = None
            elif price_data.discount_type == 'fixed':
                if price_data.discount_date:
                    logger.error(f"Room {price_data.room.id} on {date}: Fixed discount should not have a discount_date")
                    raise ValueError("تخفیف ثابت نمی‌تواند تاریخ انقضا داشته باشد. لطفاً تاریخ انقضا را برای تخفیف ثابت حذف کنید.")
                if price_data.is_fixed_discount_one_time and fixed_discount_applied:
                    discount_amount = 0
                else:
                    discount_amount = int(price_data.discount_value)
                    fixed_discount_applied = price_data.is_fixed_discount_one_time
                price_after_discount = int(price_data.price)
        else:
            discount_amount = 0

        return discount_amount, price_after_discount, discount_percentage, discount_date, fixed_discount_applied

    @swagger_auto_schema(
        operation_summary="دریافت لیست اتاق‌های هتل به همراه قیمت و تقویم قیمتی",
        operation_description=(
            "این API لیست اتاق‌های هتل مشخص شده توسط slug را به همراه قیمت‌های روزانه، تخفیف‌ها، و وضعیت دسترسی باز می‌گرداند. "
            "اگر پارامتر passengers مشخص نشده باشد، اتاق‌هایی که حداقل یک بازه قیمتی معتبر دارند و موجودی آنها بیشتر از صفر است نمایش داده می‌شوند، همراه با تقویم قیمتی برای بازه پیش‌فرض (امروز تا ۳۰ روز بعد). "
            "اگر passengers مشخص شده باشد (به فرمت [2,3,5])، اتاق‌ها یا پک‌هایی که ظرفیت‌های مشخص شده را دارند نمایش داده می‌شوند، به ترتیب ورودی و مرتب‌شده بر اساس قیمت. "
            "بازه رزرو نمی‌تواند بیشتر از ۳۰ روز باشد و مجموع مسافران نمی‌تواند بیشتر از ۸ نفر یا تعداد اتاق‌ها بیشتر از ۳ باشد.\n\n"
            "پارامترهای ورودی:\n"
            "- slug (اجباری): شناسه slug هتل\n"
            "- start_date (اختیاری): تاریخ شروع به فرمت yyyy-mm-dd\n"
            "- end_date (اختیاری): تاریخ پایان به فرمت yyyy-mm-dd\n"
            "- passengers (اختیاری): لیست ظرفیت‌های اتاق‌ها، به فرمت [2,3,5]، حداکثر ۳ اتاق و مجموع ۸ مسافر\n\n"
            "خروجی:\n"
            "- بدون passengers: لیست اتاق‌هایی که حداقل یک بازه قیمتی دارند با تقویم قیمتی\n"
            "- با passengers: لیست اتاق‌ها یا پک‌های اتاق با ظرفیت‌های مشخص‌شده، مرتب‌شده بر اساس قیمت\n"
            "- در صورت عدم وجود اتاق یا پک: پیام با جزئیات روزهای غیرقابل دسترس\n\n"
            "نکات:\n"
            "- تخفیف‌های درصدی باید تاریخ انقضا (discount_date) داشته باشند.\n"
            "- تخفیف‌های ثابت نباید تاریخ انقضا داشته باشند.\n"
            "- اتاق‌هایی با موجودی صفر در نتایج نمایش داده نمی‌شوند.\n"
            "- وضعیت‌ها فقط شامل 'open' یا 'close' هستند."
        ),
        tags=['hotel-room'],
        manual_parameters=[
            openapi.Parameter(
                name='slug', in_=openapi.IN_PATH, description='شناسه slug هتل', type=openapi.TYPE_STRING, required=True
            ),
            openapi.Parameter(
                name='start_date', in_=openapi.IN_QUERY, description='تاریخ شروع به فرمت yyyy-mm-dd (اختیاری)', type=openapi.TYPE_STRING, required=False
            ),
            openapi.Parameter(
                name='end_date', in_=openapi.IN_QUERY, description='تاریخ پایان به فرمت yyyy-mm-dd (اختیاری)', type=openapi.TYPE_STRING, required=False
            ),
            openapi.Parameter(
                name='passengers', in_=openapi.IN_QUERY, description='لیست ظرفیت‌های اتاق‌ها، به فرمت [2,3,5]، حداکثر ۳ اتاق و مجموع ۸ مسافر', type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_INTEGER), required=False
            ),
        ],
        responses={
            200: "لیست اتاق‌ها یا پک‌های اتاق با یا بدون فیلتر",
            400: "خطا در پارامترهای ورودی یا تنظیمات تخفیف",
            404: "هیچ اتاق یا پکی با موجودی یافت نشد"
        }
    )
    def get(self, request, *args, **kwargs):
        hotel = self.get_object()
        logger.info(f"Processing request for hotel {hotel.slug}")

        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        passengers = request.query_params.get('passengers')

        has_filters = any([start_date, end_date, passengers])

        persian_days = ['شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنجشنبه', 'جمعه']
        persian_months = ['فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور', 'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند']
        default_user_level = "میهمان"

        # Parse passengers parameter
        passengers_list = []
        if passengers:
            try:
                # Remove square brackets and split by comma
                passengers_clean = passengers.strip('[]').split(',')
                passengers_list = [int(p) for p in passengers_clean if p.strip()]
                if not passengers_list:
                    return Response({'detail': 'پارامتر passengers باید حداقل یک عدد صحیح داشته باشد.'}, status=400)
                if len(passengers_list) > 3:
                    return Response({'detail': 'تعداد اتاق‌ها نمی‌تواند بیشتر از ۳ باشد.'}, status=400)
                if sum(passengers_list) > 8:
                    return Response({'detail': 'مجموع مسافران نمی‌تواند بیشتر از ۸ نفر باشد.'}, status=400)
                if any(p <= 0 for p in passengers_list):
                    return Response({'detail': 'ظرفیت هر اتاق باید بیشتر از صفر باشد.'}, status=400)
            except ValueError:
                return Response({'detail': 'پارامتر passengers باید به فرمت [2,3,5] و شامل اعداد صحیح باشد.'}, status=400)

        if not has_filters:
            start_date_obj = jdatetime.date.today()
            end_date_obj = start_date_obj + jdatetime.timedelta(days=30)
            rooms_qs = hotel.rooms.filter(date_prices__isnull=False, inventory__gt=0).distinct().prefetch_related('date_prices', 'services').select_related('hotel')
            logger.info(f"No filters applied, found {rooms_qs.count()} rooms with price data and inventory > 0, using default range {start_date_obj} to {end_date_obj}")

            date_range = [start_date_obj + jdatetime.timedelta(days=i) for i in range((end_date_obj - start_date_obj).days)]
            night_count = (end_date_obj - start_date_obj).days

            room_data = []
            room_dict = {}
            for room in rooms_qs:
                room_services = ", ".join([service.title for service in room.services.all()]) or "خدمات ندارد"
                closed = ClosedDate.objects.filter(
                    room_date__room=room,
                    date__range=(start_date_obj, end_date_obj)
                ).select_related('room_date')

                price_calendar = []
                fixed_discount_applied = False

                for date in date_range:
                    price_data = room.date_prices.filter(
                        start_date__lte=date,
                        end_date__gte=date
                    ).order_by('-id').select_related('user_level').first()

                    closed_date = closed.filter(date=date).first()
                    status = "open"

                    if not price_data or closed_date:
                        status = "close"

                    try:
                        discount_amount, price_after_discount, discount_percentage, discount_date, fixed_discount_applied = self.calculate_discount(price_data, date, fixed_discount_applied)
                    except ValueError as e:
                        return Response({'detail': str(e)}, status=400)

                    price_calendar.append({
                        "date": date.strftime('%Y/%m/%d'),
                        "month": persian_months[date.month - 1],
                        "day": persian_days[date.weekday()],
                        "status": status,
                        "price": {
                            "price": price_data.price if price_data else None,
                            "price_after_discount": price_after_discount,
                            "discount_percentage": discount_percentage,
                            "discount_amount": discount_amount,
                            "discount_date": discount_date,
                            "is_fixed_discount_one_time": price_data.is_fixed_discount_one_time if price_data else False,
                            "user_level": price_data.user_level.title if price_data and price_data.user_level else default_user_level,
                            "extra_capacity_price": price_data.extra_passenger_price if price_data else 0
                        } if status == "open" else None
                    })

                first_price_data = room.date_prices.filter(
                    start_date__lte=start_date_obj,
                    end_date__gte=start_date_obj
                ).order_by('-id').select_related('user_level').first()

                if not first_price_data:
                    logger.info(f"Room {room.id} skipped: No valid price data in default range")
                    continue

                try:
                    discount_amount, price_after_discount_first, discount_percentage_first, discount_date_first, _ = self.calculate_discount(first_price_data, start_date_obj, False)
                except ValueError as e:
                    return Response({'detail': str(e)}, status=400)

                total_price = sum(
                    day['price']['price'] for day in price_calendar 
                    if day['status'] == "open" and day['price'] and day['price']['price'] is not None
                )
                total_price_discount = sum(
                    day['price']['price_after_discount'] for day in price_calendar 
                    if day['status'] == "open" and day['price'] and day['price']['price_after_discount'] is not None
                )

                room_dict[room.id] = {
                    "id": room.id,
                    "name": room.title or "",
                    "descriptions": room.description or "",
                    "room_number": room.inventory or 0,
                    "customer_club_points": room.customer_club_points or 0,
                    "room_services": room_services,
                    "accept_need": room.count or 0,
                    "dont_accept_need": room.auto_approved_count or 0,
                    "hotel": room.hotel.id,
                    "hotel_name": str(room.hotel) or "",
                    "capacity": room.room_capacity,
                    "extra_capacity": room.extra_capacity,
                    "price": {
                        "total_price": total_price,
                        "total_price_discount": total_price_discount,
                        "discount_percentage": discount_percentage_first,
                        "discount_amount": discount_amount,
                        "discount_date": discount_date_first,
                        "is_fixed_discount_one_time": first_price_data.is_fixed_discount_one_time,
                        "user_level": first_price_data.user_level.title if first_price_data.user_level else default_user_level,
                        "extra_capacity_price": first_price_data.extra_passenger_price
                    },
                    "night_count": night_count,
                    "price_calendar": price_calendar
                }

            room_data = list(room_dict.values())

            if not room_data:
                logger.warning(f"No rooms with price data and inventory > 0 found for hotel {hotel.slug}")
                return Response({
                    'detail': 'هیچ اتاقی با داده قیمتی و موجودی برای این هتل یافت نشد.',
                    'rooms': [],
                    'price_calendar': [
                        {"date": (start_date_obj + jdatetime.timedelta(days=i)).strftime('%Y/%m/%d'), "status": "close"}
                        for i in range((end_date_obj - start_date_obj).days)
                    ]
                }, status=200)

            return Response(room_data)

        try:
            start_date_obj = jdatetime.date.today() if not start_date else jdatetime.date(*map(int, start_date.split('-')))
            if end_date:
                end_date_obj = jdatetime.date(*map(int, end_date.split('-')))
                if start_date_obj > end_date_obj:
                    return Response({'detail': 'تاریخ شروع نمی‌تواند بعد از تاریخ پایان باشد.'}, status=400)
                if (end_date_obj - start_date_obj).days > 30:
                    return Response({'detail': 'بازه رزرو نمی‌تواند بیشتر از ۳۰ روز باشد.'}, status=400)
            else:
                end_date_obj = start_date_obj + jdatetime.timedelta(days=30)
        except Exception:
            return Response({'detail': 'فرمت تاریخ باید yyyy-mm-dd باشد.'}, status=400)

        logger.info(f"Applying filters: passengers={passengers}, start_date={start_date}, end_date={end_date}")

        rooms_qs = hotel.rooms.filter(
            date_prices__start_date__lte=end_date_obj,
            date_prices__end_date__gte=start_date_obj,
            inventory__gt=0,
        ).distinct().prefetch_related('date_prices', 'services').select_related('hotel')
        logger.info(f"Found {rooms_qs.count()} rooms with inventory > 0 and valid price data")

        date_range = [start_date_obj + jdatetime.timedelta(days=i) for i in range((end_date_obj - start_date_obj).days)]
        night_count = (end_date_obj - start_date_obj).days

        room_data = []
        room_dict = {}

        for room in rooms_qs:
            room_services = ", ".join([service.title for service in room.services.all()]) or "خدمات ندارد"
            closed = ClosedDate.objects.filter(
                room_date__room=room,
                date__range=(start_date_obj, end_date_obj)
            ).select_related('room_date')

            price_calendar = []
            fixed_discount_applied = False

            for date in date_range:
                price_data = room.date_prices.filter(
                    start_date__lte=date,
                    end_date__gte=date
                ).order_by('-id').select_related('user_level').first()

                closed_date = closed.filter(date=date).first()
                status = "open"

                if not price_data or closed_date:
                    status = "close"
                    logger.debug(f"Room {room.id} on {date}: {'No price data' if not price_data else 'Closed by admin'}")

                try:
                    discount_amount, price_after_discount, discount_percentage, discount_date, fixed_discount_applied = self.calculate_discount(price_data, date, fixed_discount_applied)
                except ValueError as e:
                    return Response({'detail': str(e)}, status=400)

                price_calendar.append({
                    "date": date.strftime('%Y/%m/%d'),
                    "month": persian_months[date.month - 1],
                    "day": persian_days[date.weekday()],
                    "status": status,
                    "price": {
                        "price": price_data.price if price_data else None,
                        "price_after_discount": price_after_discount,
                        "discount_percentage": discount_percentage,
                        "discount_amount": discount_amount,
                        "discount_date": discount_date,
                        "is_fixed_discount_one_time": price_data.is_fixed_discount_one_time if price_data else False,
                        "user_level": price_data.user_level.title if price_data and price_data.user_level else default_user_level,
                        "extra_capacity_price": price_data.extra_passenger_price if price_data else 0
                    } if status == "open" else None
                })

            first_price_data = room.date_prices.filter(
                start_date__lte=start_date_obj,
                end_date__gte=start_date_obj
            ).order_by('-id').select_related('user_level').first()
            if not first_price_data:
                logger.info(f"Room {room.id} skipped: No valid first_price_data")
                continue

            try:
                discount_amount, price_after_discount_first, discount_percentage_first, discount_date_first, _ = self.calculate_discount(first_price_data, start_date_obj, False)
            except ValueError as e:
                return Response({'detail': str(e)}, status=400)

            total_price = sum(
                day['price']['price'] for day in price_calendar 
                if day['status'] == "open" and day['price'] and day['price']['price'] is not None
            )
            total_price_discount = sum(
                day['price']['price_after_discount'] for day in price_calendar 
                if day['status'] == "open" and day['price'] and day['price']['price_after_discount'] is not None
            )

            room_dict[room.id] = {
                "id": room.id,
                "name": room.title or "",
                "descriptions": room.description or "",
                "room_number": room.inventory or 0,
                "customer_club_points": room.customer_club_points or 0,
                "room_services": room_services,
                "accept_need": room.count or 0,
                "dont_accept_need": room.auto_approved_count or 0,
                "hotel": room.hotel.id,
                "hotel_name": str(room.hotel) or "",
                "capacity": room.room_capacity,
                "extra_capacity": room.extra_capacity,
                "price": {
                    "total_price": total_price,
                    "total_price_discount": total_price_discount,
                    "discount_percentage": discount_percentage_first,
                    "discount_amount": discount_amount,
                    "discount_date": discount_date_first,
                    "is_fixed_discount_one_time": first_price_data.is_fixed_discount_one_time,
                    "user_level": first_price_data.user_level.title if first_price_data.user_level else default_user_level,
                    "extra_capacity_price": first_price_data.extra_passenger_price
                },
                "night_count": night_count,
                "price_calendar": price_calendar
            }

        room_data = list(room_dict.values())

        if not room_data:
            price_calendar = [
                {"date": (start_date_obj + jdatetime.timedelta(days=i)).strftime('%Y/%m/%d'), "status": "close"}
                for i in range((end_date_obj - start_date_obj).days)
            ]
            logger.warning(f"No rooms found after filtering for hotel {hotel.slug}")
            return Response({
                'detail': 'اتاقی با موجودی در بازه انتخابی یافت نشد.',
                'price_calendar': price_calendar
            }, status=404)

        if not passengers_list:
            return Response(room_data)

        # Filter rooms based on passengers list
        if len(passengers_list) == 1:
            # Single room case: filter rooms with capacity >= passengers_list[0]
            filtered_rooms = [
                room for room in room_data
                if room['capacity'] + room['extra_capacity'] >= passengers_list[0]
            ]
            if not filtered_rooms:
                price_calendar = [
                    {"date": (start_date_obj + jdatetime.timedelta(days=i)).strftime('%Y/%m/%d'), "status": "close"}
                    for i in range((end_date_obj - start_date_obj).days)
                ]
                logger.warning(f"No rooms found with capacity >= {passengers_list[0]} for hotel {hotel.slug}")
                return Response({
                    'detail': f'اتاقی با ظرفیت {passengers_list[0]} یافت نشد.',
                    'price_calendar': price_calendar
                }, status=404)
            filtered_rooms.sort(key=lambda x: x['price']['total_price_discount'])
            return Response(filtered_rooms)

        # Pack case: create packs matching the exact order of passengers_list
        packs = []
        valid_combinations = []

        # Generate all possible combinations of rooms matching the passengers_list
        for combo in itertools.permutations(room_data, len(passengers_list)):
            valid = True
            for i, capacity in enumerate(passengers_list):
                if combo[i]['capacity'] + combo[i]['extra_capacity'] < capacity:
                    valid = False
                    break
            if valid:
                valid_combinations.append(combo)

        for combo in valid_combinations:
            pack_rooms = list(combo)
            room_ids = [r['id'] for r in pack_rooms]
            logger.info(f"Evaluating pack with rooms {room_ids} for passengers {passengers_list}")

            if all(r['room_number'] > 0 for r in pack_rooms):
                pack_total_price = sum(r['price']['total_price_discount'] for r in pack_rooms)
                packs.append({
                    "pack_rooms": [
                        {
                            "id": r['id'],
                            "name": r['name'],
                            "descriptions": r['descriptions'],
                            "room_number": r['room_number'],
                            "customer_club_points": r['customer_club_points'],
                            "room_services": r['room_services'],
                            "accept_need": r['accept_need'],
                            "dont_accept_need": r['dont_accept_need'],
                            "hotel": r['hotel'],
                            "hotel_name": r['hotel_name'],
                            "capacity": r['capacity'],
                            "extra_capacity": r['extra_capacity'],
                            "price": r['price'],
                            "night_count": r['night_count'],
                            "price_calendar": r['price_calendar']
                        } for r in pack_rooms
                    ],
                    "total_price": pack_total_price,
                    "night_count": night_count,
                    "room_count": len(pack_rooms)
                })

        if not packs:
            price_calendar = [
                {"date": (start_date_obj + jdatetime.timedelta(days=i)).strftime('%Y/%m/%d'), "status": "close"}
                for i in range((end_date_obj - start_date_obj).days)
            ]
            logger.warning(f"No packs formed for hotel {hotel.slug}, passengers={passengers_list}")
            return Response({
                'detail': f'پک مناسب با ظرفیت‌های {passengers_list} یافت نشد.',
                'price_calendar': price_calendar
            }, status=404)

        packs.sort(key=lambda x: x['total_price'])
        return Response(packs)







#دریافت تصاویر شاخص و ۴ عکس صفحه داخلی هتل 
class HotelImagesView(RetrieveAPIView):
    permission_classes = (AllowAny,)
    serializer_class = HotelImagesSerializer
    queryset = Hotel.objects.all()
    lookup_field = 'slug'
    lookup_url_kwarg = 'slug'

    @swagger_auto_schema(
        operation_summary="دریافت تصاویر هتل",
        operation_description="این API تصاویر اصلی هتل را بر اساس slug باز می‌گرداند.",
        tags=['hotel'],
        manual_parameters=[
            openapi.Parameter(
                name='slug',
                in_=openapi.IN_PATH,
                description='شناسه slug هتل',
                type=openapi.TYPE_STRING,
                required=True,
            ),
        ],
        responses={
            200: HotelImagesSerializer,
            404: 'هتل پیدا نشد.'
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    





#دریافت توضیحات هتل برای صفحه جزئیات 
class HotelDescriptionView(RetrieveAPIView):
    permission_classes = (AllowAny,)
    serializer_class = HotelDescriptionSerializer
    queryset = Hotel.objects.all()
    lookup_field = 'slug'
    lookup_url_kwarg = 'slug'

    @swagger_auto_schema(
        operation_summary="دریافت توضیحات هتل",
        operation_description="این API توضیحات کلی هتل را بر اساس slug باز می‌گرداند.",
        tags=['hotel'],
        manual_parameters=[
            openapi.Parameter(
                name='slug',
                in_=openapi.IN_PATH,
                description='شناسه slug هتل',
                type=openapi.TYPE_STRING,
                required=True,
            ),
        ],
        responses={
            200: HotelDescriptionSerializer,
            404: 'هتل پیدا نشد.'
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    
    
    
    
    
#ای پی ای معرفی هتل در صفحه جزئیات هتل 
class HotelIntroductionView(RetrieveAPIView):
    permission_classes = (AllowAny,)
    serializer_class = HotelIntroductionSerializer
    queryset = Hotel.objects.select_related('best_logo').all()
    lookup_field = 'slug'
    lookup_url_kwarg = 'slug'

    @swagger_auto_schema(
        operation_summary="دریافت معرفی هتل",
        operation_description="این API اطلاعات معرفی هتل شامل ستاره، آدرس، زمان چک‌این و چک‌اوت و لوگو را باز می‌گرداند.",
        tags=['hotel'],
        manual_parameters=[
            openapi.Parameter(
                name='slug',
                in_=openapi.IN_PATH,
                description='شناسه slug هتل',
                type=openapi.TYPE_STRING,
                required=True,
            ),
        ],
        responses={
            200: HotelIntroductionSerializer,
            404: 'هتل پیدا نشد.'
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)






# ای پی ای دریافت توضیحات تکمیلی هتل در صفجه جزئیات 
class HotelFurtherDescriptionView(RetrieveAPIView):
    permission_classes = (AllowAny,)
    serializer_class = HotelFurtherDescriptionSerializer
    queryset = Hotel.objects.all()
    lookup_field = 'slug'
    lookup_url_kwarg = 'slug'

    @swagger_auto_schema(
        operation_summary="دریافت توضیحات تکمیلی هتل",
        operation_description="این API توضیحات تکمیلی هتل را بر اساس slug باز می‌گرداند.",
        tags=['hotel'],
        manual_parameters=[
            openapi.Parameter(
                name='slug',
                in_=openapi.IN_PATH,
                description='شناسه slug هتل',
                type=openapi.TYPE_STRING,
                required=True,
            ),
        ],
        responses={
            200: HotelFurtherDescriptionSerializer,
            404: 'هتل پیدا نشد.'
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)







#ای پی ای نکات ضروری و قوانین هتل در صفحه جزئیات
class HotelRulesView(RetrieveAPIView):
    permission_classes = (AllowAny,)
    serializer_class = HotelRulesSerializer
    queryset = Hotel.objects.all()
    lookup_field = 'slug'
    lookup_url_kwarg = 'slug'

    @swagger_auto_schema(
        operation_summary="دریافت قوانین و نکات مهم هتل",
        operation_description="این API قوانین هتل و نکات مهم را با توجه به slug باز می‌گرداند.",
        tags=['hotel'],
        manual_parameters=[
            openapi.Parameter(
                name='slug',
                in_=openapi.IN_PATH,
                description='شناسه slug هتل',
                type=openapi.TYPE_STRING,
                required=True,
            ),
        ],
        responses={
            200: HotelRulesSerializer,
            404: 'هتل پیدا نشد.'
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


    
    
    
    
# ای پی ای سوالات متداول هتل 
class HotelFAQListView(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = HotelFAQListSerializer
    pagination_class = None

    def get_queryset(self):
        hotel_slug = self.kwargs.get('slug')
        queryset = HotelFAQ.objects.filter(hotel__slug=hotel_slug)
        return queryset

    @swagger_auto_schema(
        operation_summary="دریافت سوالات متداول هتل",
        operation_description="این API لیستی از سوالات متداول مربوط به هتل با slug مشخص شده را باز می‌گرداند.",
        tags=['hotel'],
        manual_parameters=[
            openapi.Parameter(
                name='slug',
                in_=openapi.IN_PATH,
                description='شناسه slug هتل برای دریافت سوالات متداول',
                type=openapi.TYPE_STRING,
                required=True,
            ),
        ],
        responses={
            200: HotelFAQListSerializer(many=True),
            404: 'هتل یا سوالات متداول پیدا نشد.'
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    
    
    
    
    
#ای پی ای امکانات هتل 
class HotelFacilitiesListView(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = FacilitiesSerializer


    def get_queryset(self):
        hotel_slug = self.kwargs.get('slug')
        queryset = Facilities.objects.filter(hotels__slug=hotel_slug).order_by('id')
        return queryset

    @swagger_auto_schema(
        operation_summary="دریافت امکانات هتل",
        operation_description="این API لیستی از امکانات هتل با slug مشخص شده را باز می‌گرداند.",
        tags=['hotel'],
        manual_parameters=[
            openapi.Parameter(
                name='slug',
                in_=openapi.IN_PATH,
                description='شناسه slug هتل برای دریافت امکانات',
                type=openapi.TYPE_STRING,
                required=True,
            ),
        ],
        responses={
            200: FacilitiesSerializer(many=True),
            404: 'هتل یا امکانات مرتبط پیدا نشد.'
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    
    




# ای پی ای دریافت امکانات اتاق های هتل
class HotelRoomFacilitiesListView(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = RoomFacilitiesSerializer

    def get_queryset(self):
        hotel_slug = self.kwargs.get('slug')
        queryset = RoomFacilities.objects.filter(hotels__slug=hotel_slug).order_by('id')
        return queryset

    @swagger_auto_schema(
        operation_summary="دریافت امکانات اتاق‌های هتل",
        operation_description="این API لیستی از امکانات اتاق‌های هتل با slug مشخص شده را باز می‌گرداند.",
        tags=['hotel'],
        manual_parameters=[
            openapi.Parameter(
                name='slug',
                in_=openapi.IN_PATH,
                description='شناسه slug هتل برای دریافت امکانات اتاق‌ها',
                type=openapi.TYPE_STRING,
                required=True,
            ),
        ],
        responses={
            200: RoomFacilitiesSerializer(many=True),
            404: 'هتل یا امکانات اتاق مربوطه پیدا نشد.'
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    
    
    
    
    
    

# ای پی ای مکان های اطراف هتل 
class HotelNearbyPlaceListView(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = NearbyPlaceListSerializer
    pagination_class = None


    def get_queryset(self):
        hotel_slug = self.kwargs.get('slug')
        queryset = NearbyPlace.objects.filter(hotel__slug=hotel_slug).order_by('id')
        return queryset

    @swagger_auto_schema(
        operation_summary="دریافت مکان‌های نزدیک به هتل",
        operation_description="این API لیستی از مکان‌های نزدیک به هتل با slug مشخص شده را باز می‌گرداند.",
        tags=['hotel'],
        manual_parameters=[
            openapi.Parameter(
                name='slug',
                in_=openapi.IN_PATH,
                description='شناسه slug هتل برای دریافت مکان‌های نزدیک',
                type=openapi.TYPE_STRING,
                required=True,
            ),
        ],
        responses={
            200: NearbyPlaceListSerializer(many=True),
            404: 'هتل یا مکان‌های نزدیک پیدا نشد.'
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
        
    
    
    
    
# ای پی ای ثبت مسافر جدید 
class PassengerListCreateView(generics.ListCreateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = PassengerSerializer

    def get_queryset(self):
        return Passenger.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @swagger_auto_schema(
        tags=["Passenger-user"],
        operation_summary="لیست مسافران",
        operation_description="لیست تمام مسافران ثبت‌شده توسط کاربر جاری را بازمی‌گرداند.",
        responses={200: PassengerSerializer(many=True)}
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

    @swagger_auto_schema(
        tags=["Passenger-user"],
        operation_summary="ثبت مسافر جدید",
        operation_description="اطلاعات یک مسافر جدید را ثبت می‌کند و آن را به کاربر جاری متصل می‌کند.",
        request_body=PassengerSerializer,
        responses={201: PassengerSerializer()}
    )
    def post(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as exc:
            return Response({
                "error": str(exc),
                "exception_type": exc.__class__.__name__,
                "trace": traceback.format_exc(limit=2)
            }, status=status.HTTP_400_BAD_REQUEST)






# ای پی ای حذف و ویرایش مسافران
class PassengerRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = PassengerSerializer
    queryset = Passenger.objects.all()

    def get_object(self):
        obj = super().get_object()
        if obj.user != self.request.user:
            raise PermissionDenied("شما اجازه دسترسی به این مسافر را ندارید.")
        return obj

    def perform_update(self, serializer):
        # اطمینان از اینکه user تغییر نمی‌کند
        serializer.save(user=self.request.user)

    @swagger_auto_schema(
        tags=["Passenger-user"],
        operation_summary="ویرایش جزئی مسافر",
        operation_description="اطلاعات مسافر را به‌صورت جزئی ویرایش می‌کند. فیلدهای نام و نام خانوادگی ضروری هستند.",
        request_body=PassengerSerializer,
        responses={200: PassengerSerializer()}
    )
    def patch(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            data = request.data.copy()
            data.pop('id', None)  # ID تغییر نکند
            
            # اطمینان از وجود نام و نام خانوادگی در درخواست
            if not data.get('first_name') or not data.get('last_name'):
                return Response({
                    "error": "نام و نام خانوادگی ضروری هستند."
                }, status=status.HTTP_400_BAD_REQUEST)
                
            serializer = self.get_serializer(instance, data=data, partial=True)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data)
        except Exception as exc:
            return Response({
                "error": str(exc),
                "exception_type": exc.__class__.__name__,
                "trace": traceback.format_exc(limit=2)
            }, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        tags=["Passenger-user"],
        operation_summary="حذف یک مسافر",
        operation_description="یک مسافر خاص را حذف می‌کند.",
        responses={204: "Deleted successfully"}
    )
    def delete(self, request, *args, **kwargs):
        try:
            self.get_object().delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as exc:
            return Response({
                "error": str(exc),
                "exception_type": exc.__class__.__name__,
                "trace": traceback.format_exc(limit=2)
            }, status=status.HTTP_400_BAD_REQUEST)





# ای پی ای اضافه کردن لوگوی برترین هتل های صفجه اصلی 
class BestHotelsListCreateView(ListCreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = BestHotelsSerializer
    pagination_class = None 
    

    def get_queryset(self):
        """
        بازگرداندن لیست بهترین هتل‌ها به ترتیب.
        """
        return BestHotels.objects.all().order_by('order')

    @swagger_auto_schema(
        operation_summary="لیست برترین هتل های صفحه اصلی ",
        operation_description="""
        این API به کاربر اجازه می‌دهد تا:
        - لیست بهترین هتل‌ها را مشاهده کند
        - یک هتل جدید به لیست اضافه کند
                """,
        responses={
            200: BestHotelsSerializer(many=True),
            201: BestHotelsSerializer(),
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="ثبت لوگوی برترین هتل",
        operation_description="""
        با استفاده از این api می توانید لوگوی جدیدی از هتل را برترین هتل های صفحه اصلی اضافه کنید 
        """,
        request_body=BestHotelsSerializer,
        responses={201: BestHotelsSerializer()}
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
        





#ای پی ای هتل های پیشنهادی + شگفت انگیز + پرفروش  صفحه اول 
class HomeHotelListView(APIView):
    permission_classes = (AllowAny,)

    def get_average_score(self, hotel):
        """محاسبه میانگین کل امتیازات یک هتل"""
        comments = Comment.objects.filter(hotel=hotel, is_approved=True)
        if not comments.exists():
            return 0.0
        all_points = CommentPoint.objects.filter(comment__in=comments)
        overall_average = all_points.aggregate(avg=Avg("point"))["avg"]
        return round(overall_average or 0, 1)

    def get_hotel_min_price_map(self, hotels):
        """محاسبه کمترین قیمت و اطلاعات تخفیف برای هر هتل"""
        today = timezone.now().date()
        hotel_min_price_map = {}
        
        for hotel in hotels:
            rooms = Room.objects.filter(hotel=hotel)
            min_price = None
            min_price_data = {}

            for room in rooms:
                prices = RoomDatePrice.objects.filter(
                    room=room,
                    start_date__lte=today,
                    end_date__gte=today
                ).select_related('room')

                for price in prices:
                    original_price = price.price
                    total_price = original_price

                    if price.discount_type == 'percentage' and price.discount_date and price.discount_date >= today:
                        total_price = original_price * (1 - price.discount_value / 100)
                    elif price.discount_type == 'fixed' and price.is_fixed_discount_one_time:
                        total_price = original_price - price.discount_value

                    if min_price is None or total_price < min_price:
                        min_price = total_price
                        min_price_data = {
                            'total_price': int(total_price),
                            'original_total_price': int(original_price),
                            'discount_type': price.discount_type,
                            'discount_value': price.discount_value,
                            'discount_date': price.discount_date
                        }

            if min_price_data:
                hotel_min_price_map[hotel.id] = min_price_data

        return hotel_min_price_map

    @swagger_auto_schema(
        operation_summary="دریافت لیست هتل‌های پیشنهادی + شگفت انگیز + پرفروش‌ترین در صفحه اصلی ",
        operation_description="این API لیستی از هتل‌های پیشنهادی ویژه، شگفت‌انگیز و پرفروش را بدون صفحه‌بندی باز می‌گرداند.",
        tags=['hotel-home'],
        responses={
            200: openapi.Response(
                description="لیست هتل‌ها",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'special_offers': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_OBJECT)),
                        'flash_sales': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_OBJECT)),
                        'best_sellers': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_OBJECT)),
                    }
                )
            )
        }
    )
    def get(self, request, *args, **kwargs):
        hotels = Hotel.objects.filter(
            Q(is_special_offer=True) | 
            Q(is_flash_sale=True) | 
            Q(is_best_seller=True)
        ).select_related('city', 'type').distinct()

        hotel_min_price_map = self.get_hotel_min_price_map(hotels)
        context = {'hotel_min_price_map': hotel_min_price_map, 'request': request}

        special_offers_data = []
        flash_sales_data = []
        best_sellers_data = []

        for hotel in hotels.filter(is_special_offer=True):
            serialized = HotelListSerializer(hotel, context=context).data
            serialized['average_score'] = self.get_average_score(hotel)
            special_offers_data.append(serialized)

        for hotel in hotels.filter(is_flash_sale=True):
            serialized = HotelListSerializer(hotel, context=context).data
            serialized['average_score'] = self.get_average_score(hotel)
            flash_sales_data.append(serialized)

        for hotel in hotels.filter(is_best_seller=True):
            serialized = HotelListSerializer(hotel, context=context).data
            serialized['average_score'] = self.get_average_score(hotel)
            best_sellers_data.append(serialized)

        response_data = {
            'special_offers': special_offers_data,
            'flash_sales': flash_sales_data,
            'best_sellers': best_sellers_data
        }

        return Response(response_data)
    
    



# ای پی ای پیشنهاد هتل ها در صفحه داخلی هتل بر اساس شهر 
class HomeHotelByCityView(APIView):
    permission_classes = (AllowAny,)

    def get_average_score(self, hotel):
        """محاسبه میانگین کل امتیازات یک هتل"""
        comments = Comment.objects.filter(hotel=hotel, is_approved=True)
        if not comments.exists():
            return 0.0
        all_points = CommentPoint.objects.filter(comment__in=comments)
        overall_average = all_points.aggregate(avg=Avg("point"))["avg"]
        return round(overall_average or 0, 1)

    def get_hotel_min_price_map(self, hotels):
        """محاسبه کمترین قیمت و اطلاعات تخفیف برای هر هتل"""
        today = timezone.now().date()
        hotel_min_price_map = {}

        for hotel in hotels:
            rooms = Room.objects.filter(hotel=hotel)
            min_price = None
            min_price_data = {}

            for room in rooms:
                prices = RoomDatePrice.objects.filter(
                    room=room,
                    start_date__lte=today,
                    end_date__gte=today
                ).select_related('room')

                for price in prices:
                    original_price = price.price
                    total_price = original_price

                    if price.discount_type == 'percentage' and price.discount_date and price.discount_date >= today:
                        total_price = original_price * (1 - price.discount_value / 100)
                        discount_percentage = price.discount_value
                    elif price.discount_type == 'fixed' and price.is_fixed_discount_one_time:
                        total_price = original_price - price.discount_value
                        discount_percentage = (price.discount_value / original_price) * 100 if original_price > 0 else 0
                    else:
                        discount_percentage = 0.0

                    if min_price is None or total_price < min_price:
                        min_price = total_price
                        min_price_data = {
                            'total_price': int(total_price),
                            'original_total_price': int(original_price),
                            'discount_type': price.discount_type,
                            'discount_value': price.discount_value,
                            'discount_date': price.discount_date,
                            'discount_percentage': round(discount_percentage, 1)
                        }

            if min_price_data:
                hotel_min_price_map[hotel.id] = min_price_data

        return hotel_min_price_map

    @swagger_auto_schema(
        operation_summary="دریافت لیست هتل‌ها بر اساس نام شهر در صفحه داخلی هتل",
        operation_description="این API لیستی از هتل‌های یک شهر خاص را بر اساس نام شهر (فارسی یا لاتین) بازمی‌گرداند. اگر شهر یافت نشود، خطای 404 برگردانده می‌شود.",
        tags=['hotel'],
        manual_parameters=[
            openapi.Parameter(
                'city_name',
                openapi.IN_PATH,
                description="نام شهر (مثال: تهران)",
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        responses={
            200: openapi.Response(
                description="لیست هتل‌ها برای شهر مشخص‌شده",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'name': openapi.Schema(type=openapi.TYPE_STRING, description="نام هتل"),
                            'slug': openapi.Schema(type=openapi.TYPE_STRING, description="اسلاگ هتل"),
                            'city': openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_INTEGER, description="شناسه شهر"),
                                    'image': openapi.Schema(type=openapi.TYPE_STRING, description="لینک تصویر شهر"),
                                    'name': openapi.Schema(type=openapi.TYPE_STRING, description="نام شهر"),
                                    'province': openapi.Schema(type=openapi.TYPE_STRING, description="نام استان"),
                                    'slug': openapi.Schema(type=openapi.TYPE_STRING, description="اسلاگ شهر"),
                                    'hotels_number': openapi.Schema(type=openapi.TYPE_INTEGER, description="تعداد هتل‌ها"),
                                    'show_in_homepage': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="نمایش در صفحه اصلی"),
                                }
                            ),
                            'address': openapi.Schema(type=openapi.TYPE_STRING, description="آدرس هتل"),
                            'main_image': openapi.Schema(type=openapi.TYPE_STRING, description="تصویر اصلی هتل"),
                            'stars': openapi.Schema(type=openapi.TYPE_INTEGER, description="تعداد ستاره‌های هتل"),
                            'type': openapi.Schema(type=openapi.TYPE_STRING, description="نوع اقامتگاه"),
                            'is_special_offer': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="آیا پیشنهاد ویژه است"),
                            'is_flash_sale': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="آیا فروش فوری است"),
                            'is_best_seller': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="آیا پرفروش است"),
                            'original_total_price': openapi.Schema(type=openapi.TYPE_INTEGER, description="قیمت اصلی"),
                            'total_price': openapi.Schema(type=openapi.TYPE_INTEGER, description="قیمت نهایی با تخفیف"),
                            'rating': openapi.Schema(type=openapi.TYPE_NUMBER, description="امتیاز کلی هتل"),
                            'discount_percentage': openapi.Schema(type=openapi.TYPE_NUMBER, description="درصد تخفیف"),
                            'discount_expiry': openapi.Schema(type=openapi.TYPE_STRING, nullable=True, description="تاریخ انقضای تخفیف"),
                            'reservation_count': openapi.Schema(type=openapi.TYPE_INTEGER, description="تعداد رزروها"),
                            'average_score': openapi.Schema(type=openapi.TYPE_NUMBER, description="میانگین امتیاز کاربران"),
                        }
                    )
                )
            ),
            404: openapi.Response(
                description="شهر یافت نشد",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING, description="پیام خطا")
                    }
                )
            )
        }
    )
    def get(self, request, city_name, *args, **kwargs):
        try:
            city_name = city_name.strip()
            city = City.objects.get(name=city_name)
            hotels = Hotel.objects.filter(city=city).select_related('city', 'type').distinct()
            hotel_min_price_map = self.get_hotel_min_price_map(hotels)
            context = {'hotel_min_price_map': hotel_min_price_map, 'request': request}

            serialized_hotels = []
            for hotel in hotels:
                serialized = HotelListSerializer(hotel, context=context).data
                serialized['average_score'] = self.get_average_score(hotel)
                serialized_hotels.append(serialized)

            return Response(serialized_hotels)
        except City.DoesNotExist:
            return Response({'error': 'City not found'}, status=404)
        
        
        
        
        

#ای پی ای لیست هتل برای سرچ صفحه اول 
class HotelSearchAPI(ListCreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = HotelSearchSerializer

    def get_queryset(self):
        query = self.request.query_params.get('query', '').lower()
        if query:
            # وقتی کوئری وجود دارد، هم هتل‌ها و هم شهرها جستجو می‌شوند
            hotels = Hotel.objects.filter(name__icontains=query).select_related('city__province')
            cities = City.objects.filter(name__icontains=query).select_related('province')
        else:
            # در حالت دیفالت، فقط ۱۰ شهر اول (بر اساس ID) و هیچ هتلی
            hotels = Hotel.objects.none()  # هیچ هتلی برنمی‌گرداند
            cities = City.objects.all().select_related('province')[:10]  # فقط ۱۰ شهر
        return {"hotels": hotels, "cities": cities}

    def perform_create(self, serializer):
        pass

    @swagger_auto_schema(
        operation_summary="جستجوی هتل و شهر در کادر جستجوی هتل در صفحات اول و دیگر صفحات",
        operation_description="جستجوی هتل‌ها و شهرها بر اساس نام واردشده در پارامتر query. در حالت دیفالت (بدون کوئری)، فقط ۱۰ شهر اول نمایش داده می‌شود.",
        tags=["hotel-home"],
        manual_parameters=[
            openapi.Parameter(
                name='query',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description='نام هتل یا شهر برای جستجو',
                required=False
            )
        ],
        responses={
            200: openapi.Response(
                description="نتایج جستجوی هتل‌ها و شهرها",
                schema=HotelSearchSerializer
            )
        }
    )
    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        hotels_data = [
            {
                "id": hotel.id,
                "name": hotel.name,
                "city": {
                    "id": hotel.city.id,
                    "name": hotel.city.name,
                    "province": {"name": hotel.city.province.name},
                    "slug": hotel.city.slug
                },
                "slug": hotel.slug,
                "stars": hotel.stars  # تغییر به مقدار واقعی stars
            }
            for hotel in queryset["hotels"]
        ]
        cities_data = [
            {
                "id": city.id,
                "name": city.name,
                "province": {"name": city.province.name},
                "slug": city.slug,
                "hotels_number": city.hotels.count()
            }
            for city in queryset["cities"]
        ]
        return Response({"cities": cities_data, "hotels": hotels_data})

    
    
    
    
    
# مدل برچسب های هتل بر اساس اسلاگ هتل 
class HotelTagsView(RetrieveAPIView):
    permission_classes = (AllowAny,)
    serializer_class = HotelTagSerializer
    queryset = Hotel.objects.all()
    lookup_field = 'slug'
    lookup_url_kwarg = 'slug'

    @swagger_auto_schema(
        operation_summary="دریافت برچسب‌های هتل",
        operation_description="این API برچسب‌های مربوط به هتل را بر اساس slug باز می‌گرداند.",
        tags=['hotel'],
        manual_parameters=[
            openapi.Parameter(
                name='slug',
                in_=openapi.IN_PATH,
                description='شناسه slug هتل',
                type=openapi.TYPE_STRING,
                required=True,
            ),
        ],
        responses={
            200: HotelTagSerializer(many=True),
            404: 'هتل پیدا نشد.'
        }
    )
    def get(self, request, *args, **kwargs):
        hotel = self.get_object()  # هتل بر اساس slug
        tags = hotel.tags.all()    # فرض بر این است که هتل برچسب دارد
        serializer = self.get_serializer(tags, many=True)
        return Response(serializer.data)
    
    
    
    
    

    
    
#ای پی ای گالری تصاویر هتل 
class HotelGalleryView(RetrieveAPIView):
    permission_classes = (AllowAny,)
    serializer_class = HotelGallerySerializer
    queryset = Hotel.objects.all()
    lookup_field = 'slug'
    lookup_url_kwarg = 'slug'

    @swagger_auto_schema(
        operation_summary="دریافت گالری تصاویر هتل",
        operation_description="این API گالری‌های تصویری مربوط به یک هتل را بر اساس slug بازمی‌گرداند. هر گالری شامل عنوان و لیست تصاویر با ترتیب نمایش است.",
        tags=['hotel'],
        manual_parameters=[
            openapi.Parameter(
                name='slug',
                in_=openapi.IN_PATH,
                description='شناسه slug هتل',
                type=openapi.TYPE_STRING,
                required=True,
            ),
        ],
        responses={
            200: HotelGallerySerializer(many=True),
            404: 'هتل پیدا نشد.'
        }
    )
    def get(self, request, *args, **kwargs):
        hotel = self.get_object()
        galleries = hotel.galleries.all()
        serializer = self.get_serializer(galleries, many=True)
        return Response(serializer.data)
    
    
    
    
    
    
    
    
#دریافت لیست نظرات کاربران بر اساس اسلاگ هتل 
class HotelCommentsBySlugView(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = HotelCommentListSerializer
    pagination_class = None

    def get_queryset(self):
        slug = self.kwargs.get('slug')
        hotel = Hotel.objects.filter(slug=slug).first()
        if hotel:
            return Comment.objects.filter(hotel=hotel, is_approved=True).order_by('-created')
        return Comment.objects.none()

    @swagger_auto_schema(
        operation_summary="لیست نظرات تایید شده یک هتل با اسلاگ",
        tags=["comment-hotel"],
        manual_parameters=[
            openapi.Parameter(
                'slug', openapi.IN_PATH,
                description="اسلاگ هتل",
                type=openapi.TYPE_STRING
            )
        ]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    
    
    
    
    
    
#ای پی ای معیار امتیازدهی کامنت ها 
# class HotelCommentPointsBySlugView(APIView):
#     permission_classes = [AllowAny]

#     @swagger_auto_schema(
#         operation_summary="دریافت امتیازهای نظرات هتل با اسلاگ (تفکیک‌شده برای هر کامنت)",
#         tags=["comment-hotel"],
#         responses={200: openapi.Response('امتیازهای تفکیک‌شده')}
#     )
#     def get(self, request, slug):
#         hotel = Hotel.objects.filter(slug=slug).first()
#         if not hotel:
#             return Response([], status=200)

#         comments = Comment.objects.filter(hotel=hotel, is_approved=True)
#         data = []

#         for comment in comments:
#             points = CommentPoint.objects.filter(comment=comment)
#             serialized_points = CommentPointSerializer(points, many=True).data
#             data.append({
#                 "comment_id": comment.id,
#                 "user_id": comment.user.id if comment.user else None,
#                 "user_first_name": comment.user.first_name if comment.user else None,
#                 "user_last_name": comment.user.last_name if comment.user else None,
#                 "points": serialized_points
#             })

#         return Response(data)






#محاسبه میانگین معیار های امتیاز دهی کامنت ها بر اساس هر هتل 
class HotelCommentPointSummaryView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="میانگین امتیازهای داده‌شده به بخش‌های مختلف هتل بر اساس اسلاگ",
        tags=["comment-hotel"],
        responses={200: openapi.Response("میانگین‌ها به تفکیک آیتم و امتیاز کلی")}
    )
    def get(self, request, slug):
        hotel = Hotel.objects.filter(slug=slug).first()
        if not hotel:
            return Response({"detail": "Hotel not found"}, status=404)

        comments = Comment.objects.filter(hotel=hotel, is_approved=True)
        if not comments.exists():
            return Response({
                "average_score": 0.0,
                "items": []
            })

        # فقط امتیازهای بیشتر از ۰ رو بیار
        all_points = CommentPoint.objects.filter(comment__in=comments, point__gt=0)

        items = (
            all_points
            .values("comment_point_item__id", "comment_point_item__title")
            .annotate(average=Avg("point"))
            .order_by("comment_point_item__id")
        )

        # میانگین کلی از همه امتیازهای بالاتر از صفر
        overall_average = all_points.aggregate(avg=Avg("point"))["avg"]

        data = {
            "average_score": round(overall_average or 0, 1),
            "items": [
                {
                    "id": item["comment_point_item__id"],
                    "title": item["comment_point_item__title"],
                    "average": round(item["average"], 1) if item["average"] else 0.0
                }
                for item in items
            ]
        }

        return Response(data)

        
    
    
    
    
    

# ای پی ای لیست های پیشنهاد ها و نظرات منفی و مثبت 
class CommentPointsAndSuggestionsView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="لیست معیارهای امتیازدهی و آیتم‌های پیشنهاد شده برای کامنت‌های هتل",
        tags=["comment-hotel"],
        responses={
            200: openapi.Response(
                description="لیست آیتم‌ها",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'comment_point_items': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'title': openapi.Schema(type=openapi.TYPE_STRING),
                                    'is_positive': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                    'is_negative': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                }
                            )
                        ),
                        'suggested_comment_items': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'title': openapi.Schema(type=openapi.TYPE_STRING),
                                }
                            )
                        ),
                    }
                )
            )
        }
    )
    def get(self, request):
        comment_point_items = CommentPointItem.objects.all().values('id', 'title', 'is_positive', 'is_negative')
        suggested_comment_items = SuggestedCommentItem.objects.all().values('id', 'title')

        data = {
            "comment_point_items": list(comment_point_items),
            "suggested_comment_items": list(suggested_comment_items),
        }

        return Response(data)




comment_create_manual_params = [
    openapi.Parameter(
        name='slug',
        in_=openapi.IN_PATH,
        type=openapi.TYPE_STRING,
        description='اسلاگ هتل',
        required=True
    )
]



#ای پی ای ارسال کامنت توسط کاربر برای هتل
class CreateCommentView(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CommentSerializer

    def get_queryset(self):
        hotel = get_object_or_404(Hotel, slug=self.kwargs['slug'])
        return Comment.objects.filter(hotel=hotel, is_approved=True).order_by('-created')

    def perform_create(self, serializer):
        hotel = get_object_or_404(Hotel, slug=self.kwargs['slug'])
        serializer.save(user=self.request.user, hotel=hotel)

    @swagger_auto_schema(
        operation_summary="ایجاد کامنت برای هتل",
        operation_description="ارسال کامنت جدید برای یک هتل مشخص با slug. فقط کاربران احراز هویت‌شده مجاز هستند.",
        tags=["comment-hotel"],
        manual_parameters=comment_create_manual_params,
        request_body=CommentSerializer,
        responses={
            201: openapi.Response(
                description="کامنت با موفقیت ثبت شد",
                schema=CommentSerializer
            )
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
    
    
    
    
    
# ای پی ای صفحه بهترین هتل ها 
class BestHotelspageAPI(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="دریافت لیست بهترین هتل‌ها با فیلترهای مختلف",
        operation_description="این API لیست هتل‌های موجود را با توجه به فیلترهای شهر، تاریخ شروع، تاریخ پایان، تعداد مسافران، تعداد اتاق‌ها، ستاره‌ها، محدوده قیمت، نوع اقامتگاه و فیلترهای دیگر (مانند امکانات) بازمی‌گرداند.",
        tags=["best-hotel"],
    )
    def get(self, request):
        city = request.query_params.get('city')
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        passenger_count = request.query_params.get('passenger_count')
        room_count = request.query_params.get('room_count')
        star = request.query_params.get('star')
        min_price = request.query_params.get('min_price')
        max_price = request.query_params.get('max_price')
        residence_type = request.query_params.get('residence_type')
        other_filters = request.query_params.get('other_filters')

        # اعداد رو هندل کنیم
        try:
            passenger_count = int(passenger_count) if passenger_count else None
            room_count = int(room_count) if room_count else None
            star = int(star) if star else None
            min_price = int(min_price) if min_price else None
            max_price = int(max_price) if max_price else None
        except ValueError:
            return Response({'detail': 'مقادیر عددی باید صحیح باشند.'}, status=400)

        # هتل‌ها
        hotels_qs = Hotel.objects.all().select_related('city__province').prefetch_related(
            'facilities', 'tags', 'room_facilities'
        )

        if city:
            hotels_qs = hotels_qs.filter(city__slug=city.lower())
        if star:
            hotels_qs = hotels_qs.filter(stars=star)
        if residence_type:
            residence_types = [int(x) for x in residence_type.split(',')]
            hotels_qs = hotels_qs.filter(type__id__in=residence_types)
        if other_filters:
            facility_ids = [int(x) for x in other_filters.split(',')]
            hotels_qs = hotels_qs.filter(
                Q(facilities__id__in=facility_ids) |
                Q(room_facilities__id__in=facility_ids) |
                Q(tags__id__in=facility_ids)
            ).distinct()

        if not hotels_qs.exists():
            return Response({'detail': 'هیچ هتلی یافت نشد.'}, status=404)

        # تاریخ‌ها
        start_date_obj = end_date_obj = None
        if start_date_str or end_date_str:
            try:
                start_date_obj = jdatetime.date.today() if not start_date_str else jdatetime.date(*map(int, start_date_str.split('/')))
                end_date_obj = jdatetime.date(*map(int, end_date_str.split('/'))) if end_date_str else start_date_obj

                if start_date_obj > end_date_obj:
                    return Response({'detail': 'تاریخ شروع نمی‌تواند بعد از تاریخ پایان باشد.'}, status=400)
                nights = (end_date_obj - start_date_obj).days
                if nights < 1:
                    return Response({'detail': 'حداقل یک شب الزامی است.'}, status=400)
            except ValueError:
                return Response({'detail': 'فرمت تاریخ باید yyyy/mm/dd باشد.'}, status=400)

        # محاسبه قیمت هر هتل
        hotel_min_price_map = {}
        for hotel in hotels_qs:
            original_price = 0
            total_price = 0
            discount_type = None
            discount_value = 0
            discount_date = None

            if start_date_obj and end_date_obj:
                room_prices = RoomDatePrice.objects.filter(
                    room__hotel=hotel,
                    start_date__lte=end_date_obj,
                    end_date__gte=start_date_obj,
                    room__inventory__gt=0
                ).order_by('price')

                if not room_prices.exists():
                    continue

                rp = room_prices.first()
                original_price = rp.price
                discount_type = rp.discount_type
                discount_value = rp.discount_value
                discount_date = rp.discount_date

                if discount_type == 'percentage':
                    total_price = rp.price - (rp.price * discount_value / 100)
                elif discount_type == 'fixed':
                    total_price = rp.price - discount_value
                else:
                    total_price = rp.price
            else:
                # اگر تاریخ انتخاب نشده باشه قیمت رو صفر نذاریم
                total_price = 0

            # فیلتر قیمت
            if min_price and total_price < min_price:
                continue
            if max_price and total_price > max_price:
                continue

            hotel_min_price_map[hotel.id] = {
                "original_total_price": original_price,
                "total_price": total_price,
                "discount_type": discount_type,
                "discount_value": discount_value,
                "discount_date": discount_date,
            }

        if not hotel_min_price_map:
            return Response({'detail': 'هیچ هتلی برای این فیلترها یافت نشد.'}, status=404)

        # پاس دادن دیتا به سریالایزر
        serializer = HotelListSerializer(
            hotels_qs.filter(id__in=hotel_min_price_map.keys()),
            many=True,
            context={"request": request, "hotel_min_price_map": hotel_min_price_map},
        )
        return Response(serializer.data)
