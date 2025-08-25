from collections import defaultdict
import itertools
from datetime import datetime, timedelta
import logging
import math
import sys
import json
import traceback
import copy
import jdatetime
from rest_framework.views import APIView
from rest_framework.generics import RetrieveUpdateDestroyAPIView
from rest_framework.exceptions import PermissionDenied
from authentication import serializers
from safarname24.pagination import FacilitiesPaginator, RoomFacilitiesPaginator
from .utils import Round
from rest_framework.generics import CreateAPIView
from rest_framework.generics import ListCreateAPIView
from rest_framework import generics
from rest_framework import serializers  # Explicit import from rest_framework
from django.db.models import Prefetch



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
    Min,
    Prefetch,
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
    HotelTag,
    HotelTagPublic,
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
    FacilitySerializer,
    HotelDescriptionSerializer,
    HotelFacilitiesSerializer,
    HotelFurtherDescriptionSerializer,
    HotelGallerySerializer,
    HotelImagesSerializer,
    HotelIntroductionSerializer,
    HotelListSerializer,
    CitySerializer,
    HotelPriceRangeSerializer,
    HotelRulesSerializer,
    HotelSearchSerializer,
    HotelTagPublicSerializer,
    HotelTagSerializer,
    HotelTypeSerializer,
    RoomFacilitiesSerializer,
    RoomFacilitiesSimpleSerializer,
    RoomSerializer,
    RoomServiceSerializer,
    HotelFAQListSerializer,
    NearbyPlaceListSerializer,
    PassengerSerializer,
    FacilitiesSerializer,
    HotelCommentListSerializer,  
    
    
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
 





