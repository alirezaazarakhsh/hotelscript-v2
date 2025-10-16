from collections import defaultdict
from decimal import Decimal, InvalidOperation
import itertools
import logging
import random
import re
import math
import sys
import json
from threading import local
import traceback
import copy
from amqp import NotFound
from celery import shared_task
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import jdatetime 
from itertools import combinations
from authentication.models import NaturalProfile
from bashgah_moshtarian.models import CustomerClubPoint, DiscountActivationRecord, HotelDiscountCode, RoomDiscountCode
from bashgah_moshtarian.sms.sms import send_customer_club_deduct_sms, send_customer_club_sms
from config.models import UserLevel
from finance.models import Wallet
from reservation.models import Hotel 
from reservation.models import Reservationhotel, ReservationRoom
from rest_framework.views import APIView
from rest_framework.generics import RetrieveUpdateDestroyAPIView
from rest_framework.exceptions import PermissionDenied
from django.utils.dateparse import parse_date
from jdatetime import date as jdate, datetime as jdt
from datetime import date as gdate, datetime as gdt, timedelta
from django.utils.translation import gettext_lazy as _
from authentication import serializers
from safarname24 import settings
from safarname24.pagination import FacilitiesPaginator, RoomFacilitiesPaginator
from jdatetime import datetime as jdt
from .utils import Round
from rest_framework.generics import CreateAPIView
from rest_framework.generics import ListCreateAPIView
from rest_framework import generics
from rest_framework import serializers  # Explicit import from rest_framework
from django.db.models import Prefetch
from django.core.cache import cache  





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
    ReservationApprovalDuration,
    ReservationRoom,
    ReservationRoomPassenger,
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
    ReservationCreateResponseSerializer,
    ReservationCreateSerializer,
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

def validate_phone_number(value):
    if not re.match(r'^09\d{9}$', value):
        raise ValidationError('شماره موبایل باید به فرمت 09xxxxxxxxx باشد')

def validate_national_code(value):
    if not re.match(r'^\d{10}$', value):
        raise ValidationError('کد ملی باید 10 رقمی باشد')

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
        default_user_level = UserLevel.objects.filter(title="میهمان").first()

        user_level = default_user_level
        if request.user.is_authenticated:
            try:
                profile = request.user.natural_profile
                if profile.level:
                    user_level = profile.level
            except NaturalProfile.DoesNotExist:
                pass

        # فیلتر اتاق‌ها بر اساس تاریخ و سطح کاربری
        rooms_qs = hotel.rooms.filter(
            date_prices__start_date__lte=end_date_obj,  # بازه قیمت باید با بازه درخواستی همپوشانی داشته باشد
            date_prices__end_date__gte=start_date_obj,
            date_prices__user_level=user_level,
            inventory__gt=0
        ).distinct().prefetch_related('date_prices', 'services').select_related('hotel')

        if not rooms_qs.exists():
            rooms_qs = hotel.rooms.filter(
                date_prices__start_date__lte=end_date_obj,
                date_prices__end_date__gte=start_date_obj,
                date_prices__user_level__isnull=True,
                inventory__gt=0
            ).distinct().prefetch_related('date_prices', 'services').select_related('hotel')

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
                # ابتدا سطح کاربری، سپس fallback به عمومی
                price_data_qs = room.date_prices.filter(
                    start_date__lte=date,
                    end_date__gte=date,
                    user_level=user_level
                ).order_by('-id')
                if not price_data_qs.exists():
                    price_data_qs = room.date_prices.filter(
                        start_date__lte=date,
                        end_date__gte=date,
                        user_level__isnull=True
                    ).order_by('-id')
                price_data = price_data_qs.select_related('user_level').first()

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
                        "user_level": price_data.user_level.title if price_data and price_data.user_level else "میهمان",
                        "extra_capacity_price": price_data.extra_passenger_price if price_data else 0
                    } if status == "open" else None
                })

            first_price_data_qs = room.date_prices.filter(
                start_date__lte=start_date_obj,
                end_date__gte=start_date_obj,
                user_level=user_level
            ).order_by('-id')
            if not first_price_data_qs.exists():
                first_price_data_qs = room.date_prices.filter(
                    start_date__lte=start_date_obj,
                    end_date__gte=start_date_obj,
                    user_level__isnull=True
                ).order_by('-id')
            first_price_data = first_price_data_qs.select_related('user_level').first()
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
                    "user_level": first_price_data.user_level.title if first_price_data.user_level else "میهمان",
                    "extra_capacity_price": first_price_data.extra_passenger_price
                },
                "night_count": night_count,
                "price_calendar": price_calendar
            }

        room_data = list(room_dict.values())

        # --- Single room ---
        if not passengers_list:
            room_data.sort(key=lambda x: x['price']['total_price_discount'] or float('inf'))
            return Response(room_data)

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
        """محاسبه کمترین قیمت برای هر هتل بدون اعمال تخفیف ثابت"""
        # دریافت تاریخ امروز برای بررسی قیمت‌ها و تخفیف‌ها
        today = timezone.now().date()
        hotel_min_price_map = {}
        
        for hotel in hotels:
            # دریافت تمام اتاق‌های مربوط به هتل
            rooms = Room.objects.filter(hotel=hotel)
            min_price = None
            min_price_data = {}

            for room in rooms:
                # دریافت قیمت‌های معتبر برای اتاق در تاریخ امروز
                prices = RoomDatePrice.objects.filter(
                    room=room,
                    start_date__lte=today,
                    end_date__gte=today
                ).select_related('room')

                for price in prices:
                    # قیمت اصلی اتاق بدون اعمال تخفیف ثابت
                    original_price = price.price
                    total_price = original_price

                    # اعمال تخفیف درصدی (در صورت وجود و معتبر بودن تاریخ تخفیف)
                    if price.discount_type == 'percentage' and price.discount_date and price.discount_date >= today:
                        total_price = original_price * (1 - price.discount_value / 100)
                    # تخفیف ثابت اعمال نمی‌شود، اما اطلاعات آن حفظ می‌شود

                    # بررسی کمترین قیمت برای هتل
                    if min_price is None or total_price < min_price:
                        min_price = total_price
                        min_price_data = {
                            'total_price': int(total_price),  # قیمت نهایی بدون تخفیف ثابت
                            'original_total_price': int(original_price),  # قیمت اصلی
                            'discount_type': price.discount_type,  # نوع تخفیف (برای اطلاعات)
                            'discount_value': price.discount_value,  # مقدار تخفیف (برای اطلاعات)
                            'discount_date': price.discount_date  # تاریخ تخفیف (برای اطلاعات)
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
        # دریافت هتل‌های با پیشنهاد ویژه
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
        # دریافت هتل‌های با فروش شگفت‌انگیز
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
        # دریافت هتل‌های پرفروش
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
logger = logging.getLogger(__name__)

class ReservationCreateAPIView(generics.CreateAPIView):
    serializer_class = ReservationCreateSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="ایجاد رزرو موقت",
        operation_description="""
        ایجاد یک رزرو موقت برای کاربر و کاهش موقت موجودی اتاق‌ها.
        - اگر اتاق در حالت auto_approved باشد، رزرو مستقیماً confirmed می‌شود.
        - اگر نیاز به تأیید ادمین داشته باشد، capacity_status = pending.
        """,
        tags=["reservation-api"],
        request_body=ReservationCreateSerializer,
        responses={
            200: openapi.Response(
                description="رزرو با موفقیت ایجاد شد.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'tracking_code': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            400: openapi.Response(description="درخواست نامعتبر یا موجودی ناکافی."),
        }
    )
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        tracking_code = 'sfa' + ''.join(str(random.randint(0, 9)) for _ in range(10))

        def parse_jdate(value):
            if isinstance(value, str):
                try:
                    return jdatetime.date.fromisoformat(value)
                except ValueError:
                    return jdatetime.date.fromgregorian(date=date.fromisoformat(value))
            elif isinstance(value, dict):
                year, month, day = int(value["year"]), int(value["month"]), int(value["day"])
                if value.get("calendar") == "gregorian":
                    return jdatetime.date.fromgregorian(date=date(year, month, day))
                return jdatetime.date(year, month, day)
            elif isinstance(value, date):
                return jdatetime.date.fromgregorian(date=value)
            elif isinstance(value, jdatetime.date):
                return value
            raise ValidationError(f"فرمت تاریخ نامعتبر است: {value}")

        check_in_date = parse_jdate(data['date']['enter'])
        check_out_date = parse_jdate(data['date']['exit'])

        if check_in_date < jdatetime.date.today():
            raise ValidationError("تاریخ ورود نمی‌تواند قبل از امروز باشد.")
        if check_out_date <= check_in_date:
            raise ValidationError("تاریخ خروج باید بعد از تاریخ ورود باشد.")

        reserver_data = {}
        if hasattr(request.user, 'natural_profile'):
            profile = request.user.natural_profile
            reserver_data = {
                'reserver_first_name': profile.first_name or '',
                'reserver_last_name': profile.last_name or '',
                'reserver_national_code': profile.national_code or '',
                'reserver_phone_number': request.user.phone_number
            }

        reservation = Reservationhotel.objects.create(
            tracking_code=tracking_code,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            buyer=request.user,
            capacity_status='pending',
            payment_status='unpaid',
            **reserver_data
        )

        hotel_id = data.get('hotel_id')
        room_ids = data.get('room_id', [])
        nights = reservation.nights_count
        all_auto_approved = True

        reservation_rooms = []

        for room_id in room_ids:
            room = Room.objects.select_for_update().get(id=room_id, hotel_id=hotel_id)
            quantity = 1

            auto_approval = False
            if room.auto_approved_count >= quantity:
                auto_approval = True
            elif room.count >= quantity:
                all_auto_approved = False
            else:
                raise ValidationError(f"موجودی کافی برای اتاق {room.title} وجود ندارد.")

            room.adjust_inventory_for_reservation(quantity, auto_approval)

            total_price = Decimal('0')
            for night in range(nights):
                current_date = check_in_date.togregorian() + timedelta(days=night)
                price = RoomDatePrice.objects.filter(
                    room=room,
                    start_date__lte=current_date,
                    end_date__gte=current_date
                ).first()
                total_price += Decimal(price.price) if price else Decimal('0')

            res_room = ReservationRoom(
                reservation=reservation,
                room=room,
                quantity=quantity,
                price_per_night=total_price / nights if nights > 0 else total_price,
                subtotal=total_price,
                primary_passengers_count=room.room_capacity,
                extra_passengers_count=room.extra_capacity,
            )
            reservation_rooms.append(res_room)

        ReservationRoom.objects.bulk_create(reservation_rooms)

        reservation.capacity_status = 'confirmed' if all_auto_approved else 'pending'
        total_price, total_extra, discount_amount, half_in, half_out, total_half, code_discount, final_price, room_fixed = reservation.calculate_total_price()
        
        # ذخیره تمام مقادیر محاسبه‌شده
        reservation.total_price = total_price
        reservation.final_price = final_price
        reservation.room_fixed_discount = room_fixed
        reservation.discount = code_discount
        reservation.half_day_in_charge = half_in
        reservation.half_day_out_charge = half_out
        reservation.total_half_day_charge = total_half
        reservation.total_extra_passenger_charge = total_extra
        reservation.save(update_fields=[
            'capacity_status', 
            'total_price', 
            'final_price', 
            'room_fixed_discount', 
            'discount', 
            'half_day_in_charge', 
            'half_day_out_charge', 
            'total_half_day_charge', 
            'total_extra_passenger_charge'
        ])

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"reservation_{reservation.tracking_code}",
            {
                "type": "status_update",
                "message": {
                    "capacity_status": reservation.capacity_status,
                    "timer": None
                },
            },
        )

        logger.info(f"✅ Reservation created successfully: {tracking_code}")
        return Response({"tracking_code": tracking_code})
    
    
    
