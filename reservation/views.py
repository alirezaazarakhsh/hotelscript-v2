from collections import defaultdict
import itertools
from datetime import datetime, timedelta
import logging
import random
import re
import math
import sys
import json
import traceback
import copy
import jdatetime
from itertools import combinations
from reservation.models import Hotel 
from rest_framework.views import APIView
from rest_framework.generics import RetrieveUpdateDestroyAPIView
from rest_framework.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _
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
    ReservationRoom,
    ReservationRoomPassenger,
    Reservationhotel,
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
    HotelRulesSerializer,
    HotelSearchSerializer,
    HotelTagPublicSerializer,
    HotelTagSerializer,
    HotelTypeSerializer,
    ReservationCreateInputSerializer,
    ReservationSerializer,
    ReservationUpdatePassengersInputSerializer,
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
                    price_after_discount = price_data.price
                else:
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
                if passengers_list == [0]:
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

        # اگر هیچ اتاقی نبود، پاسخ مناسب با status 200 برگردان
        if not rooms_qs.exists():
            return Response({
                'detail': 'هیچ اتاقی برای این هتل موجود نیست.',
                'rooms': [],
                'price_calendar': [{"date": (start_date_obj + jdatetime.timedelta(days=i)).strftime('%Y/%m/%d'), "status": "close"} for i in range((end_date_obj - start_date_obj).days)]
            }, status=200)

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
                return Response({
                    'detail': f'اتاقی با ظرفیت {required_capacity} یافت نشد.',
                    'rooms': [],
                    'price_calendar': [{"date": (start_date_obj + jdatetime.timedelta(days=i)).strftime('%Y/%m/%d'), "status": "close"} for i in range(night_count)]
                }, status=200)

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
            return Response({
                'detail': f'پک مناسب با ظرفیت‌های {passengers_list} یافت نشد.',
                'packs': [],
                'price_calendar': [{"date": (start_date_obj + jdatetime.timedelta(days=i)).strftime('%Y/%m/%d'), "status": "close"} for i in range(night_count)]
            }, status=200)

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





# ای پی ای پیشنهاد هتل ها در صفحه داخلی هتل بر اساس اسلاگ هتل 
class HomeHotelByHotelSlugView(APIView):
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
        operation_summary="دریافت لیست هتل‌های پیشنهادی بر اساس اسلاگ هتل در صفحه داخلی هتل",
        operation_description="این API لیستی از هتل‌های یک شهر خاص را بر اساس اسلاگ هتل ورودی بازمی‌گرداند. شهر هتل ورودی پیدا می‌شود و هتل‌های دیگر آن شهر (به جز هتل ورودی) پیشنهاد می‌شوند. اگر هتل یافت نشود، خطای 404 برگردانده می‌شود.",
        tags=['hotel'],
        manual_parameters=[
            openapi.Parameter(
                'hotel_slug',
                openapi.IN_PATH,
                description="اسلاگ هتل (مثال: hotel-tehran-1)",
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        responses={
            200: openapi.Response(
                description="لیست هتل‌های پیشنهادی برای شهر هتل مشخص‌شده",
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
                description="هتل یافت نشد",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING, description="پیام خطا")
                    }
                )
            )
        }
    )
    def get(self, request, hotel_slug, *args, **kwargs):
        try:
            hotel_slug = hotel_slug.strip()
            input_hotel = Hotel.objects.get(slug=hotel_slug)
            city = input_hotel.city
            hotels = Hotel.objects.filter(city=city).exclude(slug=hotel_slug).select_related('city', 'type').distinct()
            hotel_min_price_map = self.get_hotel_min_price_map(hotels)
            context = {'hotel_min_price_map': hotel_min_price_map, 'request': request}

            serialized_hotels = []
            for hotel in hotels:
                serialized = HotelListSerializer(hotel, context=context).data
                serialized['average_score'] = self.get_average_score(hotel)
                serialized_hotels.append(serialized)

            return Response(serialized_hotels)
        except Hotel.DoesNotExist:
            return Response({'error': 'Hotel not found'}, status=404)
        
        
        
        

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
        'debug': logger_fallback,
        'error': logger_fallback,
    })()