# ای پی ای امکانات رفاهی تفریحی به صورت کلی 
class AllFacilitiesView(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = FacilitySerializer
    queryset = Facilities.objects.all()
    pagination_class = None  

    @swagger_auto_schema(
        operation_summary=" امکانات هتل",
        operation_description="این API لیست تمام امکانات هتل را برای شما باز می گرداند بدون صفحه بندی.",
        tags=['best-hotel']
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
                if not price_data.discount_date or price_data.discount_date <= date:
                    # اگر تاریخ انقضا وجود نداشته باشه یا به تاریخ فعلی رسیده/عبور کرده باشه، تخفیف برداشته می‌شه
                    price_after_discount = price_data.price
                else:
                    # اگر هنوز تایمر مونده، تخفیف اعمال می‌شه
                    discount_amount = int(price_data.price * price_data.discount_value / 100)
                    discount_percentage = price_data.discount_value
                    discount_date = price_data.discount_date.strftime('%Y/%m/%d')
                    price_after_discount = int(max(price_data.price - discount_amount, 0))
            elif price_data.discount_type == 'fixed':
                if price_data.discount_date:
                    logger.error(f"Room {price_data.room.id} on {date}: Fixed discount should not have a discount_date")
                    raise ValueError("تخفیف ثابت نمی‌تواند تاریخ انقضا داشته باشد. لطفاً تاریخ انقضا را برای تخفیف ثابت حذف کنید.")
                if price_data.is_fixed_discount_one_time and fixed_discount_applied:
                    discount_amount = 0
                else:
                    discount_amount = int(price_data.discount_value)
                    fixed_discount_applied = price_data.is_fixed_discount_one_time
                price_after_discount = int(max(price_data.price - discount_amount, 0))
        else:
            discount_amount = 0

        return discount_amount, price_after_discount, discount_percentage, discount_date, fixed_discount_applied

    @swagger_auto_schema(
        operation_summary="دریافت لیست اتاق‌های هتل به همراه قیمت و تقویم قیمتی",
        tags=['hotel-room'],
        manual_parameters=[
            openapi.Parameter(name='slug', in_=openapi.IN_PATH, description='شناسه slug هتل', type=openapi.TYPE_STRING, required=True),
            openapi.Parameter(name='start-date', in_=openapi.IN_QUERY, description='تاریخ شروع به فرمت yyyy-mm-dd (اختیاری)', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter(name='end-date', in_=openapi.IN_QUERY, description='تاریخ پایان به فرمت yyyy-mm-dd (اختیاری)', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter(name='passengers', in_=openapi.IN_QUERY, description='لیست ظرفیت‌های اتاق‌ها، به فرمت [2,3,5] یا 0 برای نمایش همه، حداکثر ۳ اتاق و مجموع ۸ مسافر', type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_INTEGER), required=False),
        ]
    )
    def get(self, request, *args, **kwargs):
        hotel = self.get_object()
        logger.info(f"Processing request for hotel {hotel.slug}")

        start_date = request.query_params.get('start-date')
        end_date = request.query_params.get('end-date')
        passengers = request.query_params.get('passengers')

        # Parse passengers parameter
        passengers_list = []
        if passengers:
            try:
                passengers_clean = passengers.strip('[]').split(',')
                passengers_list = [int(p) for p in passengers_clean if p.strip()]
                if not passengers_list:
                    return Response({'detail': 'پارامتر passengers باید حداقل یک عدد صحیح داشته باشد.'}, status=400)
                if passengers_list == [0]:  # Handle passengers=[0] to return all rooms
                    passengers_list = []
                elif len(passengers_list) > 3:
                    return Response({'detail': 'تعداد اتاق‌ها نمی‌تواند بیشتر از ۳ باشد.'}, status=400)
                elif sum(passengers_list) > 8:
                    return Response({'detail': 'مجموع مسافران نمی‌تواند بیشتر از ۸ نفر باشد.'}, status=400)
                elif any(p < 0 for p in passengers_list):
                    return Response({'detail': 'ظرفیت هر اتاق نمی‌تواند منفی باشد.'}, status=400)
            except ValueError:
                return Response({'detail': 'پارامتر passengers باید به فرمت [2,3,5] یا 0 و شامل اعداد صحیح باشد.'}, status=400)

        try:
            start_date_obj = jdatetime.date.today() if not start_date else jdatetime.date(*map(int, start_date.split('-')))
            end_date_obj = jdatetime.date(*map(int, end_date.split('-'))) if end_date else start_date_obj + jdatetime.timedelta(days=30)
            if start_date_obj > end_date_obj:
                return Response({'detail': 'تاریخ شروع نمی‌تواند بعد از تاریخ پایان باشد.'}, status=400)
            if start_date_obj == end_date_obj:
                return Response({'detail': 'بازه رزرو نمی‌تواند صفر شب باشد.'}, status=400)
            if (end_date_obj - start_date_obj).days > 30:
                return Response({'detail': 'بازه رزرو نمی‌تواند بیشتر از ۳۰ روز باشد.'}, status=400)
        except Exception:
            return Response({'detail': 'فرمت تاریخ باید yyyy-mm-dd باشد.'}, status=400)

        persian_days = ['شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنجشنبه', 'جمعه']
        persian_months = ['فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور', 'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند']
        default_user_level = "میهمان"

        # Filter rooms to ensure they are available for the entire date range
        rooms_qs = hotel.rooms.filter(
            date_prices__start_date__lte=start_date_obj,
            date_prices__end_date__gte=end_date_obj,
            inventory__gt=0
        ).distinct().prefetch_related('date_prices', 'services').select_related('hotel')

        date_range = [start_date_obj + jdatetime.timedelta(days=i) for i in range((end_date_obj - start_date_obj).days)]
        night_count = (end_date_obj - start_date_obj).days

        room_dict = {}
        for room in rooms_qs:
            room_services = ", ".join([s.title for s in room.services.all()]) or "خدمات ندارد"
            closed_dates = ClosedDate.objects.filter(room_date__room=room, date__range=(start_date_obj, end_date_obj))
            price_calendar = []
            fixed_discount_applied = False

            for date in date_range:
                price_data = room.date_prices.filter(start_date__lte=date, end_date__gte=date).order_by('-id').select_related('user_level').first()
                closed_date = closed_dates.filter(date=date).first()
                status = "open" if price_data and not closed_date else "close"

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

            first_price_data = room.date_prices.filter(start_date__lte=start_date_obj, end_date__gte=start_date_obj).order_by('-id').select_related('user_level').first()
            if not first_price_data:
                continue

            try:
                discount_amount, price_after_discount_first, discount_percentage_first, discount_date_first, _ = self.calculate_discount(first_price_data, start_date_obj, False)
            except ValueError as e:
                return Response({'detail': str(e)}, status=400)

            total_price = sum(day['price']['price'] for day in price_calendar if day['status'] == "open" and day['price'])
            # Only apply percentage discounts to total_price_discount
            total_price_discount = sum(
                day['price']['price_after_discount'] if day['status'] == "open" and day['price'] and day['price']['discount_percentage'] is not None else
                day['price']['price'] for day in price_calendar if day['status'] == "open" and day['price']
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

        if not passengers_list:
            room_data.sort(key=lambda x: x['price']['total_price_discount'] or float('inf'))
            return Response(room_data)

        # --- Single room ---
        if len(passengers_list) == 1:
            required_capacity = passengers_list[0]
            filtered_rooms = [r for r in room_data if r['capacity'] <= required_capacity <= r['capacity'] + r['extra_capacity']]
            if not filtered_rooms:
                price_calendar = [{"date": (start_date_obj + jdatetime.timedelta(days=i)).strftime('%Y/%m/%d'), "status": "close"} for i in range(night_count)]
                return Response({'detail': f'اتاقی با ظرفیت {required_capacity} یافت نشد.', 'price_calendar': price_calendar}, status=404)
            
            for room in filtered_rooms:
                if required_capacity > room['capacity']:
                    extra_passengers = required_capacity - room['capacity']
                    extra_price_per_night = room['price']['extra_capacity_price']
                    for day in room['price_calendar']:
                        if day['status'] == "open" and day['price']:
                            day['price']['price'] += extra_passengers * extra_price_per_night
                            day['price']['price_after_discount'] += extra_passengers * extra_price_per_night if day['price']['discount_percentage'] is None else 0
                    room['price']['total_price'] = sum(day['price']['price'] for day in room['price_calendar'] if day['status'] == "open" and day['price'])
                    room['price']['total_price_discount'] = sum(
                        day['price']['price_after_discount'] if day['price']['discount_percentage'] is not None else
                        day['price']['price'] for day in room['price_calendar'] if day['status'] == "open" and day['price']
                    )
                
                room['selected_passenger'] = required_capacity
            
            filtered_rooms.sort(key=lambda x: x['price']['total_price_discount'] or float('inf'))
            return Response(filtered_rooms)

        # --- Pack rooms ---
        packs = []
        passengers_list.sort()
        room_candidates = {}
        for p in set(passengers_list):
            room_candidates[p] = [r for r in room_data if r['capacity'] <= p <= r['capacity'] + r['extra_capacity'] and r['room_number'] > 0]

        def generate_packs(current_pack, remaining_groups, used_rooms):
            if not remaining_groups:
                pack_total_price = 0
                pack_rooms = []
                for orig_room, p in current_pack:
                    room = copy.deepcopy(orig_room)
                    if p > room['capacity']:
                        extra_passengers = p - room['capacity']
                        extra_price_per_night = room['price']['extra_capacity_price']
                        for day in room['price_calendar']:
                            if day['status'] == "open" and day['price']:
                                day['price']['price'] += extra_passengers * extra_price_per_night
                                day['price']['price_after_discount'] += extra_passengers * extra_price_per_night if day['price']['discount_percentage'] is None else 0
                        room['price']['total_price'] = sum(day['price']['price'] for day in room['price_calendar'] if day['status'] == "open" and day['price'])
                        room['price']['total_price_discount'] = sum(
                            day['price']['price_after_discount'] if day['price']['discount_percentage'] is not None else
                            day['price']['price'] for day in room['price_calendar'] if day['status'] == "open" and day['price']
                        )
                    room['selected_passenger'] = p
                    pack_rooms.append(room)
                    pack_total_price += room['price']['total_price_discount']
                packs.append({
                    "pack_rooms": pack_rooms,
                    "total_price": pack_total_price,
                    "night_count": night_count,
                    "room_count": len(current_pack)
                })
                return

            p = remaining_groups[0]
            for room in room_candidates.get(p, []):
                room_id = room['id']
                used_count = used_rooms.get(room_id, 0)
                if used_count < room['room_number']:
                    new_used = used_rooms.copy()
                    new_used[room_id] = used_count + 1
                    generate_packs(current_pack + [(room, p)], remaining_groups[1:], new_used)

        generate_packs([], passengers_list, {})

        if not packs:
            price_calendar = [{"date": (start_date_obj + jdatetime.timedelta(days=i)).strftime('%Y/%m/%d'), "status": "close"} for i in range(night_count)]
            return Response({'detail': f'پک مناسب با ظرفیت‌های {passengers_list} یافت نشد.', 'price_calendar': price_calendar}, status=404)

        seen = set()
        unique_packs = []
        for pack in packs:
            key = tuple(sorted((r['id'], r['selected_passenger']) for r in pack['pack_rooms']))
            if key not in seen:
                seen.add(key)
                unique_packs.append(pack)

        unique_packs.sort(key=lambda x: x['total_price'])
        return Response(unique_packs)
    
    
    

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
    
    
    
    

#ای پی ای امکانات اتاق ها به صورت کلی 
class AllRoomFacilitiesView(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = RoomFacilitiesSimpleSerializer
    queryset = RoomFacilities.objects.all().order_by('id')
    pagination_class = None


    @swagger_auto_schema(
        operation_summary=" امکانات اتاق‌ها",
        operation_description="این API لیست تمام امکانات اتاق‌ها را بدون توجه به هتل برمی‌گرداند.",
        tags=['best-hotel'],
        responses={200: RoomFacilitiesSimpleSerializer(many=True)}
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
class BaseHotelListView(APIView):
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


class SuggesteHotelListView(BaseHotelListView):
    @swagger_auto_schema(
        operation_summary="دریافت لیست هتل‌های پیشنهادی",
        operation_description="این API لیستی از هتل‌های پیشنهادی ویژه را بدون صفحه‌بندی باز می‌گرداند.",
        tags=['hotel-home'],
        responses={
            200: openapi.Response(
                description="لیست هتل‌های پیشنهادی ویژه",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_OBJECT)
                )
            )
        }
    )
    def get(self, request, *args, **kwargs):
        hotels = Hotel.objects.filter(is_special_offer=True).select_related('city', 'type').distinct()
        hotel_min_price_map = self.get_hotel_min_price_map(hotels)
        context = {'hotel_min_price_map': hotel_min_price_map, 'request': request}

        special_offers_data = []
        for hotel in hotels:
            serialized = HotelListSerializer(hotel, context=context).data
            serialized['average_score'] = self.get_average_score(hotel)
            special_offers_data.append(serialized)

        return Response(special_offers_data)



class AmazingHotelsListView(BaseHotelListView):
    @swagger_auto_schema(
        operation_summary="دریافت لیست هتل‌های فروش شگفت‌انگیز",
        operation_description="این API لیستی از هتل‌های فروش شگفت‌انگیز را بدون صفحه‌بندی باز می‌گرداند.",
        tags=['hotel-home'],
        responses={
            200: openapi.Response(
                description="لیست هتل‌های فروش شگفت‌انگیز",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_OBJECT)
                )
            )
        }
    )
    def get(self, request, *args, **kwargs):
        hotels = Hotel.objects.filter(is_flash_sale=True).select_related('city', 'type').distinct()
        hotel_min_price_map = self.get_hotel_min_price_map(hotels)
        context = {'hotel_min_price_map': hotel_min_price_map, 'request': request}

        flash_sales_data = []
        for hotel in hotels:
            serialized = HotelListSerializer(hotel, context=context).data
            serialized['average_score'] = self.get_average_score(hotel)
            flash_sales_data.append(serialized)

        return Response(flash_sales_data)




class BestSellersListView(BaseHotelListView):
    @swagger_auto_schema(
        operation_summary="دریافت لیست هتل‌های پرفروش‌ترین",
        operation_description="این API لیستی از هتل‌های پرفروش‌ترین را بدون صفحه‌بندی باز می‌گرداند.",
        tags=['hotel-home'],
        responses={
            200: openapi.Response(
                description="لیست هتل‌های پرفروش‌ترین",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_OBJECT)
                )
            )
        }
    )
    def get(self, request, *args, **kwargs):
        hotels = Hotel.objects.filter(is_best_seller=True).select_related('city', 'type').distinct()
        hotel_min_price_map = self.get_hotel_min_price_map(hotels)
        context = {'hotel_min_price_map': hotel_min_price_map, 'request': request}

        best_sellers_data = []
        for hotel in hotels:
            serialized = HotelListSerializer(hotel, context=context).data
            serialized['average_score'] = self.get_average_score(hotel)
            best_sellers_data.append(serialized)

        return Response(best_sellers_data)



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
try:
    logger = logging.getLogger(__name__)