# ای پی ای جزئيات یک رزرو با tracking_code
logger = logging.getLogger(__name__)

class ReservationDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="نمایش جزئیات رزرو",
        operation_description="""
        این API جزئیات یک رزرو خاص را بر اساس کد پیگیری (tracking_code) نمایش می‌دهد.
        
        ### نحوه استفاده
        - **tracking_code**: کد پیگیری رزرو که در URL به صورت `${tracking-code}` وارد می‌شود (مثلاً `sfa1234567890`).
        - **مثال درخواست**:
          ```
          GET /hotel/reservation/reservation-detail/sfa1234567890/
          ```
        - **پاسخ**:
          - `reserver`: اطلاعات رزروکننده (نام، نام خانوادگی، شماره موبایل، کد ملی).
          - `date.enter`: تاریخ ورود به هتل (فرمت ISO، مثلاً `1404-06-30`).
          - `date.exit`: تاریخ خروج از هتل (فرمت ISO، مثلاً `1404-07-02`).
          - `time.enter`: ساعت ورود به هتل (فرمت `HH:MM:SS`، مثلاً `14:00:00`).
          - `time.exit`: ساعت خروج از هتل (فرمت `HH:MM:SS`، مثلاً `12:00:00`).
          - `number_of_nights`: تعداد شب‌های اقامت (یک عدد صحیح).
          - `hotel_name`: نام هتل (رشته).
          - `hotel_star`: تعداد ستاره‌های هتل (یک عدد صحیح).
          - `city_name`: نام شهر هتل (رشته).
          - `province_name`: نام استان هتل (رشته).
          - `number_of_rooms`: تعداد اتاق‌های رزرو شده (یک عدد صحیح).
          - `half_charges.enter.enabled`: وضعیت پشتیبانی نیم‌شارژ ورود توسط هتل.
          - `half_charges.exit.enabled`: وضعیت پشتیبانی نیم‌شارژ خروج توسط هتل.
        - **اعتبارسنجی**: کاربر باید احراز هویت شده باشد و کد پیگیری باید متعلق به رزروهای او باشد.
        """,
        tags=["reservation-api"],
        responses={
            200: openapi.Response(
                description="جزئیات رزرو با موفقیت برگردانده شد.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'reserver': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'first_name': openapi.Schema(type=openapi.TYPE_STRING, description='نام رزروکننده', example='علی'),
                                'last_name': openapi.Schema(type=openapi.TYPE_STRING, description='نام خانوادگی رزروکننده', example='احمدی'),
                                'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description='شماره موبایل', example='09123456789'),
                                'national_code': openapi.Schema(type=openapi.TYPE_STRING, description='کد ملی', example='1234567890')
                            }
                        ),
                        'date': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'enter': openapi.Schema(type=openapi.TYPE_STRING, description='تاریخ ورود', example='1404-06-30'),
                                'exit': openapi.Schema(type=openapi.TYPE_STRING, description='تاریخ خروج', example='1404-07-02')
                            }
                        ),
                        'time': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'enter': openapi.Schema(type=openapi.TYPE_STRING, description='ساعت ورود', example='14:00:00'),
                                'exit': openapi.Schema(type=openapi.TYPE_STRING, description='ساعت خروج', example='12:00:00')
                            }
                        ),
                        'number_of_nights': openapi.Schema(type=openapi.TYPE_INTEGER, description='تعداد شب‌های اقامت', example=2),
                        'hotel_name': openapi.Schema(type=openapi.TYPE_STRING, description='نام هتل', example='هتل آزادی'),
                        'hotel_star': openapi.Schema(type=openapi.TYPE_INTEGER, description='تعداد ستاره‌ها', example=5),
                        'city_name': openapi.Schema(type=openapi.TYPE_STRING, description='نام شهر', example='تهران'),
                        'province_name': openapi.Schema(type=openapi.TYPE_STRING, description='نام استان', example='تهران'),
                        'number_of_rooms': openapi.Schema(type=openapi.TYPE_INTEGER, description='تعداد اتاق‌ها', example=1),
                        'half_charges': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'enter': openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        'enabled': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='وضعیت پشتیبانی نیم‌شارژ ورود توسط هتل', example=True)
                                    }
                                ),
                                'exit': openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        'enabled': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='وضعیت پشتیبانی نیم‌شارژ خروج توسط هتل', example=True)
                                    }
                                )
                            }
                        )
                    }
                )
            ),
            404: openapi.Response(description="رزرو با کد پیگیری داده‌شده یافت نشد."),
            403: openapi.Response(description="دسترسی غیرمجاز.")
        }
    )
    def get(self, request, tracking_code, *args, **kwargs):
        # دریافت رزرو
        reservation = get_object_or_404(Reservationhotel, tracking_code=tracking_code)
        if reservation.buyer != request.user:
            raise ValidationError("شما به این رزرو دسترسی ندارید.")

        # اطلاعات هتل از اولین اتاق رزرو شده
        reservation_room = reservation.reservation_rooms.first()
        if not reservation_room or not reservation_room.room or not reservation_room.room.hotel:
            raise NotFound("اطلاعات هتل یا اتاق یافت نشد.")

        hotel = reservation_room.room.hotel
        city = hotel.city
        province = city.province if hasattr(city, 'province') else None

        # بررسی پروفایل حقیقی کاربر برای اطلاعات رزروکننده
        reserver_data = {
            'first_name': '',
            'last_name': '',
            'phone_number': '',
            'national_code': ''
        }
        try:
            profile = request.user.natural_profile
            user = request.user
            if (profile.first_name and profile.last_name and 
                profile.national_code and hasattr(user, 'phone_number') and user.phone_number):
                reserver_data = {
                    'first_name': profile.first_name,
                    'last_name': profile.last_name,
                    'phone_number': user.phone_number,
                    'national_code': profile.national_code
                }
        except AttributeError:
            logger.warning("پروفایل حقیقی کاربر یا شماره موبایل وجود ندارد یا کامل نیست.")

        # آماده‌سازی پاسخ
        response_data = {
            'reserver': reserver_data,
            'date': {
                'enter': reservation.check_in_date.isoformat() if reservation.check_in_date else None,
                'exit': reservation.check_out_date.isoformat() if reservation.check_out_date else None
            },
            'time': {
                'enter': hotel.check_in_time.strftime('%H:%M:%S') if hasattr(hotel, 'check_in_time') and hotel.check_in_time else None,
                'exit': hotel.check_out_time.strftime('%H:%M:%S') if hasattr(hotel, 'check_out_time') and hotel.check_out_time else None
            },
            'number_of_nights': reservation.nights_count,
            'hotel_name': hotel.name,
            'hotel_star': hotel.stars,
            'city_name': city.name if city else None,
            'province_name': province.name if province else None,
            'number_of_rooms': reservation.total_rooms,
            'half_charges': {
                'enter': {
                    'enabled': hotel.has_check_in_half_day_charge
                },
                'exit': {
                    'enabled': hotel.has_check_out_half_day_charge
                }
            }
        }

        return Response(response_data, status=status.HTTP_200_OK)
    
    