# --- Custom Pagination ---
class BestHotelsPagination(PageNumberPagination):
    page_size = 8
    max_page_size = 8
    page_query_param = 'page'

    def get_paginated_response(self, data):
        total_items = min(self.page.paginator.count, 800)
        total_pages = self.page.paginator.num_pages
        return Response({
            'count': total_items,
            'total_pages': total_pages,
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
    city = CitySerializer()
    residence_type = serializers.CharField(source='type.title')

    class Meta:
        model = Hotel
        fields = (
            'name', 'slug', 'city', 'address', 'main_image', 'stars', 'residence_type',
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
        return HotelTagPublicSerializer(public_tags, many=True, context={'request': self.context.get('request')}).data

    def get_night_count(self, obj):
        return self.context.get("night_count", 0)

    def get_comment_count(self, obj):
        return self.context.get('hotel_comment_count_map', {}).get(obj.id, 0)


# --- API View ---
class BestHotelspageAPI(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = UpdatedHotelListSerializer
    pagination_class = BestHotelsPagination
    queryset = Hotel.objects.none()

    def get_average_score(self, hotel):
        comments = Comment.objects.filter(hotel=hotel, is_approved=True)
        if not comments.exists():
            return 0.0
        overall_average = CommentPoint.objects.filter(comment__in=comments).aggregate(avg=Avg("point"))["avg"]
        return round(overall_average or 0, 1)

    def calculate_discount(self, price_data, date, fixed_discount_applied=False):
        """محاسبه مقدار تخفیف و قیمت پس از تخفیف"""
        discount_amount = 0
        price_after_discount = price_data.price if price_data else None
        discount_percentage = None
        discount_date = None

        if price_data and price_data.discount_type != 'none':
            if price_data.discount_type == 'percentage':
                if not price_data.discount_date or price_data.discount_date <= date:
                    price_after_discount = price_data.price
                else:
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

    def get_room_data(self, hotel, start_date_obj, end_date_obj, passengers_list):
        date_range = [start_date_obj + jdatetime.timedelta(days=i) for i in range((end_date_obj - start_date_obj).days)]
        night_count = (end_date_obj - start_date_obj).days

        rooms_qs = hotel.rooms.filter(
            date_prices__start_date__lte=start_date_obj,
            date_prices__end_date__gte=end_date_obj,
            inventory__gt=0
        ).distinct().prefetch_related('date_prices', 'services').select_related('hotel')

        room_dict = {}
        for room in rooms_qs:
            closed_dates = ClosedDate.objects.filter(room_date__room=room, date__range=(start_date_obj, end_date_obj))
            price_calendar = []
            fixed_discount_applied = False
            has_zero_price = False

            for date in date_range:
                price_data = room.date_prices.filter(start_date__lte=date, end_date__gte=date).order_by('-id').select_related('user_level').first()
                closed_date = closed_dates.filter(date=date).first()
                status = "open" if price_data and not closed_date else "close"

                if status == "open" and (price_data.price == 0 or price_data.price is None):
                    has_zero_price = True
                    break

                try:
                    discount_amount, price_after_discount, discount_percentage, discount_date, fixed_discount_applied = self.calculate_discount(price_data, date, fixed_discount_applied)
                except ValueError:
                    continue

                price_calendar.append({
                    "status": status,
                    "price": {
                        "price": price_data.price if price_data else None,
                        "price_after_discount": price_after_discount,
                        "discount_percentage": discount_percentage,
                        "discount_amount": discount_amount,
                        "discount_date": discount_date,
                        "is_fixed_discount_one_time": price_data.is_fixed_discount_one_time if price_data else False,
                        "extra_capacity_price": price_data.extra_passenger_price if price_data else 0
                    } if status == "open" else None
                })

            if has_zero_price or not price_calendar or all(day['status'] != "open" for day in price_calendar):
                continue

            total_price = sum(day['price']['price'] for day in price_calendar if day['status'] == "open" and day['price'])
            total_price_discount = sum(
                day['price']['price_after_discount'] if day['status'] == "open" and day['price'] and day['price']['discount_percentage'] is not None else
                day['price']['price'] for day in price_calendar if day['status'] == "open" and day['price']
            )

            if total_price == 0 or total_price_discount == 0:
                continue

            first_price_data = room.date_prices.filter(start_date__lte=start_date_obj, end_date__gte=start_date_obj).order_by('-id').select_related('user_level').first()
            if not first_price_data:
                continue

            try:
                discount_amount, price_after_discount_first, discount_percentage_first, discount_date_first, _ = self.calculate_discount(first_price_data, start_date_obj, False)
            except ValueError:
                continue

            room_dict[room.id] = {
                "id": room.id,
                "capacity": room.room_capacity,
                "extra_capacity": room.extra_capacity,
                "room_number": room.inventory or 0,
                "price": {
                    "total_price": total_price,
                    "total_price_discount": total_price_discount,
                    "discount_percentage": discount_percentage_first,
                    "discount_date": discount_date_first,
                    "is_fixed_discount_one_time": first_price_data.is_fixed_discount_one_time,
                    "extra_capacity_price": first_price_data.extra_passenger_price
                },
                "price_calendar": price_calendar
            }

        room_data = list(room_dict.values())

        # If passengers_list is empty or [0], find the cheapest room regardless of capacity
        if not passengers_list or passengers_list == [0]:
            if not room_data:
                return None
            min_room = min(room_data, key=lambda x: x['price']['total_price_discount'] or float('inf'))
            min_price_data = {
                'original_total_price': min_room['price']['total_price'],
                'total_price': min_room['price']['total_price_discount'],
                'discount_percentage': min_room['price']['discount_percentage'],
                'discount_date': min_room['price']['discount_date'],
            }
        else:
            # --- Single room ---
            if len(passengers_list) == 1:
                required_capacity = passengers_list[0]
                filtered_rooms = [r for r in room_data if r['capacity'] <= required_capacity <= r['capacity'] + r['extra_capacity']]
                if not filtered_rooms:
                    return None

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

                min_room = min(filtered_rooms, key=lambda x: x['price']['total_price_discount'] or float('inf'))
                min_price_data = {
                    'original_total_price': min_room['price']['total_price'],
                    'total_price': min_room['price']['total_price_discount'],
                    'discount_percentage': min_room['price']['discount_percentage'],
                    'discount_date': min_room['price']['discount_date'],
                }

            # --- Pack rooms ---
            else:
                packs = []
                passengers_list.sort()
                room_candidates = {}
                for p in set(passengers_list):
                    room_candidates[p] = [r for r in room_data if r['capacity'] <= p <= r['capacity'] + r['extra_capacity'] and r['room_number'] > 0]

                def generate_packs(current_pack, remaining_groups, used_rooms):
                    if not remaining_groups:
                        pack_total_price = 0
                        pack_total_original = 0
                        pack_discount_percentages = set()
                        pack_discount_dates = set()
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
                            pack_total_original += room['price']['total_price']
                            pack_total_price += room['price']['total_price_discount']
                            if room['price']['discount_percentage']:
                                pack_discount_percentages.add(room['price']['discount_percentage'])
                            if room['price']['discount_date']:
                                pack_discount_dates.add(room['price']['discount_date'])
                        packs.append({
                            "total_price": pack_total_price,
                            "original_total_price": pack_total_original,
                            "discount_percentage": list(pack_discount_percentages)[0] if len(pack_discount_percentages) == 1 else None,
                            "discount_date": list(pack_discount_dates)[0] if len(pack_discount_dates) == 1 else None,
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
                    return None

                min_pack = min(packs, key=lambda x: x['total_price'])
                min_price_data = {
                    'original_total_price': min_pack['original_total_price'],
                    'total_price': min_pack['total_price'],
                    'discount_percentage': min_pack['discount_percentage'],
                    'discount_date': min_pack['discount_date'],
                }

        if min_price_data:
            min_price_data.update({
                'rating': hotel.rating or 0,
                'reservation_count': hotel.reservation_count or 0,
                'average_score': self.get_average_score(hotel),
            })
        return min_price_data

    @swagger_auto_schema(
        operation_summary="دریافت لیست بهترین هتل‌ها با فیلترهای مختلف",
        operation_description=(
            "این API لیست هتل‌ها را با توجه به فیلترها بازمی‌گرداند. "
            "قیمت اصلی (price) و قیمت با تخفیف (price_after_discount) "
            "برای ارزان‌ترین اتاق یا پک در کل بازه نمایش داده می‌شود. "
            "اگر passengers=0 یا خالی باشد، تمام هتل‌ها با ارزان‌ترین اتاق نمایش داده می‌شوند. "
            "همچنین تعداد شب‌ها (night_count) و تعداد کامنت‌های تأییدشده (comment_count) نمایش داده می‌شود."
        ),
        tags=["best-hotel"],
        manual_parameters=[
            openapi.Parameter(name='city', in_=openapi.IN_QUERY, description='نام شهر', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter(name='start-date', in_=openapi.IN_QUERY, description='تاریخ شروع به فرمت yyyy-mm-dd', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter(name='end-date', in_=openapi.IN_QUERY, description='تاریخ پایان به فرمت yyyy-mm-dd', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter(name='passengers', in_=openapi.IN_QUERY, description='ظرفیت مسافران برای فیلتر اتاق‌ها (0 برای نمایش همه هتل‌ها یا لیست مثل 1,2)', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter(name='min-price', in_=openapi.IN_QUERY, description='حداقل قیمت', type=openapi.TYPE_INTEGER, required=False),
            openapi.Parameter(name='max-price', in_=openapi.IN_QUERY, description='حداکثر قیمت', type=openapi.TYPE_INTEGER, required=False),
            openapi.Parameter(name='star', in_=openapi.IN_QUERY, description='تعداد ستاره‌های هتل (مثل 5 یا لیست مثل 4,5)', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter(name='residence-type', in_=openapi.IN_QUERY, description='شناسه نوع اقامتگاه (مثل 1 یا لیست مثل 1,2)', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter(name='hotel-facilities', in_=openapi.IN_QUERY, description='شناسه‌های امکانات هتل (مثل 3 یا لیست مثل 3,4)', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter(name='room-facilities', in_=openapi.IN_QUERY, description='شناسه‌های امکانات اتاق (مثل 1 یا لیست مثل 1,2)', type=openapi.TYPE_STRING, required=False),
        ]
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

        passenger_values = []
        if passengers:
            try:
                passenger_values = [int(x.strip()) for x in passengers.split(',') if x.strip()]
                if len(passenger_values) > 3 or sum(passenger_values) > 8 or any(p < 0 for p in passenger_values):
                    return Response({'detail': 'پارامتر passengers نامعتبر است.'}, status=400)
                if passenger_values == [0]:
                    passenger_values = []  # Treat passengers=0 as no passenger constraint
            except ValueError:
                return Response({'detail': 'پارامتر passengers باید لیست اعداد صحیح باشد.'}, status=400)

        try:
            min_price = int(min_price) if min_price else None
            max_price = int(max_price) if max_price else None
        except ValueError:
            return Response({'detail': 'پارامترهای عددی معتبر نیستند.'}, status=400)

        hotels_qs = Hotel.objects.all().select_related('city__province', 'type').prefetch_related(
            'public_tags',
            Prefetch('rooms', queryset=Room.objects.prefetch_related(
                Prefetch('date_prices', queryset=RoomDatePrice.objects.select_related('room', 'user_level'))
            )),
            Prefetch('comments', queryset=Comment.objects.filter(is_approved=True))
        )

        if city:
            hotels_qs = hotels_qs.filter(city__name__iexact=city)

        if star:
            try:
                star_values = [int(x) for x in star.split(',') if x.strip()]
                hotels_qs = hotels_qs.filter(stars__in=star_values)
            except ValueError:
                return Response({'detail': 'مقدار star باید عدد یا لیست جدا شده با کاما باشد.'}, status=400)
        if residence_type:
            try:
                residence_ids = [int(x.strip()) for x in residence_type.split(',') if x.strip()]
                logger.info(f"Filtering by residence_type IDs: {residence_ids}")
                if residence_ids:  # فقط اگر لیست residence_ids خالی نباشد، فیلتر اعمال شود
                    hotels_qs = hotels_qs.filter(type__id__in=residence_ids)
            except ValueError:
                return Response({'detail': 'شناسه نوع اقامتگاه نامعتبر است.'}, status=400)
        if room_facilities:
            try:
                room_fac_ids = [int(x) for x in room_facilities.split(',') if x.strip()]
                for fac_id in room_fac_ids:
                    hotels_qs = hotels_qs.filter(room_facilities__id=fac_id)
                hotels_qs = hotels_qs.distinct()
            except ValueError:
                return Response({'detail': 'شناسه‌های امکانات اتاق نامعتبر است.'}, status=400)

        if hotel_facilities:
            try:
                hotel_fac_ids = [int(x) for x in hotel_facilities.split(',') if x.strip()]
                for fac_id in hotel_fac_ids:
                    hotels_qs = hotels_qs.filter(facilities__id=fac_id)
                hotels_qs = hotels_qs.distinct()
            except ValueError:
                return Response({'detail': 'شناسه‌های امکانات هتل نامعتبر است.'}, status=400)

        today = jdatetime.date.today()
        try:
            start_date_obj = today if not start_date_str else jdatetime.date(*map(int, start_date_str.split('-')))
            end_date_obj = today + jdatetime.timedelta(days=1) if not end_date_str else jdatetime.date(*map(int, end_date_str.split('-')))
            if start_date_obj > end_date_obj:
                return Response({'detail': 'تاریخ شروع نمی‌تواند بعد از تاریخ پایان باشد.'}, status=400)
            if (end_date_obj - start_date_obj).days > 30:
                return Response({'detail': 'بازه رزرو نمی‌تواند بیشتر از ۳۰ روز باشد.'}, status=400)
        except Exception:
            return Response({'detail': 'فرمت تاریخ باید yyyy-mm-dd باشد.'}, status=400)

        night_count = max((end_date_obj - start_date_obj).days, 0) if start_date_str or end_date_str else 0

        hotel_min_price_map = {}
        for hotel in hotels_qs:
            min_price_data = self.get_room_data(hotel, start_date_obj, end_date_obj, passenger_values)
            if min_price_data:
                hotel_min_price_map[hotel.id] = min_price_data

        # فیلتر هتل‌هایی که قیمت صفر دارند
        hotel_min_price_map = {
            hotel_id: data for hotel_id, data in hotel_min_price_map.items()
            if data.get('total_price', 0) > 0 and data.get('original_total_price', 0) > 0
        }

        # If no dates and no passengers (or passengers=0), include all hotels
        if not start_date_str and not end_date_str and not passengers:
            for hotel in hotels_qs:
                if hotel.id not in hotel_min_price_map:
                    hotel_min_price_map[hotel.id] = {
                        'original_total_price': 0,
                        'total_price': 0,
                        'discount_percentage': None,
                        'discount_date': None,
                        'rating': hotel.rating or 0,
                        'reservation_count': hotel.reservation_count or 0,
                        'average_score': self.get_average_score(hotel),
                    }
        else:
            # Filter hotels that have valid min_price_data
            filtered_hotel_ids = list(hotel_min_price_map.keys())
            hotels_qs = hotels_qs.filter(id__in=filtered_hotel_ids)

        # Apply min/max price filter if applicable
        if min_price is not None or max_price is not None:
            filtered_hotel_ids = [
                hid for hid, data in hotel_min_price_map.items()
                if (min_price is None or data['total_price'] >= min_price) and
                   (max_price is None or data['total_price'] <= max_price)
            ]
            hotels_qs = hotels_qs.filter(id__in=filtered_hotel_ids)

        # Sort hotels by min total_price ascending
        sorted_hotels = sorted(
            hotels_qs,
            key=lambda h: hotel_min_price_map.get(h.id, {}).get('total_price', float('inf'))
        )

        # Comment count map
        hotel_comment_count_map = {h.id: h.comments.count() for h in sorted_hotels}

        context = {
            'request': request,
            'hotel_min_price_map': hotel_min_price_map,
            'hotel_comment_count_map': hotel_comment_count_map,
            'night_count': night_count,
        }

        page = self.paginate_queryset(sorted_hotels)
        if page is not None:
            serializer = self.get_serializer(page, many=True, context=context)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(sorted_hotels, many=True, context=context)
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
        'debug': logger_fallback,
        'error': logger_fallback,
    })()

class GetPriceRangeAPI(generics.GenericAPIView):
    """
    API برای دریافت محدوده قیمت (min / max) هتل‌ها با فیلترهای اعمال‌شده.
    خروجی فقط دو فیلد دارد: min_price و max_price (بر اساس جمع قیمت‌های روزانه با اعمال تخفیف درصدی).
    """
    permission_classes = [AllowAny]

    def get_average_score(self, hotel):
        comments = Comment.objects.filter(hotel=hotel, is_approved=True)
        if not comments.exists():
            return 0.0
        all_points = CommentPoint.objects.filter(comment__in=comments)
        overall_average = all_points.aggregate(avg=Avg("point"))["avg"]
        return round(overall_average or 0, 1)

    def calculate_discount(self, price_data, date, fixed_discount_applied=False):
        """محاسبه مقدار تخفیف و قیمت پس از تخفیف"""
        discount_amount = 0
        price_after_discount = price_data.price if price_data else None
        discount_percentage = None
        discount_date = None

        if price_data and price_data.discount_type != 'none':
            if price_data.discount_type == 'percentage':
                if not price_data.discount_date or price_data.discount_date <= date:
                    price_after_discount = price_data.price
                else:
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

    def get_room_data(self, hotel, start_date_obj, end_date_obj, passengers_list):
        date_range = [start_date_obj + jdatetime.timedelta(days=i) for i in range((end_date_obj - start_date_obj).days)]
        night_count = (end_date_obj - start_date_obj).days

        rooms_qs = hotel.rooms.filter(
            date_prices__start_date__lte=start_date_obj,
            date_prices__end_date__gte=end_date_obj,
            inventory__gt=0
        ).distinct().prefetch_related('date_prices', 'services').select_related('hotel')

        room_dict = {}
        for room in rooms_qs:
            closed_dates = ClosedDate.objects.filter(room_date__room=room, date__range=(start_date_obj, end_date_obj))
            price_calendar = []
            fixed_discount_applied = False
            has_zero_price = False

            for date in date_range:
                price_data = room.date_prices.filter(start_date__lte=date, end_date__gte=date).order_by('-id').select_related('user_level').first()
                closed_date = closed_dates.filter(date=date).first()
                status = "open" if price_data and not closed_date else "close"

                if status == "open" and (price_data.price == 0 or price_data.price is None):
                    has_zero_price = True
                    break

                try:
                    discount_amount, price_after_discount, discount_percentage, discount_date, fixed_discount_applied = self.calculate_discount(price_data, date, fixed_discount_applied)
                except ValueError:
                    continue

                price_calendar.append({
                    "status": status,
                    "price": {
                        "price": price_data.price if price_data else None,
                        "price_after_discount": price_after_discount,
                        "discount_percentage": discount_percentage,
                        "discount_amount": discount_amount,
                        "discount_date": discount_date,
                        "is_fixed_discount_one_time": price_data.is_fixed_discount_one_time if price_data else False,
                        "extra_capacity_price": price_data.extra_passenger_price if price_data else 0
                    } if status == "open" else None
                })

            if has_zero_price or not price_calendar or all(day['status'] != "open" for day in price_calendar):
                continue

            total_price = sum(day['price']['price'] for day in price_calendar if day['status'] == "open" and day['price'])
            total_price_discount = sum(
                day['price']['price_after_discount'] if day['status'] == "open" and day['price'] and day['price']['discount_percentage'] is not None else
                day['price']['price'] for day in price_calendar if day['status'] == "open" and day['price']
            )

            if total_price == 0 or total_price_discount == 0:
                continue

            first_price_data = room.date_prices.filter(start_date__lte=start_date_obj, end_date__gte=start_date_obj).order_by('-id').select_related('user_level').first()
            if not first_price_data:
                continue

            try:
                discount_amount, price_after_discount_first, discount_percentage_first, discount_date_first, _ = self.calculate_discount(first_price_data, start_date_obj, False)
            except ValueError:
                continue

            room_dict[room.id] = {
                "id": room.id,
                "capacity": room.room_capacity,
                "extra_capacity": room.extra_capacity,
                "room_number": room.inventory or 0,
                "price": {
                    "total_price": total_price,
                    "total_price_discount": total_price_discount,
                    "discount_percentage": discount_percentage_first,
                    "discount_date": discount_date_first,
                    "is_fixed_discount_one_time": first_price_data.is_fixed_discount_one_time,
                    "extra_capacity_price": first_price_data.extra_passenger_price
                },
                "price_calendar": price_calendar
            }

        room_data = list(room_dict.values())

        # If passengers_list is empty or [0], find the cheapest room regardless of capacity
        if not passengers_list or passengers_list == [0]:
            if not room_data:
                return None
            min_room = min(room_data, key=lambda x: x['price']['total_price_discount'] or float('inf'))
            min_price_data = {
                'total_price': min_room['price']['total_price_discount'],
            }
        else:
            # --- Single room ---
            if len(passengers_list) == 1:
                required_capacity = passengers_list[0]
                filtered_rooms = [r for r in room_data if r['capacity'] <= required_capacity <= r['capacity'] + r['extra_capacity']]
                if not filtered_rooms:
                    return None

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

                min_room = min(filtered_rooms, key=lambda x: x['price']['total_price_discount'] or float('inf'))
                min_price_data = {
                    'total_price': min_room['price']['total_price_discount'],
                }

            # --- Pack rooms ---
            else:
                packs = []
                passengers_list.sort()
                room_candidates = {}
                for p in set(passengers_list):
                    room_candidates[p] = [r for r in room_data if r['capacity'] <= p <= r['capacity'] + r['extra_capacity'] and r['room_number'] > 0]

                def generate_packs(current_pack, remaining_groups, used_rooms):
                    if not remaining_groups:
                        pack_total_price = 0
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
                            pack_total_price += room['price']['total_price_discount']
                        packs.append({
                            "total_price": pack_total_price,
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
                    return None

                min_pack = min(packs, key=lambda x: x['total_price'])
                min_price_data = {
                    'total_price': min_pack['total_price'],
                }

        return min_price_data

    @swagger_auto_schema(
        operation_summary="فیلتر محدوده قیمت هتل",
        operation_description=(
            "این API حداقل و حداکثر قیمت را برمی‌گرداند (بر اساس جمع قیمت‌های روزانه با اعمال تخفیف درصدی). "
            "لیست هتل‌ها بازگردانده نمی‌شود."
        ),
        tags=["best-hotel"],
        manual_parameters=[
            openapi.Parameter(name='city', in_=openapi.IN_QUERY, description='نام شهر', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter(name='start-date', in_=openapi.IN_QUERY, description='تاریخ شروع به فرمت yyyy-mm-dd', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter(name='end-date', in_=openapi.IN_QUERY, description='تاریخ پایان به فرمت yyyy-mm-dd', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter(name='passengers', in_=openapi.IN_QUERY, description='ظرفیت مسافران برای فیلتر اتاق‌ها (0 برای نمایش همه هتل‌ها یا لیست مثل 1,2)', type=openapi.TYPE_STRING, required=False),
        ]
    )
    def get(self, request, *args, **kwargs):
        city = request.query_params.get('city')
        start_date_str = request.query_params.get('start-date')
        end_date_str = request.query_params.get('end-date')
        passengers = request.query_params.get('passengers')

        # parse passengers
        try:
            if not passengers or passengers.strip() in ('', '0'):
                passenger_list = []
            else:
                passenger_list = [int(x.strip()) for x in passengers.split(',') if x.strip() != '']
                if len(passenger_list) > 3 or sum(passenger_list) > 8 or any(p < 0 for p in passenger_list):
                    return Response({'detail': 'پارامتر passengers نامعتبر است.'}, status=400)
        except ValueError:
            return Response({'detail': 'پارامتر passengers باید لیست اعداد صحیح باشد.'}, status=400)

        # parse dates
        today = jdatetime.date.today()
        try:
            start_date = today if not start_date_str else jdatetime.date(*map(int, start_date_str.split('-')))
            end_date = today + jdatetime.timedelta(days=1) if not end_date_str else jdatetime.date(*map(int, end_date_str.split('-')))
            if end_date <= start_date:
                return Response({'detail': 'تاریخ شروع نمی‌تواند بعد از تاریخ پایان باشد.'}, status=400)
            if (end_date - start_date).days > 30:
                return Response({'detail': 'بازه رزرو نمی‌تواند بیشتر از ۳۰ روز باشد.'}, status=400)
        except Exception:
            return Response({'detail': 'فرمت تاریخ باید yyyy-mm-dd باشد.'}, status=400)

        # آماده‌سازی queryset هتل‌ها و اتاق‌ها
        hotels_qs = Hotel.objects.all().select_related('city__province', 'type').prefetch_related(
            'public_tags',
            Prefetch('rooms', queryset=Room.objects.prefetch_related(
                Prefetch('date_prices', queryset=RoomDatePrice.objects.select_related('room', 'user_level'))
            ))
        )

        if city:
            hotels_qs = hotels_qs.filter(city__name__iexact=city)

        prices = []

        for hotel in hotels_qs:
            min_price_data = self.get_room_data(hotel, start_date, end_date, passenger_list)
            if min_price_data:
                total_price = min_price_data.get('total_price', 0)
                if total_price > 0:
                    prices.append(total_price)

        if not prices:
            return Response({"min_price": 0, "max_price": 0})

        return Response({
            "min_price": int(min(prices)),
            "max_price": int(max(prices)),
        })
        
        
        


# ای پی ای رزرو 
class ReservationCreateAPIView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ReservationSerializer

    @swagger_auto_schema(
        operation_summary="ایجاد رزرو موقت و دریافت اطلاعات هتل و اتاق",
        operation_description="ایجاد رزرو موقت با اطلاعات هتل، اتاق‌ها و تاریخ. اطلاعات هتل، اتاق‌ها و فیلدهای خالی برای مسافران بازگردانده می‌شود.",
        tags=["reservation-api"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'hotel_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'room_id': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_INTEGER)),
                'date': openapi.Schema(type=openapi.TYPE_OBJECT,
                    properties={
                        'start': openapi.Schema(type=openapi.TYPE_STRING, description="تاریخ شروع YYYY-MM-DD"),
                        'end': openapi.Schema(type=openapi.TYPE_STRING, description="تاریخ پایان YYYY-MM-DD"),
                    }
                ),
            },
            required=['hotel_id', 'room_id', 'date']
        ),
        responses={
            201: openapi.Response(description="رزرو موقت با موفقیت ایجاد شد", schema=ReservationSerializer),
            400: openapi.Response(description="خطای ورودی یا اعتبارسنجی"),
            404: openapi.Response(description="هتل یا اتاق یافت نشد"),
        }
    )
    def post(self, request, *args, **kwargs):
        try:
            hotel_id = request.data.get('hotel_id')
            room_ids = request.data.get('room_id', [])
            date_data = request.data.get('date', {})
            start_date = date_data.get('start')
            end_date = date_data.get('end')

            if not (hotel_id and room_ids and start_date and end_date):
                return Response({"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)

            # تبدیل تاریخ‌ها از شمسی به میلادی
            try:
                check_in_date = jdatetime.datetime.strptime(start_date, '%Y-%m-%d').date()
                check_out_date = jdatetime.datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST)

            hotel = get_object_or_404(Hotel, id=hotel_id)
            rooms = Room.objects.filter(id__in=room_ids, hotel=hotel)
            if rooms.count() != len(room_ids):
                return Response({"error": "One or more rooms not found or invalid"}, status=status.HTTP_400_BAD_REQUEST)

            # ایجاد رزرو اصلی
            reservation = Reservationhotel.objects.create(
                buyer=request.user,
                reserver_first_name="Pending",
                reserver_last_name="Pending",
                reserver_phone_number="00000000000",
                check_in_date=check_in_date,
                check_out_date=check_out_date,
                status='unconfirmed',
            )

            # ایجاد رزرو اتاق‌ها با quantity پیش‌فرض
            for room in rooms:
                ReservationRoom.objects.create(
                    reservation=reservation,
                    room=room,
                    quantity=1  # یا مقدار واقعی که کاربر انتخاب کرده
                )

            # محاسبه قیمت‌ها، نیم‌شارژها و تخفیف‌ها
            total_price, total_discount, half_day_in_charge, half_day_out_charge = reservation.calculate_total_price()
            reservation.total_price = total_price
            reservation.discount = total_discount
            reservation.half_day_in_charge = half_day_in_charge
            reservation.half_day_out_charge = half_day_out_charge
            reservation.final_price = total_price - total_discount
            reservation.save(update_fields=['total_price', 'discount', 'half_day_in_charge', 'half_day_out_charge', 'final_price'])

            serializer = ReservationSerializer(reservation)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response({"error": str(e), "traceback": traceback.format_exc()}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e), "traceback": traceback.format_exc()}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ReservationUpdatePassengersAPIView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ReservationSerializer
    lookup_field = 'tracking_code'

    def get_queryset(self):
        return Reservationhotel.objects.filter(buyer=self.request.user)

    @swagger_auto_schema(
        operation_summary="ویرایش اطلاعات مسافران رزرو",
        operation_description="ویرایش اطلاعات مسافران (مسافر اصلی، سایر مسافران، مسافران ظرفیت اضافه) برای رزرو موجود با استفاده از کد پیگیری.",
        tags=["reservation-api"],
        request_body=ReservationUpdatePassengersInputSerializer,
        responses={
            200: openapi.Response(
                description="مسافران با موفقیت به‌روزرسانی شدند",
                schema=ReservationSerializer
            ),
            400: openapi.Response(
                description="خطای ورودی یا اعتبارسنجی",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                        'traceback': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
            404: openapi.Response(
                description="رزرو یافت نشد",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                        'traceback': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            )
        }
    )
    def put(self, request, *args, **kwargs):
        try:
            reservation = self.get_object()

            main_passenger = request.data.get('main_passenger', {})
            other_passengers = request.data.get('other_passengers', [])
            extra_capacity_passengers = request.data.get('extra_capacity_passengers', [])

            # Validate main_passenger
            if not all(key in main_passenger for key in ['first_name', 'last_name', 'mobile_number']):
                return Response(
                    {"error": _("Main passenger must have first_name, last_name, and mobile_number")},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validate capacities
            rooms = reservation.reservation_rooms.all()
            # هر اتاق به‌صورت یک واحد حساب می‌شود
            total_capacity = sum(r.room.room_capacity for r in rooms)
            total_extra_capacity = sum(r.room.extra_capacity for r in rooms)

            if len(other_passengers) > total_capacity - 1:
                return Response(
                    {"error": _(f"Too many other passengers. Maximum allowed: {total_capacity - 1}")},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if len(extra_capacity_passengers) > total_extra_capacity:
                return Response(
                    {"error": _(f"Too many extra capacity passengers. Maximum allowed: {total_extra_capacity}")},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Update reservation
            reservation.reserver_first_name = main_passenger['first_name']
            reservation.reserver_last_name = main_passenger['last_name']
            reservation.reserver_phone_number = main_passenger['mobile_number']
            reservation.reserver_national_code = main_passenger.get('national_code')
            reservation.save()

            # Clear old passengers
            for room in rooms:
                room.passengers.all().delete()

            # Add passengers to the first room
            first_room = rooms.first()
            if first_room:
                ReservationRoomPassenger.objects.create(
                    reservation_room=first_room,
                    first_name=main_passenger['first_name'],
                    last_name=main_passenger['last_name'],
                    mobile_number=main_passenger['mobile_number'],
                    national_code=main_passenger.get('national_code'),
                    passenger_type='primary'
                )
                for passenger in other_passengers:
                    ReservationRoomPassenger.objects.create(
                        reservation_room=first_room,
                        first_name=passenger.get('first_name'),
                        last_name=passenger.get('last_name'),
                        national_code=passenger.get('national_code'),
                        passenger_type='secondary'
                    )
                for passenger in extra_capacity_passengers:
                    ReservationRoomPassenger.objects.create(
                        reservation_room=first_room,
                        first_name=passenger.get('first_name'),
                        last_name=passenger.get('last_name'),
                        national_code=passenger.get('national_code'),
                        passenger_type='extra'
                    )

            serializer = ReservationSerializer(reservation)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except ValidationError as e:
            return Response(
                {"error": str(e), "traceback": traceback.format_exc()},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": str(e), "traceback": traceback.format_exc()},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