except Exception:
    def logger_fallback(*args, **kwargs):
        print(*args, file=sys.stderr)
    logger = type('Logger', (), {
        'info': logger_fallback,
        'warning': logger_fallback,
        'debug': logger_fallback
    })()


# --- Pagination ---
class BestHotelsPagination(PageNumberPagination):
    page_size = 8
    max_page_size = 8
    page_query_param = 'page'

    def get_paginated_response(self, data):
        total_items = self.page.paginator.count
        total_pages = math.ceil(total_items / self.page_size)
        if total_pages > 100:
            total_pages = 100
            total_items = self.page_size * 100
        return Response({
            'count': total_items,
            'current_page': self.page.number,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data,
        })


# --- Serializer ---
class UpdatedHotelListSerializer(serializers.ModelSerializer):
    price = serializers.SerializerMethodField()
    price_after_discount = serializers.SerializerMethodField()
    discount_percentage = serializers.SerializerMethodField()
    discount_date = serializers.SerializerMethodField()
    night_count = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    average_score = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()
    reservation_count = serializers.SerializerMethodField()
    public_tags = serializers.SerializerMethodField()
    city = CitySerializer(read_only=True)

    class Meta:
        model = Hotel
        fields = (
            'name', 'slug', 'city', 'address', 'main_image', 'stars', 'type',
            'price', 'price_after_discount', 'discount_percentage',
            'discount_date', 'night_count', 'rating', 'average_score',
            'comment_count', 'reservation_count', 'public_tags',
        )

    def get_price(self, obj):
        return self.context.get('hotel_min_price_map', {}).get(obj.id, {}).get('original_total_price', 0)

    def get_price_after_discount(self, obj):
        return self.context.get('hotel_min_price_map', {}).get(obj.id, {}).get('total_price', 0)

    def get_discount_percentage(self, obj):
        return self.context.get('hotel_min_price_map', {}).get(obj.id, {}).get('discount_percentage', None)

    def get_discount_date(self, obj):
        return self.context.get('hotel_min_price_map', {}).get(obj.id, {}).get('discount_date', None)

    def get_rating(self, obj):
        return self.context.get('hotel_min_price_map', {}).get(obj.id, {}).get('rating', 0)

    def get_average_score(self, obj):
        return self.context.get('hotel_min_price_map', {}).get(obj.id, {}).get('average_score', 0.0)

    def get_reservation_count(self, obj):
        return self.context.get('hotel_min_price_map', {}).get(obj.id, {}).get('reservation_count', 0)

    def get_public_tags(self, obj):
        public_tags = HotelTagPublic.objects.filter(hotel=obj)
        return HotelTagPublicSerializer(
            public_tags, many=True,
            context={'request': self.context.get('request')}
        ).data

    def get_night_count(self, obj):
        return self.context.get("night_count", 1)

    def get_comment_count(self, obj):
        return self.context.get('hotel_comment_count_map', {}).get(obj.id, 0)

    def get_city(self, obj):
        return obj.city.name if obj.city else None