# ای پی ای نمایش عکس هتل برای رزرو 
logger = logging.getLogger(__name__)


class HotelImageAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="نمایش لینک عکس هتل و اسلاگ هتل",
        operation_description="""
        این API لینک عکس اصلی هتل و اسلاگ هتل را بر اساس کد پیگیری (tracking_code) نمایش می‌دهد.
        
        ### نحوه استفاده
        - **tracking_code**: کد پیگیری رزرو که در URL به صورت `${tracking-code}` وارد می‌شود (مثلاً `sfa1234567890`).
        
        - **مثال درخواست**:
          ```
          GET /hotel/reservation/hotel-slug/sfa1234567890/
          ```
        - **پاسخ**:
          ```json
          {
            "hotel_image": "https://safarnameh24.com/media/images/hotels/hotel-azadi/main_image.jpg",
            "hotel_slug": "hotel-azadi"
          }
          ```
        """,
        tags=["reservation-api"],
        responses={
            200: openapi.Response(
                description="اطلاعات هتل با موفقیت برگردانده شد.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'hotel_image': openapi.Schema(type=openapi.TYPE_STRING, description='لینک عکس اصلی هتل'),
                        'hotel_slug': openapi.Schema(type=openapi.TYPE_STRING, description='اسلاگ هتل'),
                    }
                )
            ),
            404: openapi.Response(description="رزرو یا هتل یافت نشد."),
            403: openapi.Response(description="دسترسی غیرمجاز."),
        }
    )
    def get(self, request, tracking_code, *args, **kwargs):
        reservation = get_object_or_404(Reservationhotel, tracking_code=tracking_code)
        if reservation.buyer != request.user:
            raise ValidationError("شما به این رزرو دسترسی ندارید.")

        reservation_room = reservation.reservation_rooms.first()
        if not reservation_room or not reservation_room.room or not reservation_room.room.hotel:
            raise NotFound("اطلاعات هتل یا اتاق یافت نشد.")

        hotel = reservation_room.room.hotel

        if not hotel.main_image:
            raise NotFound("عکس اصلی هتل موجود نیست.")

        # ساخت لینک کامل
        site_url = getattr(settings, "SITE_URL", "https://safarnameh24.com")
        image_url = f"{site_url}{hotel.main_image.url}"

        response_data = {
            'hotel_image': image_url,
            'hotel_slug': hotel.slug
        }

        return Response(response_data, status=status.HTTP_200_OK)
    
    


# ای پی ای جزئیات صورت حساب رزرو و ویرایش صورتحساب 
logger = logging.getLogger(__name__)

class ReservationInvoiceAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def parse_number(self, value):
        """
        تبدیل رشته یا عدد با یا بدون ویرگول به Decimal.
        اگر مقدار None باشد، مقدار 0 برمی‌گردد.
        """
        if value is None:
            return Decimal('0')
        return Decimal(str(value).replace(',', '').strip())

    @swagger_auto_schema(
        operation_summary="دریافت صورت‌حساب رزرو",
        operation_description="""
        مشاهده صورت‌حساب رزرو بر اساس **tracking_code**.

        **فیلدهای خروجی:**
        - `nights_count`: تعداد شب‌های اقامت
        - `total_price`: مجموع قیمت اتاق‌ها
        - `extra_passengers`: مجموع قیمت نفرات اضافه
        - `half_charges`: مجموع نیم‌شارژها
        - `discount_on_purchase`: تخفیف ثابت اتاق‌ها
        - `discount_code`: تخفیف کد تخفیف
        - `wallet_withdraw`: مبلغ برداشت از کیف پول
        - `final_price`: قیمت نهایی (پس از کسر تمام تخفیف‌ها و برداشت از کیف پول)
        """,
        responses={
            200: openapi.Response(description="جزئیات صورت‌حساب رزرو"),
            403: openapi.Response(description="عدم دسترسی به رزرو"),
            404: openapi.Response(description="رزرو یافت نشد"),
        },
        tags=["reservation-api"]
    )
    def get(self, request, tracking_code):
        reservation = get_object_or_404(Reservationhotel, tracking_code=tracking_code)
        if reservation.buyer != request.user:
            logger.warning(f"کاربر {request.user.phone_number} به رزرو {tracking_code} دسترسی ندارد.")
            raise ValidationError("شما به این رزرو دسترسی ندارید.")

        # استفاده مستقیم از مقادیر ذخیره‌شده در رزرو
        response_data = {
            "nights_count": reservation.nights_count,
            "total_price": int(self.parse_number(reservation.total_price)),
            "extra_passengers": int(self.parse_number(reservation.total_extra_passenger_charge)),
            "half_charges": int(self.parse_number(reservation.total_half_day_charge)),
            "discount_on_purchase": int(self.parse_number(reservation.room_fixed_discount)),
            "discount_code": int(self.parse_number(reservation.discount)),
            "wallet_withdraw": int(self.parse_number(reservation.wallet_withdrawal_amount)),
            "final_price": int(self.parse_number(reservation.final_price))
        }

        # لاگ کردن مقادیر برای دیباگ
        logger.debug(f"ReservationInvoiceAPIView response: {response_data}")

        return Response(response_data, status=status.HTTP_200_OK)
    
    

# ای پی ای توضیحات تکمیلی رزرو 
class ReservationDescriptionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="دریافت توضیحات رزرو",
        operation_description="دریافت توضیحات تکمیلی یک رزرو بر اساس کد پیگیری.",
        tags=["reservation-api"]
    )
    def get(self, request, tracking_code):
        reservation = get_object_or_404(Reservationhotel, tracking_code=tracking_code)
        return Response({
            'description': reservation.additional_notes
        })

    @swagger_auto_schema(
        operation_summary="بروزرسانی توضیحات رزرو",
        operation_description="بروزرسانی توضیحات تکمیلی یک رزرو بر اساس کد پیگیری.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['description'],
            properties={
                'description': openapi.Schema(type=openapi.TYPE_STRING, description='توضیحات جدید رزرو')
            }
        ),
        tags=["reservation-api"]
    )
    def put(self, request, tracking_code):
        reservation = get_object_or_404(Reservationhotel, tracking_code=tracking_code)
        notes = request.data.get('description', None)
        if notes is None:
            return Response({'detail': 'فیلد description الزامی است.'}, status=status.HTTP_400_BAD_REQUEST)

        reservation.additional_notes = notes
        reservation.save(update_fields=['additional_notes'])
        return Response({
            'description': reservation.additional_notes
        }, status=status.HTTP_200_OK)






# views.py
logger = logging.getLogger(__name__)

def validate_phone_number(value):
    if not re.match(r'^09\d{9}$', value):
        raise ValidationError('شماره موبایل باید به فرمت 09xxxxxxxxx باشد')

def validate_national_code(value):
    if not re.match(r'^\d{10}$', value):
        raise ValidationError('کد ملی باید 10 رقمی باشد')
    check_digits = int(value[9])
    total = sum(int(value[i]) * (10 - i) for i in range(9)) % 11
    if int(value[3:9]) == 0 or not ((total < 2 and check_digits == total) or (total >= 2 and check_digits == (11 - total))):
        raise ValidationError('کد ملی معتبر نیست')

class ReservationRoomDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="دریافت اطلاعات رزرو برای ویرایش",
        operation_description="""
        این API اطلاعات کامل یک رزرو را بر اساس کد پیگیری (tracking_code) برای ویرایش بازمی‌گرداند.

        **ساختار خروجی:**
        - `reserver`: اطلاعات رزروکننده شامل:
            - `first_name`: نام رزروکننده
            - `last_name`: نام خانوادگی رزروکننده
            - `phone_number`: شماره موبایل
            - `national_code`: کد ملی
        - `rooms`: لیست اتاق‌های رزرو شده شامل:
            - `id`: شناسه اتاق
            - `name`: نام اتاق
            - `capacity`: ظرفیت اصلی اتاق
            - `extra_capacity`: ظرفیت اضافه اتاق
            - `extra_capacity_price`: قیمت هر نفر اضافه
            - `discount_on_purchase`: تخفیف ثابت اتاق
            - `passengers`: شامل:
                - `main_passenger`: اطلاعات مسافر اصلی
                - `other_passengers`: لیست سایر مسافران
                - `extra_capacity_passengers`: لیست مسافران اضافه
            - `half_charges`: شامل نیم‌شارژها:
                - `enter`: وضعیت و قیمت نیم‌شارژ ورود (بر اساس پشتیبانی هتل)
                - `exit`: وضعیت و قیمت نیم‌شارژ خروج (بر اساس پشتیبانی هتل)
        """,
        tags=["reservation-api"]
    )
    def get(self, request, tracking_code):
        reservation = get_object_or_404(Reservationhotel, tracking_code=tracking_code)
        if reservation.buyer != request.user:
            raise ValidationError("شما به این رزرو دسترسی ندارید.")

        # اطلاعات رزروکننده
        reserver_data = {
            'first_name': reservation.reserver_first_name or '',
            'last_name': reservation.reserver_last_name or '',
            'phone_number': reservation.reserver_phone_number or '',
            'national_code': reservation.reserver_national_code or ''
        }

        response_data = {
            "reserver": reserver_data,
            "rooms": []
        }

        for res_room in reservation.reservation_rooms.all():
            if not res_room.room or not res_room.room.hotel:
                raise NotFound("اطلاعات هتل یا اتاق یافت نشد.")
            
            hotel = res_room.room.hotel
            res_room.calculate_room_prices()
            res_room.calculate_half_day_prices()

            # همیشه قیمت‌های نیم‌شارژ نمایش داده شوند (اگر هتل پشتیبانی کند)
            half_day_in_price = int(res_room.half_day_in_price or 0) if hotel.has_check_in_half_day_charge else 0
            half_day_out_price = int(res_room.half_day_out_price or 0) if hotel.has_check_out_half_day_charge else 0

            room_data = {
                "id": res_room.room.id if res_room.room else None,
                "name": res_room.room.title if res_room.room else "",
                "capacity": int(res_room.room.room_capacity if res_room.room else 0),
                "extra_capacity": int(res_room.room.extra_capacity if res_room.room else 0),
                "extra_capacity_price": int(res_room.extra_passenger_price or 0),
                "discount_on_purchase": int(res_room.fixed_discount or 0),
                "passengers": {
                    "main_passenger": {},
                    "other_passengers": [],
                    "extra_capacity_passengers": []
                },
                "half_charges": {
                    "enter": {
                        "enabled": res_room.half_day_in_selected and hotel.has_check_in_half_day_charge,
                        "price": half_day_in_price,
                        "available": hotel.has_check_in_half_day_charge  # نشان‌دهنده امکان انتخاب توسط کاربر
                    },
                    "exit": {
                        "enabled": res_room.half_day_out_selected and hotel.has_check_out_half_day_charge,
                        "price": half_day_out_price,
                        "available": hotel.has_check_out_half_day_charge  # نشان‌دهنده امکان انتخاب توسط کاربر
                    }
                }
            }

            for passenger in res_room.passengers.all():
                passenger_data = {
                    "first_name": passenger.first_name,
                    "last_name": passenger.last_name,
                    "phone_number": passenger.mobile_number or "",
                    "national_code": passenger.national_code or ""
                }
                if passenger.passenger_type == "primary":
                    room_data["passengers"]["main_passenger"] = passenger_data
                elif passenger.passenger_type == "secondary":
                    room_data["passengers"]["other_passengers"].append(passenger_data)
                elif passenger.passenger_type == "extra":
                    room_data["passengers"]["extra_capacity_passengers"].append(passenger_data)

            response_data["rooms"].append(room_data)

        return Response(response_data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="بروزرسانی اطلاعات رزرو",
        operation_description="""
        این API امکان ویرایش رزرو را فراهم می‌کند و شامل موارد زیر است:

        **ورودی:**
        - `reserver`: اطلاعات رزروکننده شامل نام، نام خانوادگی، شماره موبایل، و کد ملی
        - `rooms`: لیستی از اتاق‌ها با اطلاعات مسافران و نیم‌شارژها
        """,
        tags=["reservation-api"]
    )
    def put(self, request, tracking_code):
        with transaction.atomic():
            reservation = get_object_or_404(Reservationhotel, tracking_code=tracking_code)
            if reservation.buyer != request.user:
                raise ValidationError("شما به این رزرو دسترسی ندارید.")

            data = request.data
            reserver_data = data.get('reserver', {})
            rooms_data = data.get('rooms', [])

            # اعتبارسنجی رزروکننده
            for field in ['first_name', 'last_name', 'phone_number', 'national_code']:
                if field not in reserver_data or not reserver_data[field]:
                    return Response({'detail': f'فیلد {field} برای رزروکننده الزامی است.'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                validate_phone_number(reserver_data['phone_number'])
                validate_national_code(reserver_data['national_code'])
            except ValidationError as e:
                return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

            # اعتبارسنجی اتاق‌ها و مسافران
            reservation_room_ids = [r.room.id for r in reservation.reservation_rooms.all() if r.room]
            passenger_national_codes = []
            for room_entry in rooms_data:
                if room_entry['id'] not in reservation_room_ids:
                    return Response({'detail': f'اتاق {room_entry["id"]} به این رزرو تعلق ندارد.'}, status=status.HTTP_400_BAD_REQUEST)

                passengers = room_entry.get('passengers', {})
                main_passenger = passengers.get('main_passenger', {})
                for field in ['first_name', 'last_name', 'phone_number', 'national_code']:
                    if field not in main_passenger or not main_passenger[field]:
                        return Response({'detail': f'فیلد {field} برای مسافر اصلی الزامی است (اتاق {room_entry["id"]}).'}, status=status.HTTP_400_BAD_REQUEST)
                try:
                    validate_phone_number(main_passenger['phone_number'])
                    validate_national_code(main_passenger['national_code'])
                except ValidationError as e:
                    return Response({'detail': f'خطا در اعتبارسنجی مسافر اصلی (اتاق {room_entry["id"]}): {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

                if main_passenger['national_code'] in passenger_national_codes:
                    return Response({'detail': f'کد ملی {main_passenger["national_code"]} تکراری است.'}, status=status.HTTP_400_BAD_REQUEST)
                passenger_national_codes.append(main_passenger['national_code'])

                for p_type in ['other_passengers', 'extra_capacity_passengers']:
                    for passenger in passengers.get(p_type, []):
                        if not passenger.get('first_name') or not passenger.get('last_name'):
                            return Response({'detail': f'نام و نام خانوادگی برای مسافر الزامی است (اتاق {room_entry["id"]}).'}, status=status.HTTP_400_BAD_REQUEST)
                        if passenger.get('phone_number'):
                            try:
                                validate_phone_number(passenger['phone_number'])
                            except ValidationError as e:
                                return Response({'detail': f'خطا در شماره موبایل مسافر (اتاق {room_entry["id"]}): {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
                        if passenger.get('national_code'):
                            try:
                                validate_national_code(passenger['national_code'])
                            except ValidationError as e:
                                return Response({'detail': f'خطا در کد ملی مسافر (اتاق {room_entry["id"]}): {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
                            if passenger['national_code'] in passenger_national_codes:
                                return Response({'detail': f'کد ملی {passenger["national_code"]} تکراری است.'}, status=status.HTTP_400_BAD_REQUEST)
                            passenger_national_codes.append(passenger['national_code'])

                # اعتبارسنجی و تنظیم نیم‌شارژها
                res_room = reservation.reservation_rooms.filter(room_id=room_entry['id']).first()
                hotel = res_room.room.hotel if res_room and res_room.room else None
                if hotel:
                    half_charges = room_entry.get('half_charges', {})
                    for charge_type in ['enter', 'exit']:
                        charge = half_charges.get(charge_type, {})
                        enabled = charge.get('enabled', False)
                        is_half_charge_supported = hotel.has_check_in_half_day_charge if charge_type == 'enter' else hotel.has_check_out_half_day_charge
                        if enabled and not is_half_charge_supported:
                            return Response({'detail': f'نیم‌شارژ {charge_type} برای این هتل پشتیبانی نمی‌شود (اتاق {room_entry["id"]}).'}, status=status.HTTP_400_BAD_REQUEST)
                        # تنظیم مقدار enabled
                        if charge_type == 'enter':
                            res_room.half_day_in_selected = enabled and is_half_charge_supported
                        else:
                            res_room.half_day_out_selected = enabled and is_half_charge_supported

            # ذخیره اطلاعات رزروکننده
            reservation.reserver_first_name = reserver_data['first_name']
            reservation.reserver_last_name = reserver_data['last_name']
            reservation.reserver_phone_number = reserver_data['phone_number']
            reservation.reserver_national_code = reserver_data['national_code']
            reservation.save(update_fields=['reserver_first_name', 'reserver_last_name', 'reserver_phone_number', 'reserver_national_code'])

            # ذخیره اطلاعات اتاق‌ها و مسافران
            res_rooms_list = list(reservation.reservation_rooms.all())
            for room_data, res_room in zip(rooms_data, res_rooms_list):
                passengers_data = room_data.get('passengers', {})
                half_charges = room_data.get('half_charges', {})

                # تنظیم نیم‌شارژها
                res_room.half_day_in_selected = half_charges.get('enter', {}).get('enabled', res_room.half_day_in_selected) and hotel.has_check_in_half_day_charge
                res_room.half_day_out_selected = half_charges.get('exit', {}).get('enabled', res_room.half_day_out_selected) and hotel.has_check_out_half_day_charge
                res_room.calculate_half_day_prices()  # محاسبه مجدد قیمت‌های نیم‌شارژ
                res_room.half_day_in_price = int(half_charges.get('enter', {}).get('price', res_room.half_day_in_price))
                res_room.half_day_out_price = int(half_charges.get('exit', {}).get('price', res_room.half_day_out_price))
                res_room.extra_passenger_price = int(room_data.get('extra_capacity_price', res_room.extra_passenger_price or 0))
                res_room.fixed_discount = int(room_data.get('discount_on_purchase', res_room.fixed_discount or 0))
                res_room.calculate_room_prices()
                res_room.save(update_fields=[
                    'half_day_in_selected', 'half_day_out_selected',
                    'half_day_in_price', 'half_day_out_price',
                    'extra_passenger_price', 'fixed_discount',
                    'price_per_night', 'subtotal'
                ])

                res_room.passengers.all().delete()
                main_passenger = passengers_data.get('main_passenger', {})
                ReservationRoomPassenger.objects.create(
                    reservation_room=res_room,
                    passenger_type='primary',
                    first_name=main_passenger['first_name'],
                    last_name=main_passenger['last_name'],
                    mobile_number=main_passenger['phone_number'],
                    national_code=main_passenger['national_code'],
                    is_primary=True
                )

                for p_type in ['other_passengers', 'extra_capacity_passengers']:
                    passenger_type_db = 'secondary' if p_type == 'other_passengers' else 'extra'
                    for passenger in passengers_data.get(p_type, []):
                        ReservationRoomPassenger.objects.create(
                            reservation_room=res_room,
                            passenger_type=passenger_type_db,
                            first_name=passenger['first_name'],
                            last_name=passenger['last_name'],
                            mobile_number=passenger.get('phone_number', None),
                            national_code=passenger.get('national_code', None),
                            is_primary=False
                        )

            # محاسبه و ذخیره قیمت‌های نهایی
            total_price, total_extra, discount_amount, half_in, half_out, total_half, code_discount, final_price, room_fixed = reservation.calculate_total_price()
            reservation.total_price = total_price
            reservation.total_extra_passenger_charge = total_extra
            reservation.discount = code_discount
            reservation.room_fixed_discount = room_fixed
            reservation.half_day_in_charge = half_in
            reservation.half_day_out_charge = half_out
            reservation.total_half_day_charge = total_half
            reservation.final_price = final_price
            reservation._skip_price_calculation = True
            reservation.save(update_fields=[
                'total_price', 'total_extra_passenger_charge', 'discount',
                'room_fixed_discount', 'half_day_in_charge',
                'half_day_out_charge', 'total_half_day_charge', 'final_price'
            ])

        return Response({'detail': 'رزرو با موفقیت بروزرسانی شد.'}, status=status.HTTP_200_OK)
    
    
    
#لیست مسافران برای بخش رزرو
class PassengerListForReservationView(generics.GenericAPIView):
    """
    API لیست مسافران برای بخش رزرواسیون بدون صفحه‌بندی.
    """
    permission_classes = (IsAuthenticated,)
    serializer_class = PassengerSerializer

    def get_queryset(self):
        # فقط مسافرانی که به کاربر جاری تعلق دارند
        return Passenger.objects.filter(user=self.request.user)

    @swagger_auto_schema(
        tags=["reservation-api"],
        operation_summary="لیست مسافران برای رزرواسیون",
        operation_description="تمام مسافران ثبت‌شده توسط کاربر جاری را بدون صفحه‌بندی بازمی‌گرداند.",
        responses={200: PassengerSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as exc:
            return Response({
                "error": str(exc),
                "exception_type": exc.__class__.__name__,
                "trace": traceback.format_exc(limit=2)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    
    
    
# ای پی ای کد تخفیف برای رزرو 
llogger = logging.getLogger(__name__)

# متغیر محلی برای کنترل ارسال SMS و تخصیص امتیاز
_thread_locals = local()

def set_skip_points_and_sms(value):
    setattr(_thread_locals, 'skip_points_and_sms', value)

def get_skip_points_and_sms():
    return getattr(_thread_locals, 'skip_points_and_sms', False)

class ApplyDiscountCodeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="اعمال کد تخفیف روی رزرو",
        operation_description="اعمال کد تخفیف وارد شده توسط کاربر روی رزرو (برای اتاق‌ها یا هتل‌ها). کد تخفیف به‌صورت غیرحساس به حروف بزرگ و کوچک پردازش می‌شود.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'discount_code': openapi.Schema(type=openapi.TYPE_STRING, description='کد تخفیف وارد شده'),
            },
            required=['discount_code'],
        ),
        responses={
            200: openapi.Response(description="کد تخفیف با موفقیت اعمال شد."),
            400: openapi.Response(description="کد تخفیف نامعتبر، منقضی شده یا فعال نشده است."),
            403: openapi.Response(description="کد قبلاً استفاده شده است یا امتیاز کافی نیست."),
            404: openapi.Response(description="رزرو یافت نشد.")
        },
        tags=["reservation-api"]
    )
    def post(self, request, tracking_code, *args, **kwargs):
        code = request.data.get("discount_code")
        if not code:
            return Response({"error": "discount_code الزامی است."}, status=status.HTTP_400_BAD_REQUEST)

        code = code.upper()

        try:
            reservation = Reservationhotel.objects.get(tracking_code=tracking_code, buyer=request.user)
        except Reservationhotel.DoesNotExist:
            return Response({"error": "رزرو با کد پیگیری وارد شده یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

        room_discount = None
        hotel_discount = None
        try:
            room_discount = RoomDiscountCode.objects.get(code__iexact=code)
        except RoomDiscountCode.DoesNotExist:
            try:
                hotel_discount = HotelDiscountCode.objects.get(code__iexact=code)
            except HotelDiscountCode.DoesNotExist:
                return Response({"error": "کد تخفیف نامعتبر است."}, status=status.HTTP_400_BAD_REQUEST)

        now_j = jdatetime.datetime.now().date()
        discount_obj = room_discount or hotel_discount

        logger.debug(f"discount_obj.discount_value: {discount_obj.discount_value}")

        if discount_obj.expires_at and discount_obj.expires_at < now_j:
            return Response({"error": "کد تخفیف منقضی شده است."}, status=status.HTTP_400_BAD_REQUEST)

        if discount_obj.users.exists() and request.user not in discount_obj.users.all():
            return Response({"error": "این کد تخفیف برای شما در دسترس نیست."}, status=status.HTTP_400_BAD_REQUEST)

        if room_discount and not any(rr.room == room_discount.room for rr in reservation.reservation_rooms.all()):
            return Response({"error": "این کد تخفیف برای اتاق‌های این رزرو معتبر نیست."}, status=status.HTTP_400_BAD_REQUEST)
        elif hotel_discount and reservation.reservation_rooms.first().room.hotel != hotel_discount.hotel:
            return Response({"error": "این کد تخفیف برای این هتل معتبر نیست."}, status=status.HTTP_400_BAD_REQUEST)

        if reservation.payment_status == 'paid' or reservation.capacity_status == 'rejected':
            return Response({"error": "نمی‌توان روی رزرو پرداخت‌شده یا لغو‌شده تخفیف اعمال کرد."}, status=status.HTTP_400_BAD_REQUEST)

        user_level = getattr(getattr(request.user, 'natural_profile', None), 'level', None)
        if discount_obj.user_level and discount_obj.user_level != user_level:
            return Response({"error": "این کد تخفیف برای سطح کاربری شما فعال نیست."}, status=status.HTTP_400_BAD_REQUEST)

        # بررسی امتیاز مورد نیاز برای کد تخفیف
        user_points = getattr(request.user, 'customer_points', None)
        if user_points and discount_obj.required_points > user_points.points:
            return Response({"error": "امتیاز کافی برای استفاده از این کد تخفیف ندارید."}, status=status.HTTP_403_FORBIDDEN)

        # بررسی اینکه کاربر قبلاً از کد تخفیف استفاده نکرده باشد
        if hotel_discount:
            activation_exists = DiscountActivationRecord.objects.filter(
                user=request.user,
                hotel_discount_code=hotel_discount,
                discount_type='hotel',
                reward_claimed=True
            ).exists()
        else:
            activation_exists = DiscountActivationRecord.objects.filter(
                user=request.user,
                room_discount_code=room_discount,
                discount_type='room',
                reward_claimed=True
            ).exists()

        if activation_exists:
            return Response({"error": "شما قبلاً از این کد تخفیف استفاده کرده‌اید."}, status=status.HTTP_403_FORBIDDEN)

        with transaction.atomic():
            # حذف رکورد قبلی DiscountActivationRecord اگر وجود داشته باشد و reward_claimed=False باشد
            if hotel_discount:
                DiscountActivationRecord.objects.filter(
                    user=request.user,
                    hotel_discount_code=hotel_discount,
                    discount_type='hotel',
                    reward_claimed=False
                ).delete()
            else:
                DiscountActivationRecord.objects.filter(
                    user=request.user,
                    room_discount_code=room_discount,
                    discount_type='room',
                    reward_claimed=False
                ).delete()

            # ایجاد رکورد جدید DiscountActivationRecord با reward_claimed=False
            if hotel_discount:
                activation_record = DiscountActivationRecord.objects.create(
                    user=request.user,
                    hotel_discount_code=hotel_discount,
                    discount_type='hotel',
                    reward_claimed=False
                )
            else:
                activation_record = DiscountActivationRecord.objects.create(
                    user=request.user,
                    room_discount_code=room_discount,
                    discount_type='room',
                    reward_claimed=False
                )

            # کسر امتیاز اگر لازم باشد
            if discount_obj.required_points > 0:
                customer_points, created = CustomerClubPoint.objects.get_or_create(
                    user=request.user,
                    defaults={'points': 0}
                )
                customer_points.points -= discount_obj.required_points
                set_skip_points_and_sms(True)
                customer_points.save()
                set_skip_points_and_sms(False)
                logger.info(f"امتیاز {discount_obj.required_points} از کاربر {request.user.phone_number} برای کد تخفیف {code} کسر شد.")
                send_customer_club_deduct_sms(
                    phone_number=request.user.phone_number,
                    user_name=request.user.first_name or request.user.phone_number,
                    deducted_points=discount_obj.required_points,
                    current_points=customer_points.points
                )

            # محاسبه قیمت جدید با تخفیف
            reservation.applied_discount_code = code
            discount_value = min(Decimal(discount_obj.discount_value), reservation.final_price)
            total, total_extra, _, half_day_in_charge, half_day_out_charge, total_half_day_charge, _, final_without_promo, room_fixed_discount = reservation.calculate_total_price()

            new_total_discount = discount_value
            new_final_price = max(Decimal('0'), final_without_promo - new_total_discount - room_fixed_discount)

            logger.debug(f"discount_value: {discount_value}, new_total_discount: {new_total_discount}, final_without_promo: {final_without_promo}, new_final_price: {new_final_price}")

            reservation.discount = new_total_discount
            reservation.final_price = new_final_price
            reservation.total_price = total
            reservation.half_day_in_charge = half_day_in_charge
            reservation.half_day_out_charge = half_day_out_charge
            reservation.total_half_day_charge = total_half_day_charge
            reservation.total_extra_passenger_charge = total_extra

            set_skip_points_and_sms(True)  # جلوگیری از اجرای سیگنال Reservationhotel
            reservation._skip_price_calculation = True
            reservation.save(update_fields=['applied_discount_code', 'discount', 'final_price', 'total_price', 'half_day_in_charge', 'half_day_out_charge', 'total_half_day_charge', 'total_extra_passenger_charge'])
            delattr(reservation, '_skip_price_calculation')
            set_skip_points_and_sms(False)

        return Response({
            "status": "ok",
            "tracking_code": reservation.tracking_code,
            "discount_code": discount_obj.code,
            "discount_value": int(discount_value),
            "final_price": int(reservation.final_price),
            "total_discount": int(reservation.discount),
            "remaining_uses": discount_obj.remaining_uses,
            "usage_limit": discount_obj.usage_limit
        }, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="حذف کد تخفیف از رزرو",
        operation_description="حذف کد تخفیف اعمال‌شده از رزرو.",
        responses={
            200: openapi.Response(description="کد تخفیف با موفقیت حذف شد."),
            404: openapi.Response(description="رزرو یا کد تخفیف یافت نشد.")
        },
        tags=["reservation-api"]
    )
    def delete(self, request, tracking_code, *args, **kwargs):
        try:
            reservation = Reservationhotel.objects.get(tracking_code=tracking_code, buyer=request.user)
        except Reservationhotel.DoesNotExist:
            return Response({"error": "رزرو با کد پیگیری وارد شده یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

        if reservation.discount <= 0 or not reservation.applied_discount_code:
            return Response({"error": "هیچ کد تخفیفی برای حذف وجود ندارد."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # حذف رکورد DiscountActivationRecord با reward_claimed=False
            discount_obj = RoomDiscountCode.objects.filter(code__iexact=reservation.applied_discount_code).first() or \
                          HotelDiscountCode.objects.filter(code__iexact=reservation.applied_discount_code).first()
            if discount_obj:
                DiscountActivationRecord.objects.filter(
                    user=request.user,
                    discount_type='room' if isinstance(discount_obj, RoomDiscountCode) else 'hotel',
                    **({'room_discount_code': discount_obj} if isinstance(discount_obj, RoomDiscountCode) else {'hotel_discount_code': discount_obj}),
                    reward_claimed=False
                ).delete()
                logger.debug(f"DiscountActivationRecord برای کد تخفیف {reservation.applied_discount_code} حذف شد.")

                # بازگرداندن امتیاز اگر کد تخفیف نیاز به امتیاز داشته باشد
                if discount_obj.required_points > 0:
                    customer_points, created = CustomerClubPoint.objects.get_or_create(
                        user=request.user,
                        defaults={'points': 0}
                    )
                    customer_points.points += discount_obj.required_points
                    set_skip_points_and_sms(True)
                    customer_points.save()
                    set_skip_points_and_sms(False)
                    logger.info(f"امتیاز {discount_obj.required_points} به کاربر {request.user.phone_number} برای حذف کد تخفیف {reservation.applied_discount_code} بازگردانده شد.")
                    send_customer_club_sms(
                        phone_number=request.user.phone_number,
                        user_name=request.user.first_name or request.user.phone_number,
                        added_points=discount_obj.required_points,
                        current_points=customer_points.points
                    )

            total, total_extra, _, half_day_in_charge, half_day_out_charge, total_half_day_charge, _, final_without_promo, room_fixed_discount = reservation.calculate_total_price()
            reservation.discount = Decimal('0')
            reservation.final_price = final_without_promo - room_fixed_discount
            reservation.total_price = total
            reservation.half_day_in_charge = half_day_in_charge
            reservation.half_day_out_charge = half_day_out_charge
            reservation.total_half_day_charge = total_half_day_charge
            reservation.total_extra_passenger_charge = total_extra
            reservation.applied_discount_code = None

            set_skip_points_and_sms(True)  # جلوگیری از اجرای سیگنال Reservationhotel
            reservation._skip_price_calculation = True
            reservation.save(update_fields=['applied_discount_code', 'discount', 'final_price', 'total_price', 'half_day_in_charge', 'half_day_out_charge', 'total_half_day_charge', 'total_extra_passenger_charge'])
            delattr(reservation, '_skip_price_calculation')
            set_skip_points_and_sms(False)

        return Response({
            "status": "ok",
            "tracking_code": reservation.tracking_code,
            "discount_code": None,
            "final_price": int(reservation.final_price),
            "total_discount": int(reservation.discount)
        }, status=status.HTTP_200_OK)
        
        
        
        
# ای پی ای برداشت از کیف پول 
logger = logging.getLogger(__name__)

class WalletWithdrawAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="تنظیم برداشت از کیف پول برای رزرو",
        operation_description="""
        این API به کاربر احراز هویت‌شده اجازه می‌دهد مبلغ برداشت از کیف پول را برای یک رزرو مشخص تنظیم یا حذف کند.
        مبلغ فقط در صورت نهایی شدن پرداخت رزرو (payment_status='paid') از موجودی کیف پول کسر می‌شود.

        **ورودی‌ها (در body درخواست POST):**
        - `amount`: مبلغ برداشت (تومان، حداقل ۱۰,۰۰۰ تومان، حداکثر موجودی کیف پول یا قیمت نهایی رزرو)

        **حالات خاص:**
        - برای حذف برداشت، مقدار `amount=0` ارسال کنید یا از متد DELETE استفاده کنید.
        - فقط برای رزروهای با وضعیت پرداخت `unpaid` قابل تنظیم است.
        - مبلغ زیر ۱۰,۰۰۰ تومان یا بیشتر از موجودی کیف پول/قیمت نهایی رزرو مجاز نیست.

        **خروجی:**
        - در صورت موفقیت: پیام تأیید تنظیم یا حذف برداشت.
        - در صورت خطا: پیام خطا با جزئیات.
        """,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'amount': openapi.Schema(type=openapi.TYPE_INTEGER, description='مبلغ برداشت (تومان، ۰ برای حذف برداشت)'),
            },
            required=['amount']
        ),
        responses={
            200: openapi.Response(description="برداشت تنظیم یا حذف شد."),
            400: openapi.Response(description="خطاهای اعتبارسنجی (مثل مبلغ نامعتبر یا وضعیت پرداخت نامناسب)."),
            403: openapi.Response(description="عدم دسترسی به رزرو"),
            404: openapi.Response(description="رزرو یا کیف پول یافت نشد."),
        },
        tags=["reservation-api"]
    )
    def post(self, request, tracking_code):
        # دریافت رزرو با استفاده از tracking_code
        reservation = get_object_or_404(Reservationhotel, tracking_code=tracking_code)
        
        # بررسی دسترسی کاربر
        if reservation.buyer != request.user:
            logger.warning(f"کاربر {request.user.phone_number} به رزرو {tracking_code} دسترسی ندارد.")
            return Response({"detail": "شما به این رزرو دسترسی ندارید."}, status=status.HTTP_403_FORBIDDEN)

        # بررسی وضعیت پرداخت رزرو
        if reservation.payment_status != 'unpaid':
            logger.warning(f"تلاش برای تنظیم برداشت برای رزرو {tracking_code} با وضعیت پرداخت {reservation.payment_status}.")
            return Response({"detail": "نمی‌توان برای رزرو پرداخت‌شده یا در حال پرداخت برداشت تنظیم کرد."}, status=status.HTTP_400_BAD_REQUEST)

        # دریافت و اعتبارسنجی مبلغ
        amount_str = request.data.get('amount')
        try:
            amount = Decimal(str(amount_str).replace(',', '').strip())
        except (TypeError, ValueError, InvalidOperation):
            logger.error(f"مبلغ نامعتبر برای رزرو {tracking_code}: {amount_str}")
            return Response({"detail": "مبلغ نامعتبر است."}, status=status.HTTP_400_BAD_REQUEST)

        # اعتبارسنجی مبلغ
        if amount < 0:
            logger.error(f"مبلغ منفی برای رزرو {tracking_code}: {amount}")
            return Response({"detail": "مبلغ نمی‌تواند منفی باشد."}, status=status.HTTP_400_BAD_REQUEST)

        if amount > 0 and amount < 10000:
            logger.error(f"مبلغ کمتر از ۱۰,۰۰۰ تومان برای رزرو {tracking_code}: {amount}")
            return Response({"detail": "مبلغ باید حداقل ۱۰,۰۰۰ تومان باشد."}, status=status.HTTP_400_BAD_REQUEST)

        # دریافت کیف پول کاربر
        try:
            wallet = Wallet.objects.get(user=request.user)
        except Wallet.DoesNotExist:
            logger.error(f"کیف پول برای کاربر {request.user.phone_number} یافت نشد.")
            return Response({"detail": "کیف پول یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

        # بررسی موجودی کیف پول
        if amount > wallet.balance:
            logger.error(f"مبلغ بیشتر از موجودی کیف پول برای رزرو {tracking_code}: {amount} > {wallet.balance}")
            return Response({"detail": "مبلغ بیشتر از موجودی کیف پول است."}, status=status.HTTP_400_BAD_REQUEST)

        # محاسبه قیمت پایه (بدون کسر wallet_withdrawal_amount) برای مقایسه
        base_price = reservation.total_price + reservation.total_extra_passenger_charge + reservation.total_half_day_charge
        temp_final_price = base_price - reservation.discount - reservation.room_fixed_discount
        if amount > temp_final_price:
            logger.error(f"مبلغ بیشتر از قیمت نهایی رزرو {tracking_code}: {amount} > {temp_final_price}")
            return Response({"detail": "مبلغ بیشتر از قیمت نهایی رزرو است."}, status=status.HTTP_400_BAD_REQUEST)

        # تنظیم یا حذف برداشت
        with transaction.atomic():
            reservation.wallet_withdrawal_amount = amount
            if amount == 0:
                reservation.wallet_withdrawn = False  # بازنشانی فلگ در صورت حذف برداشت
                logger.info(f"برداشت از کیف پول برای رزرو {tracking_code} حذف شد.")
            else:
                logger.info(f"مبلغ برداشت {amount} برای رزرو {tracking_code} تنظیم شد.")
            reservation.save()  # این کار باعث بازمحاسبه final_price می‌شود

        # پاسخ مناسب
        message = "برداشت از کیف پول حذف شد." if amount == 0 else "برداشت از کیف پول تنظیم شد."
        return Response({"detail": message}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="حذف برداشت از کیف پول برای رزرو",
        operation_description="""
        این API به کاربر احراز هویت‌شده اجازه می‌دهد برداشت از کیف پول برای یک رزرو مشخص را حذف کند.
        این عمل مقدار `wallet_withdrawal_amount` را به صفر و فلگ `wallet_withdrawn` را به False تنظیم می‌کند.

        **حالات خاص:**
        - فقط برای رزروهای با وضعیت پرداخت `unpaid` قابل انجام است.

        **خروجی:**
        - در صورت موفقیت: پیام تأیید حذف برداشت.
        - در صورت خطا: پیام خطا با جزئیات.
        """,
        responses={
            200: openapi.Response(description="برداشت از کیف پول حذف شد."),
            400: openapi.Response(description="وضعیت پرداخت رزرو نامناسب است."),
            403: openapi.Response(description="عدم دسترسی به رزرو"),
            404: openapi.Response(description="رزرو یافت نشد."),
        },
        tags=["reservation-api"]
    )
    def delete(self, request, tracking_code):
        # دریافت رزرو با استفاده از tracking_code
        reservation = get_object_or_404(Reservationhotel, tracking_code=tracking_code)
        
        # بررسی دسترسی کاربر
        if reservation.buyer != request.user:
            logger.warning(f"کاربر {request.user.phone_number} به رزرو {tracking_code} دسترسی ندارد.")
            return Response({"detail": "شما به این رزرو دسترسی ندارید."}, status=status.HTTP_403_FORBIDDEN)

        # بررسی وضعیت پرداخت رزرو
        if reservation.payment_status != 'unpaid':
            logger.warning(f"تلاش برای حذف برداشت برای رزرو {tracking_code} با وضعیت پرداخت {reservation.payment_status}.")
            return Response({"detail": "نمی‌توان برای رزرو پرداخت‌شده یا در حال پرداخت برداشت را حذف کرد."}, status=status.HTTP_400_BAD_REQUEST)

        # حذف برداشت
        with transaction.atomic():
            reservation.wallet_withdrawal_amount = Decimal('0')
            reservation.wallet_withdrawn = False
            reservation.save(update_fields=['wallet_withdrawal_amount', 'wallet_withdrawn'])
            logger.info(f"برداشت از کیف پول برای رزرو {tracking_code} حذف شد.")

        # پاسخ مناسب
        return Response({"detail": "برداشت از کیف پول حذف شد."}, status=status.HTTP_200_OK)