# --- Utility function برای اعمال تخفیف درصدی فقط ---
def apply_percentage_discount(price, discount_type, discount_value, discount_date=None, date=None):
    """
    price: قیمت اصلی
    discount_type: 'percentage' یا 'fixed'
    discount_value: مقدار تخفیف
    discount_date: تاریخ انقضای درصدی
    date: تاریخ محاسبه
    """
    final_price = price
    if discount_type == 'percentage' and discount_date and discount_date >= date:
        final_price = int(price - (price * discount_value / 100))
    # تخفیف ثابت روی قیمت کل اعمال نمیشه
    return max(final_price, 0)


# --- API View ---
class BestHotelspageAPI(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = UpdatedHotelListSerializer
    pagination_class = BestHotelsPagination
    queryset = Hotel.objects.none()

    def get_average_score(self, hotel):
        comments = Comment.objects.filter(hotel=hotel, is_approved=True)
        if not comments.exists():
            return 0.0
        all_points = CommentPoint.objects.filter(comment__in=comments)
        overall_average = all_points.aggregate(avg=Avg("point"))["avg"]
        return round(overall_average or 0, 1)

    def _sum_prices_over_range(self, room, start_date, end_date):
        date_range = [start_date + jdatetime.timedelta(days=i) for i in range((end_date - start_date).days or 1)]
        total_price_raw = 0
        total_price_discounted = 0
        discount_percentage = None
        discount_date_str = None

        for d in date_range:
            price_data = room.date_prices.filter(start_date__lte=d, end_date__gte=d).order_by('-id').select_related('user_level').first()
            if not price_data:
                return None

            total_price_raw += price_data.price
            price_after = apply_percentage_discount(
                price_data.price, price_data.discount_type,
                price_data.discount_value, price_data.discount_date, d
            )
            total_price_discounted += price_after

            if price_data.discount_type == 'percentage':
                discount_percentage = price_data.discount_value
                discount_date_str = price_data.discount_date.strftime('%Y-%m-%d') if price_data.discount_date else None

        return {
            'original_total_price': int(total_price_raw),
            'total_price': int(total_price_discounted),
            'discount_percentage': discount_percentage,
            'discount_date': discount_date_str
        }

    def calculate_min_pack_price(self, remaining_passengers, available_rooms, start_date_obj, end_date_obj):
        if not remaining_passengers:
            return 0, 0

        p = remaining_passengers[0]
        best_result = None

        for room in available_rooms:
            if room.inventory > 0 and p <= room.room_capacity + room.extra_capacity:
                summed = self._sum_prices_over_range(room, start_date_obj, end_date_obj)
                if not summed:
                    continue

                sub_discounted = summed['total_price']
                sub_original = summed['original_total_price']

                if len(remaining_passengers) > 1:
                    remaining_rooms = available_rooms.exclude(id=room.id)
                    sub_d, sub_o = self.calculate_min_pack_price(remaining_passengers[1:], remaining_rooms, start_date_obj, end_date_obj)
                    if sub_d is None:
                        continue
                    sub_discounted += sub_d
                    sub_original += sub_o

                if not best_result or sub_discounted < best_result[0]:
                    best_result = (sub_discounted, sub_original)

        return best_result if best_result else (None, None)

    @swagger_auto_schema(
        operation_summary="دریافت لیست بهترین هتل‌ها با فیلترهای مختلف",
        tags=["best-hotel"],
    )
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        city = request.query_params.get('city')
        start_date_str = request.query_params.get('start-date')
        end_date_str = request.query_params.get('end-date')
        passengers = request.query_params.get('passengers')
        star = request.query_params.get('star')
        min_price = request.query_params.get('min-price')
        max_price = request.query_params.get('max-price')
        residence_type = request.query_params.get('residence-type')
        room_facilities = request.query_params.get('room-facilities')
        hotel_facilities = request.query_params.get('hotel-facilities')

        try:
            passenger_values = [int(x) for x in (passengers.split(',') if passengers else ['1'])]
            min_price = int(min_price) if min_price else None
            max_price = int(max_price) if max_price else None
        except ValueError:
            raise ValidationError({'detail': 'پارامترهای عددی معتبر نیستند.'})

        rooms_with_min_price = Room.objects.annotate(
            min_price=Min('date_prices__price')
        ).order_by('min_price')

        hotels_qs = Hotel.objects.all().select_related('city__province').prefetch_related(
            'public_tags',
            Prefetch('rooms', queryset=rooms_with_min_price.prefetch_related(
                Prefetch('date_prices', queryset=RoomDatePrice.objects.select_related('room', 'user_level'))
            )),
            Prefetch('comments', queryset=Comment.objects.filter(is_approved=True))
        ).order_by('rating').distinct()

        if city:
            hotels_qs = hotels_qs.filter(city__name__iexact=city)

        if star:
            try:
                star_values = [int(x) for x in star.split(',')]
                hotels_qs = hotels_qs.filter(stars__in=star_values)
            except ValueError:
                raise ValidationError({'detail': 'مقدار star باید عدد یا لیست جدا شده با کاما باشد.'})

        if residence_type:
            try:
                residence_types = [int(x) for x in residence_type.split(',')]
                hotels_qs = hotels_qs.filter(type__id__in=residence_types)
            except ValueError:
                raise ValidationError({'detail': 'شناسه نوع اقامتگاه نامعتبر است.'})

        if room_facilities:
            try:
                room_facility_ids = [int(x) for x in room_facilities.split(',')]
                hotels_qs = hotels_qs.filter(rooms__facilities__id__in=room_facility_ids).distinct()
            except ValueError:
                raise ValidationError({'detail': 'شناسه‌های امکانات اتاق نامعتبر است.'})

        if hotel_facilities:
            try:
                hotel_facility_ids = [int(x) for x in hotel_facilities.split(',')]
                hotels_qs = hotels_qs.filter(public_tags__id__in=hotel_facility_ids).distinct()
            except ValueError:
                raise ValidationError({'detail': 'شناسه‌های امکانات هتل نامعتبر است.'})

        today = jdatetime.date.today()
        start_date_obj = today if not start_date_str else jdatetime.date(*map(int, start_date_str.split('-')))
        end_date_obj = today + jdatetime.timedelta(days=1) if not end_date_str else jdatetime.date(*map(int, end_date_str.split('-')))
        if end_date_obj <= start_date_obj:
            end_date_obj = start_date_obj + jdatetime.timedelta(days=1)

        night_count = (end_date_obj - start_date_obj).days

        hotel_min_price_map = {}
        hotel_comment_count_map = {}

        for hotel in hotels_qs:
            rooms_qs = hotel.rooms.filter(
                date_prices__start_date__lte=start_date_obj,
                date_prices__end_date__gte=end_date_obj,
                inventory__gt=0,
            ).distinct()

            if not rooms_qs.exists():
                continue

            hotel_comment_count_map[hotel.id] = hotel.comments.count()

            if len(passenger_values) == 1 and passenger_values[0] == 0:
                min_price_data = None
                for room in rooms_qs:
                    summed = self._sum_prices_over_range(room, start_date_obj, end_date_obj)
                    if summed and (min_price_data is None or summed['total_price'] < min_price_data['total_price']):
                        min_price_data = summed.copy()
                        min_price_data.update({
                            'rating': hotel.rating or 0,
                            'reservation_count': hotel.reservation_count or 0,
                            'average_score': self.get_average_score(hotel),
                        })
            else:
                min_discounted, min_original = self.calculate_min_pack_price(passenger_values, rooms_qs, start_date_obj, end_date_obj)
                if min_discounted is not None:
                    min_price_data = {
                        'total_price': min_discounted,
                        'original_total_price': min_original,
                        'discount_percentage': None,
                        'discount_date': None,
                        'rating': hotel.rating or 0,
                        'reservation_count': hotel.reservation_count or 0,
                        'average_score': self.get_average_score(hotel),
                    }
                else:
                    continue

            hotel_min_price_map[hotel.id] = min_price_data

        serializer = self.get_serializer(hotels_qs, many=True, context={
            'hotel_min_price_map': hotel_min_price_map,
            'hotel_comment_count_map': hotel_comment_count_map,
            'night_count': night_count,
            'request': request,
        })

        page = self.paginate_queryset(hotels_qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True, context={
                'hotel_min_price_map': hotel_min_price_map,
                'hotel_comment_count_map': hotel_comment_count_map,
                'night_count': night_count,
                'request': request,
            })
            return self.get_paginated_response(serializer.data)

        return Response(serializer.data)





#ای پی ای فیلتر محدوده قیمت بهترین هتل ها 
try:
    logger = logging.getLogger(__name__)
except Exception:
    def logger_fallback(*args, **kwargs):
        print(*args, file=sys.stderr)
    logger = type('Logger', (), {
        'info': logger_fallback,
        'warning': logger_fallback,
        'debug': logger_fallback
    })()


class GetPriceRangeAPI(generics.ListAPIView):
    """API برای دریافت لیست هتل‌ها بر اساس محدوده قیمت و فیلترهای اعمال‌شده."""
    permission_classes = [AllowAny]
    serializer_class = HotelPriceRangeSerializer

    def get_average_score(self, hotel):
        """محاسبه میانگین امتیاز هتل بر اساس نظرات تأییدشده."""
        comments = Comment.objects.filter(hotel=hotel, is_approved=True)
        if not comments.exists():
            return 0.0
        all_points = CommentPoint.objects.filter(comment__in=comments)
        overall_average = all_points.aggregate(avg=Avg("point"))["avg"]
        return round(overall_average or 0, 1)

    def _sum_prices_over_range(self, room, start_date, end_date):
        """محاسبه مجموع قیمت‌ها برای یک بازه زمانی با اعمال فقط تخفیف درصدی."""
        date_range = [start_date + jdatetime.timedelta(days=i) for i in range((end_date - start_date).days or 1)]
        total_price_raw = 0
        total_price_discounted = 0
        remembered_discount_percentage = None
        remembered_discount_date = None

        for d in date_range:
            price_data = room.date_prices.filter(
                start_date__lte=d,
                end_date__gte=d
            ).order_by('-id').select_related('user_level', 'room').first()

            if not price_data:
                logger.warning(f"No price data found for room {room.id} on date {d}")
                return None

            price_raw = price_data.price
            price_after = price_raw

            if price_data.discount_type == 'percentage':
                if price_data.discount_date and price_data.discount_date >= d:
                    disc_amount = int(price_raw * price_data.discount_value / 100)
                    price_after = max(price_raw - disc_amount, 0)
                    remembered_discount_percentage = price_data.discount_value
                    remembered_discount_date = price_data.discount_date.strftime('%Y-%m-%d')
                    logger.debug(f"Applied {disc_amount} discount for room {room.id} on {d}")
                else:
                    price_after = price_raw

            total_price_raw += price_raw
            total_price_discounted += price_after

        logger.info(f"Room {room.id}: Raw price = {total_price_raw}, Discounted price = {total_price_discounted}")
        return {
            'original_total_price': int(total_price_raw),
            'total_price': int(total_price_discounted),
            'discount_percentage': remembered_discount_percentage,
            'discount_date': remembered_discount_date,
        }

    @swagger_auto_schema(
        operation_summary="فیلتر محدوده قیمت هتل ",
        operation_description=(
            "این API لیست هتل‌ها را با توجه به فیلترها و محدوده قیمت (بر اساس قیمت نهایی با تخفیف درصدی) "
            "بازمی‌گرداند. قیمت‌ها بر اساس مجموع قیمت کل بازه، تاریخ، تعداد شب‌ها، و ظرفیت مسافران محاسبه می‌شوند. "
            "حداقل و حداکثر قیمت کل هتل‌های فیلترشده نیز نمایش داده می‌شود."
        ),
        tags=["best-hotel"],
        manual_parameters=[
            openapi.Parameter(name='city', in_=openapi.IN_QUERY, description='نام شهر', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter(name='start-date', in_=openapi.IN_QUERY, description='تاریخ شروع به فرمت yyyy-mm-dd', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter(name='end-date', in_=openapi.IN_QUERY, description='تاریخ پایان به فرمت yyyy-mm-dd', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter(name='passengers', in_=openapi.IN_QUERY, description='ظرفیت مسافران برای فیلتر اتاق‌ها (0 برای نمایش همه هتل‌ها یا لیست مثل 1,2)', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter(name='star', in_=openapi.IN_QUERY, description='ستاره‌های هتل (مثل 3,4,5)', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter(name='min-price', in_=openapi.IN_QUERY, description='حداقل قیمت (بر اساس قیمت نهایی کل بازه)', type=openapi.TYPE_INTEGER, required=False),
            openapi.Parameter(name='max-price', in_=openapi.IN_QUERY, description='حداکثر قیمت (بر اساس قیمت نهایی کل بازه)', type=openapi.TYPE_INTEGER, required=False),
            openapi.Parameter(name='residence-type', in_=openapi.IN_QUERY, description='نوع اقامتگاه', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter(name='room-facilities', in_=openapi.IN_QUERY, description='شناسه امکانات اتاق‌ها (مثل 1,2)', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter(name='hotel-facilities', in_=openapi.IN_QUERY, description='شناسه امکانات هتل‌ها (مثل 1,2)', type=openapi.TYPE_STRING, required=False),
        ]
    )
    def get(self, request, *args, **kwargs):
        city = request.query_params.get('city')
        start_date_str = request.query_params.get('start-date')
        end_date_str = request.query_params.get('end-date')
        passengers = request.query_params.get('passengers')
        star = request.query_params.get('star')
        min_price_param = request.query_params.get('min-price')
        max_price_param = request.query_params.get('max-price')
        residence_type = request.query_params.get('residence-type')
        room_facilities = request.query_params.get('room-facilities')
        hotel_facilities = request.query_params.get('hotel-facilities')

        try:
            passenger_values = [int(x) for x in (passengers.split(',') if passengers else ['1'])]
            min_price_param = int(min_price_param) if min_price_param else None
            max_price_param = int(max_price_param) if max_price_param else None
        except ValueError:
            raise ValidationError({'detail': 'پارامترهای عددی معتبر نیستند.'})

        rooms_with_min_price = Room.objects.annotate(
            min_price=Min('date_prices__price')
        ).order_by('min_price')

        hotels_qs = Hotel.objects.all().select_related('city__province').prefetch_related(
            'public_tags',
            Prefetch('rooms', queryset=rooms_with_min_price.prefetch_related(
                Prefetch('date_prices', queryset=RoomDatePrice.objects.select_related('room', 'user_level'))
            )),
            Prefetch('comments', queryset=Comment.objects.filter(is_approved=True))
        ).order_by('rating').distinct()

        if city:
            hotels_qs = hotels_qs.filter(city__name__iexact=city)

        if star:
            try:
                star_values = [int(x) for x in star.split(',')]
                hotels_qs = hotels_qs.filter(stars__in=star_values)
            except ValueError:
                raise ValidationError({'detail': 'مقدار star باید عدد یا لیست جدا شده با کاما باشد.'})

        if residence_type:
            try:
                residence_types = [int(x) for x in residence_type.split(',')]
                hotels_qs = hotels_qs.filter(type__id__in=residence_types)
            except ValueError:
                raise ValidationError({'detail': 'شناسه نوع اقامتگاه نامعتبر است.'})

        if room_facilities:
            try:
                room_facility_ids = [int(x) for x in room_facilities.split(',')]
                hotels_qs = hotels_qs.filter(rooms__facilities__id__in=room_facility_ids).distinct()
            except ValueError:
                raise ValidationError({'detail': 'شناسه‌های امکانات اتاق نامعتبر است.'})

        if hotel_facilities:
            try:
                hotel_facility_ids = [int(x) for x in hotel_facilities.split(',')]
                hotels_qs = hotels_qs.filter(public_tags__id__in=hotel_facility_ids).distinct()
            except ValueError:
                raise ValidationError({'detail': 'شناسه‌های امکانات هتل نامعتبر است.'})

        # مدیریت تاریخ
        today = jdatetime.date.today()
        start_date_obj = today if not start_date_str else jdatetime.date(*map(int, start_date_str.split('-')))
        end_date_obj = today + jdatetime.timedelta(days=1) if not end_date_str else jdatetime.date(*map(int, end_date_str.split('-')))
        if end_date_obj <= start_date_obj:
            end_date_obj = start_date_obj + jdatetime.timedelta(days=1)

        hotel_min_price_map = {}
        filtered_hotels = []

        for hotel in hotels_qs:
            rooms_qs = hotel.rooms.filter(
                date_prices__start_date__lte=start_date_obj,
                date_prices__end_date__gte=end_date_obj,
                inventory__gt=0,
            ).distinct()

            if not rooms_qs.exists():
                continue

            if len(passenger_values) == 1 and passenger_values[0] == 0:
                min_price_data = None
                for room in rooms_qs:
                    summed = self._sum_prices_over_range(room, start_date_obj, end_date_obj)
                    if summed and (min_price_data is None or summed['total_price'] < min_price_data['total_price']):
                        min_price_data = summed
            else:
                def calculate_min_pack_price(remaining_passengers, available_rooms):
                    if not remaining_passengers:
                        return 0
                    p = remaining_passengers[0]
                    min_pack_price = float('inf')

                    for room in available_rooms:
                        if room.inventory > 0 and p <= room.room_capacity + room.extra_capacity:
                            summed = self._sum_prices_over_range(room, start_date_obj, end_date_obj)
                            if summed:
                                sub_price = summed['total_price']
                                if len(remaining_passengers) > 1:
                                    remaining_rooms = available_rooms.exclude(id=room.id)
                                    sub_price += calculate_min_pack_price(remaining_passengers[1:], remaining_rooms)
                                if sub_price < min_pack_price:
                                    min_pack_price = sub_price

                    return min_pack_price if min_pack_price != float('inf') else None

                min_pack_price = calculate_min_pack_price(passenger_values, rooms_qs)
                if min_pack_price is not None:
                    min_price_data = {'total_price': min_pack_price}

            if min_price_data:
                total_price = min_price_data['total_price']
                if (min_price_param is None or total_price >= min_price_param) and (max_price_param is None or total_price <= max_price_param):
                    hotel_min_price_map[hotel.id] = min_price_data
                    filtered_hotels.append(hotel)

        if not filtered_hotels:
            return Response({
                'detail': 'هیچ هتلی در این محدوده قیمت یافت نشد.',
                'min_price': 0,
                'max_price': 0
            })

        # محاسبه حداقل و حداکثر قیمت از هتل‌های فیلترشده
        hotel_prices = [hotel_min_price_map[hotel.id]['total_price'] for hotel in filtered_hotels]
        min_price = min(hotel_prices) if hotel_prices else 0
        max_price = max(hotel_prices) if hotel_prices else 0

        serializer = self.get_serializer(filtered_hotels, many=True, context={'hotel_min_price_map': hotel_min_price_map})
        response_data = {
            'hotels': serializer.data,
            'min_price': min_price,
            'max_price': max_price
        }
        return Response(response_data)