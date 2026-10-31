from collections import defaultdict
import time
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
from django.core.paginator import Paginator as DjangoPaginator, EmptyPage, PageNotAnInteger
from django.db.models import Subquery
from django.db.models import OuterRef
from asgiref.sync import async_to_sync
import jdatetime 
from itertools import combinations
from authentication.models import NaturalProfile
from bashgah_moshtarian.models import (
    CustomerClubPoint,
    DiscountActivationRecord,
    HotelDiscountCode,
    RoomDiscountCode,
    PersonalDiscountCode,
)
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
from zarvantrip import settings
from zarvantrip.pagination import FacilitiesPaginator, Paginator, RoomFacilitiesPaginator
from jdatetime import datetime as jdt
from .utils import Round
from rest_framework.generics import CreateAPIView
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND  # Import status codes
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
    OperationalError,
    DatabaseError,
    IntegrityError,
    connections,
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
    CancellationReason,
    ClosedDate,
    CommentPoint,
    CommentPointItem,
    Hotel,
    HotelTag,
    HotelTagPublic,
    ReservationApprovalDuration,
    ReservationInvoiceSettings,
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
    SEOMeta,
    SuggestedCommentItem,
    UserCancellation,
    set_skip_points_and_sms,
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
    HotelLinkSerializer,
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



#لیست اتاق ها 
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
    if not value:
        raise ValidationError('کد شناسایی نمی‌تواند خالی باشد')

    # کد ملی 10 رقمی => بررسی checksum
    if re.match(r'^\d{10}$', value):
        check_digits = int(value[9])
        total = sum(int(value[i]) * (10 - i) for i in range(9)) % 11

        if int(value[3:9]) == 0 or not ((total < 2 and check_digits == total) or (total >= 2 and check_digits == (11 - total))):
            raise ValidationError('کد ملی معتبر نیست')
        return

    # فرمت پاسپورت: 6 تا 9 حرف یا عدد
    if re.match(r'^[A-Za-z0-9]{6,9}$', value):
        return

    raise ValidationError('کد شناسایی نامعتبر است. باید کد ملی ۱۰ رقمی یا شماره پاسپورت ۶ تا ۹ کاراکتر باشد.')


class HotelRoomsView(generics.RetrieveAPIView):
    permission_classes = (AllowAny,)
    serializer_class = RoomSerializer
    queryset = Hotel.objects.all()
    lookup_field = 'slug'
    lookup_url_kwarg = 'slug'

    def calculate_discount(self, price_data, date, fixed_discount_applied=False):
        """محاسبه مقدار تخفیف و قیمت پس از تخفیف"""
        if not price_data:
            return 0, None, None, None, fixed_discount_applied
            
        discount_amount = 0
        price_after_discount = price_data.price
        discount_percentage = None
        discount_date = None

        if price_data.discount_type != 'none':
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

        # --- تعیین سطح کاربری ---
        user_level = None
        if request.user.is_authenticated:
            try:
                profile = request.user.natural_profile
                if profile.level:
                    user_level = profile.level
                    logger.info(f"User level detected: {user_level.title}")
                else:
                    logger.info("User has no level, using available prices")
            except NaturalProfile.DoesNotExist:
                logger.info("No natural profile found, using available prices")
        else:
            logger.info("Anonymous user, using available prices")

        # --- مرحله ۱: تمام اتاق‌های فعال (فقط موجودی > 0) ---
        active_rooms = hotel.rooms.filter(inventory__gt=0).distinct()

        if not active_rooms.exists():
            return Response({
                'detail': 'هیچ اتاقی برای این هتل موجود نیست.',
                'rooms': [],
                'price_calendar': [{"date": (start_date_obj + jdatetime.timedelta(days=i)).strftime('%Y/%m/%d'), "status": "close"} for i in range((end_date_obj - start_date_obj).days)]
            }, status=200)

        # --- مرحله ۲: تمام اتاق‌ها رو بگیر (بدون فیلتر قیمت) ---
        rooms_qs = active_rooms.prefetch_related('date_prices', 'services').select_related('hotel')

        date_range = [start_date_obj + jdatetime.timedelta(days=i) for i in range((end_date_obj - start_date_obj).days)]
        night_count = (end_date_obj - start_date_obj).days

        room_dict = {}
        for room in rooms_qs:
            room_services = ", ".join([s.title for s in room.services.all()]) or "خدمات ندارد"
            closed_dates = ClosedDate.objects.filter(room_date__room=room, date__range=(start_date_obj, end_date_obj))
            price_calendar = []
            fixed_discount_applied = False

            for date in date_range:
                # --- انتخاب قیمت: اولویت با سطح کاربری، سپس عمومی ---
                price_data = None
                price_data_qs = room.date_prices.filter(
                    start_date__lte=date,
                    end_date__gte=date
                )

                # اولویت اول: قیمت سطح کاربری
                if user_level:
                    level_prices = price_data_qs.filter(user_level=user_level)
                    if level_prices.exists():
                        price_data = level_prices.order_by('-id').first()
                        logger.debug(f"Using level price for {user_level.title}: {price_data.price if price_data else 'None'}")
                
                # اولویت دوم: قیمت عمومی (فقط اگر قیمت سطح کاربری پیدا نشد)
                if not price_data:
                    public_prices = price_data_qs.filter(user_level__isnull=True)
                    if public_prices.exists():
                        price_data = public_prices.order_by('-id').first()
                        logger.debug(f"Using public price: {price_data.price if price_data else 'None'}")

                closed_date = closed_dates.filter(date=date).first()
                
                # وضعیت: اگر قیمت (از هر نوع) وجود داشت و تاریخ بسته نبود، open است
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
                        "user_level": price_data.user_level.title if price_data and price_data.user_level else "عمومی",
                        "extra_capacity_price": price_data.extra_passenger_price if price_data else 0
                    } if status == "open" else None
                })

            # --- قیمت اولین روز (برای نمایش تخفیف) ---
            first_price_data = None
            first_price_data_qs = room.date_prices.filter(
                start_date__lte=start_date_obj,
                end_date__gte=start_date_obj
            )

            # اولویت اول: قیمت سطح کاربری برای روز اول
            if user_level:
                level_prices = first_price_data_qs.filter(user_level=user_level)
                if level_prices.exists():
                    first_price_data = level_prices.order_by('-id').first()
            
            # اولویت دوم: قیمت عمومی برای روز اول
            if not first_price_data:
                public_prices = first_price_data_qs.filter(user_level__isnull=True)
                if public_prices.exists():
                    first_price_data = public_prices.order_by('-id').first()

            # حتی اگر first_price_data هم None باشد، باز هم اتاق را نمایش می‌دهیم
            try:
                discount_amount, price_after_discount_first, discount_percentage_first, discount_date_first, _ = self.calculate_discount(first_price_data, start_date_obj, False)
            except ValueError as e:
                return Response({'detail': str(e)}, status=400)

            # --- محاسبه قیمت کل از price_calendar (بدون احتساب نفر اضافه) ---
            total_price = sum(
                day['price']['price'] for day in price_calendar
                if day['status'] == "open" and day['price'] and day['price']['price'] is not None
            )

            total_price_discount = sum(
                day['price']['price_after_discount']
                if day['status'] == "open" and day['price'] and day['price']['price_after_discount'] is not None
                else day['price']['price']
                if day['status'] == "open" and day['price'] and day['price']['price'] is not None
                else 0
                for day in price_calendar
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
                "image": request.build_absolute_uri(room.image.url) if room.image else None,
                "price": {
                    "total_price": total_price,
                    "total_price_discount": total_price_discount,
                    "discount_percentage": discount_percentage_first,
                    "discount_amount": discount_amount,
                    "discount_date": discount_date_first,
                    "is_fixed_discount_one_time": first_price_data.is_fixed_discount_one_time if first_price_data else False,
                    "user_level": first_price_data.user_level.title if first_price_data and first_price_data.user_level else "عمومی",
                    "extra_capacity_price": first_price_data.extra_passenger_price if first_price_data else 0
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
                # قیمت نفر اضافه را به قیمت کل اضافه نکن؛ فقط ظرفیت را چک کن
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
                    # قیمت نفر اضافه را به قیمت کل اضافه نکن؛ فقط ظرفیت را چک کن
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
        operation_summary="دریافت تصاویر شاخص و ۴ عکس صفحه داخلی هتل",
        operation_description="این API تا ۵ تصویر اصلی هتل را به صورت لیست مستقیم URLها (بدون کلید) برمی‌گرداند.",
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
            200: openapi.Response(
                description="لیست URLهای تصاویر هتل",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_STRING),
                    description="آدرس کامل تصاویر"
                )
            ),
            404: 'هتل پیدا نشد.'
        }
    )
    def retrieve(self, request, *args, **kwargs):
        hotel = self.get_object()
        serializer = self.get_serializer(hotel, context={'request': request})
        # فقط مقدار فیلد images را برمی‌گردانیم (نه کل آبجکت)
        return Response(serializer.data['images'])




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
        except serializers.ValidationError as exc:
            return Response({
                "error": "داده‌های ورودی نامعتبر هستند.",
                "details": exc.detail
            }, status=status.HTTP_400_BAD_REQUEST)
        except IntegrityError as exc:
            return Response({
                "error": "مسافر با این کد شناسایی قبلاً ثبت شده است.",
                "details": str(exc)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({
                "error": str(exc),
                "exception_type": exc.__class__.__name__,
                "trace": traceback.format_exc(limit=2)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)






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

    def get_hotel_min_price_map(self, hotels, user_level=None):
        """محاسبه کمترین قیمت برای هر هتل با فال‌بک: سطح → عمومی (بدون تخفیف ثابت)"""
        today = jdate.today()  # تاریخ شمسی
        hotel_min_price_map = {}

        for hotel in hotels:
            # مرحله ۱: اتاق‌های فعال (فقط موجودی > 0)
            active_rooms = hotel.rooms.filter(inventory__gt=0).distinct()
            if not active_rooms.exists():
                continue

            # مرحله ۲: قیمت‌های امروز
            price_qs = RoomDatePrice.objects.filter(
                room__in=active_rooms,
                start_date__lte=today,
                end_date__gte=today
            ).select_related('room', 'user_level')

            # مرحله ۳: فال‌بک هوشمند: سطح → عمومی
            if user_level:
                level_prices = price_qs.filter(user_level=user_level)
                final_prices = level_prices if level_prices.exists() else price_qs.filter(user_level__isnull=True)
            else:
                final_prices = price_qs.filter(user_level__isnull=True)

            if not final_prices.exists():
                continue

            min_price = float('inf')
            min_price_data = None

            for price in final_prices:
                original_price = price.price
                total_price = original_price

                # تخفیف درصدی (فقط اگر تاریخ انقضا >= امروز)
                if (price.discount_type == 'percentage' and
                        price.discount_date and
                        price.discount_date >= today):
                    total_price = int(original_price * (100 - price.discount_value) / 100)
                else:
                    total_price = int(original_price)

                if total_price < min_price:
                    min_price = total_price
                    min_price_data = {
                        'total_price': total_price,
                        'original_total_price': int(original_price) if price.discount_type == 'percentage' else None,
                        'discount_type': price.discount_type,
                        'discount_value': price.discount_value if price.discount_type == 'percentage' else 0,
                        'discount_date': price.discount_date.strftime('%Y/%m/%d') if price.discount_date else None,
                        'user_level': price.user_level.title if price.user_level else "عمومی",
                    }

            if min_price_data:
                hotel_min_price_map[hotel.id] = min_price_data

        return hotel_min_price_map

    def get(self, request, *args, **kwargs):
        # --- تعیین سطح کاربر ---
        user_level = None
        if request.user.is_authenticated:
            try:
                profile = request.user.natural_profile
                if profile and profile.level:
                    user_level = profile.level
            except Exception as e:
                logger.warning(f"User level fetch failed: {e}")

        # --- کوئری هتل‌ها ---
        hotels = self.get_queryset()  # یا هر کوئری که داری

        # --- محاسبه قیمت با فال‌بک ---
        hotel_min_price_map = self.get_hotel_min_price_map(hotels, user_level)

        # --- سریالایز ---
        context = {
            'hotel_min_price_map': hotel_min_price_map,
            'request': request
        }
        serializer = HotelListSerializer(hotels, many=True, context=context)
        return Response(serializer.data)





class SuggesteHotelListView(BaseHotelListView):
    @swagger_auto_schema(
        operation_summary="دریافت لیست هتل‌های پیشنهادی",
        operation_description="این API لیستی از هتل‌های پیشنهادی ویژه را بدون صفحه‌بندی باز می‌گرداند. "
                             "فقط هتل‌هایی نمایش داده می‌شوند که امروز اتاق فعال و موجودی داشته باشند. "
                             "فقط تخفیف‌های درصدی معتبر (تاریخ انقضا نگذشته) نمایش داده می‌شوند. "
                             "تخفیف‌های ثابت و هنگام خرید نادیده گرفته می‌شوند.",
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
        today = jdatetime.date.today()

        # هتل‌های پیشنهادی
        hotels = Hotel.objects.filter(status='published', is_special_offer=True).select_related('city', 'type').distinct()
        if not hotels.exists():
            return Response([])

        # تعیین سطح کاربری
        user_level = None  # عمومی = None
        if request.user.is_authenticated:
            try:
                profile = request.user.natural_profile
                if profile and profile.level:
                    user_level = profile.level
            except Exception as e:
                logger.warning(f"User level fetch failed in SuggesteHotelListView: {e}")

        hotel_min_price_map = {}
        valid_hotels = []

        for hotel in hotels:
            # مرحله ۱: اتاق‌های فعال فقط بر اساس موجودی (بدون فیلتر date_prices)
            active_rooms = hotel.rooms.filter(inventory__gt=0).distinct()

            if not active_rooms.exists():
                continue

            # مرحله ۲: قیمت‌های امروز (بدون فیلتر سطح)
            price_qs = RoomDatePrice.objects.filter(
                room__in=active_rooms,
                start_date__lte=today,
                end_date__gte=today
            )

            # مرحله ۳: انتخاب قیمت بر اساس سطح کاربر (اولویت با سطح کاربری، سپس عمومی)
            final_prices = None
            if user_level:
                level_prices = price_qs.filter(user_level=user_level)
                if level_prices.exists():
                    final_prices = level_prices
                    logger.debug(f"Using level prices for user level: {user_level.title}")
            
            # اگر قیمت سطح کاربری پیدا نشد، از قیمت عمومی استفاده کن
            if not final_prices:
                public_prices = price_qs.filter(user_level__isnull=True)
                if public_prices.exists():
                    final_prices = public_prices
                    logger.debug("Using public prices as fallback")
                else:
                    # اگر هیچ قیمتی (نه سطح کاربری، نه عمومی) پیدا نشد، باز هم هتل را نمایش بده
                    # اما با کمترین قیمت از بین تمام قیمت‌های موجود
                    all_prices = price_qs
                    if all_prices.exists():
                        final_prices = all_prices
                        logger.debug("Using any available prices (no level or public prices found)")
                    else:
                        # اگر اصلاً هیچ قیمتی برای امروز نبود، هتل را حذف نکن
                        # بلکه با وضعیت بدون قیمت نمایش بده
                        logger.debug(f"Hotel {hotel.id} has no prices for today, but keeping it in list")
                        hotel_min_price_map[hotel.id] = {
                            'total_price': None,
                            'original_total_price': None,
                            'discount_type': 'none',
                            'discount_value': 0,
                            'discount_date': None,
                            'user_level': "بدون قیمت",
                            'has_price': False
                        }
                        valid_hotels.append(hotel)
                        continue

            # مرحله ۴: پیدا کردن کمترین قیمت
            min_price = float('inf')
            min_price_data = None

            for price_data in final_prices:
                base_price = price_data.price

                if (price_data.discount_type == 'percentage' and
                        price_data.discount_date and
                        price_data.discount_date >= today):
                    discounted_price = int(base_price * (100 - price_data.discount_value) / 100)
                    if discounted_price < min_price:
                        min_price = discounted_price
                        min_price_data = {
                            'total_price': discounted_price,
                            'original_total_price': base_price,
                            'discount_type': 'percentage',
                            'discount_value': price_data.discount_value,
                            'discount_date': price_data.discount_date.strftime('%Y/%m/%d'),
                            'user_level': price_data.user_level.title if price_data.user_level else "عمومی",
                            'has_price': True
                        }
                else:
                    if base_price < min_price:
                        min_price = base_price
                        min_price_data = {
                            'total_price': base_price,
                            'original_total_price': None,
                            'discount_type': 'none',
                            'discount_value': 0,
                            'discount_date': None,
                            'user_level': price_data.user_level.title if price_data.user_level else "عمومی",
                            'has_price': True
                        }

            if min_price_data:
                hotel_min_price_map[hotel.id] = min_price_data
                valid_hotels.append(hotel)

        # مرحله ۵: سریالایز
        context = {'hotel_min_price_map': hotel_min_price_map, 'request': request}
        special_offers_data = []

        for hotel in valid_hotels:
            serialized = HotelListSerializer(hotel, context=context).data
            serialized['average_score'] = self.get_average_score(hotel)
            
            # اضافه کردن اطلاعات قیمت به صورت مستقیم
            price_info = hotel_min_price_map.get(hotel.id, {})
            serialized['price_info'] = price_info
            
            special_offers_data.append(serialized)

        return Response(special_offers_data)
    
    
    

class AmazingHotelsListView(BaseHotelListView):
    @swagger_auto_schema(
        operation_summary="دریافت لیست هتل‌های فروش شگفت‌انگیز",
        operation_description="این API لیستی از هتل‌های فروش شگفت‌انگیز را بدون صفحه‌بندی باز می‌گرداند. "
                             "فقط هتل‌هایی نمایش داده می‌شوند که امروز اتاق فعال و موجودی داشته باشند. "
                             "فقط تخفیف‌های درصدی معتبر (تاریخ انقضا نگذشته) نمایش داده می‌شوند. "
                             "تخفیف‌های ثابت و هنگام خرید نادیده گرفته می‌شوند.",
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
        today = jdatetime.date.today()

        # هتل‌های فروش شگفت‌انگیز
        hotels = Hotel.objects.filter(status='published', is_flash_sale=True).select_related('city', 'type').distinct()
        if not hotels.exists():
            return Response([])

        # تعیین سطح کاربری
        user_level = None  # عمومی = None
        if request.user.is_authenticated:
            try:
                profile = request.user.natural_profile
                if profile and profile.level:
                    user_level = profile.level
            except Exception as e:
                logger.warning(f"User level fetch failed in AmazingHotelsListView: {e}")

        hotel_min_price_map = {}
        valid_hotels = []

        for hotel in hotels:
            # مرحله ۱: اتاق‌های فعال فقط بر اساس موجودی (بدون فیلتر date_prices)
            active_rooms = hotel.rooms.filter(inventory__gt=0).distinct()

            if not active_rooms.exists():
                continue

            # مرحله ۲: قیمت‌های امروز (بدون فیلتر سطح)
            price_qs = RoomDatePrice.objects.filter(
                room__in=active_rooms,
                start_date__lte=today,
                end_date__gte=today
            )

            # مرحله ۳: انتخاب قیمت بر اساس سطح کاربر (اولویت با سطح کاربری، سپس عمومی)
            final_prices = None
            if user_level:
                level_prices = price_qs.filter(user_level=user_level)
                if level_prices.exists():
                    final_prices = level_prices
                    logger.debug(f"Using level prices for user level: {user_level.title}")
            
            # اگر قیمت سطح کاربری پیدا نشد، از قیمت عمومی استفاده کن
            if not final_prices:
                public_prices = price_qs.filter(user_level__isnull=True)
                if public_prices.exists():
                    final_prices = public_prices
                    logger.debug("Using public prices as fallback")
                else:
                    # اگر هیچ قیمتی (نه سطح کاربری، نه عمومی) پیدا نشد، باز هم هتل را نمایش بده
                    # اما با کمترین قیمت از بین تمام قیمت‌های موجود
                    all_prices = price_qs
                    if all_prices.exists():
                        final_prices = all_prices
                        logger.debug("Using any available prices (no level or public prices found)")
                    else:
                        # اگر اصلاً هیچ قیمتی برای امروز نبود، هتل را حذف نکن
                        # بلکه با وضعیت بدون قیمت نمایش بده
                        logger.debug(f"Hotel {hotel.id} has no prices for today, but keeping it in list")
                        hotel_min_price_map[hotel.id] = {
                            'total_price': None,
                            'original_total_price': None,
                            'discount_type': 'none',
                            'discount_value': 0,
                            'discount_date': None,
                            'user_level': "بدون قیمت",
                            'has_price': False
                        }
                        valid_hotels.append(hotel)
                        continue

            # مرحله ۴: پیدا کردن کمترین قیمت
            min_price = float('inf')
            min_price_data = None

            for price_data in final_prices:
                base_price = price_data.price

                if (price_data.discount_type == 'percentage' and
                        price_data.discount_date and
                        price_data.discount_date >= today):
                    discounted_price = int(base_price * (100 - price_data.discount_value) / 100)
                    if discounted_price < min_price:
                        min_price = discounted_price
                        min_price_data = {
                            'total_price': discounted_price,
                            'original_total_price': base_price,
                            'discount_type': 'percentage',
                            'discount_value': price_data.discount_value,
                            'discount_date': price_data.discount_date.strftime('%Y/%m/%d'),
                            'user_level': price_data.user_level.title if price_data.user_level else "عمومی",
                            'has_price': True
                        }
                else:
                    if base_price < min_price:
                        min_price = base_price
                        min_price_data = {
                            'total_price': base_price,
                            'original_total_price': None,
                            'discount_type': 'none',
                            'discount_value': 0,
                            'discount_date': None,
                            'user_level': price_data.user_level.title if price_data.user_level else "عمومی",
                            'has_price': True
                        }

            if min_price_data:
                hotel_min_price_map[hotel.id] = min_price_data
                valid_hotels.append(hotel)

        # مرحله ۵: سریالایز
        context = {'hotel_min_price_map': hotel_min_price_map, 'request': request}
        flash_sales_data = []

        for hotel in valid_hotels:
            serialized = HotelListSerializer(hotel, context=context).data
            serialized['average_score'] = self.get_average_score(hotel)
            
            # اضافه کردن اطلاعات قیمت به صورت مستقیم
            price_info = hotel_min_price_map.get(hotel.id, {})
            serialized['price_info'] = price_info
            
            flash_sales_data.append(serialized)

        return Response(flash_sales_data)
    
    


class BestSellersListView(BaseHotelListView):
    @swagger_auto_schema(
        operation_summary="دریافت لیست هتل‌های پرفروش‌ترین",
        operation_description="این API لیستی از هتل‌های پرفروش‌ترین را بدون صفحه‌بندی باز می‌گرداند. "
                             "فقط هتل‌هایی نمایش داده می‌شوند که امروز اتاق فعال و موجودی داشته باشند. "
                             "فقط تخفیف‌های درصدی معتبر (تاریخ انقضا نگذشته) نمایش داده می‌شوند. "
                             "تخفیف‌های ثابت و هنگام خرید نادیده گرفته می‌شوند.",
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
        today = jdatetime.date.today()

        # هتل‌های پرفروش
        hotels = Hotel.objects.filter(status='published', is_best_seller=True).select_related('city', 'type').distinct()
        if not hotels.exists():
            return Response([])

        # تعیین سطح کاربری
        user_level = None  # عمومی = None
        if request.user.is_authenticated:
            try:
                profile = request.user.natural_profile
                if profile and profile.level:
                    user_level = profile.level
            except Exception as e:
                logger.warning(f"User level fetch failed in BestSellersListView: {e}")

        hotel_min_price_map = {}
        valid_hotels = []

        for hotel in hotels:
            # مرحله ۱: اتاق‌های فعال فقط بر اساس موجودی (بدون فیلتر date_prices)
            active_rooms = hotel.rooms.filter(inventory__gt=0).distinct()

            if not active_rooms.exists():
                continue

            # مرحله ۲: قیمت‌های امروز (بدون فیلتر سطح)
            price_qs = RoomDatePrice.objects.filter(
                room__in=active_rooms,
                start_date__lte=today,
                end_date__gte=today
            )

            # مرحله ۳: انتخاب قیمت بر اساس سطح کاربر (اولویت با سطح کاربری، سپس عمومی)
            final_prices = None
            if user_level:
                level_prices = price_qs.filter(user_level=user_level)
                if level_prices.exists():
                    final_prices = level_prices
                    logger.debug(f"Using level prices for user level: {user_level.title}")
            
            # اگر قیمت سطح کاربری پیدا نشد، از قیمت عمومی استفاده کن
            if not final_prices:
                public_prices = price_qs.filter(user_level__isnull=True)
                if public_prices.exists():
                    final_prices = public_prices
                    logger.debug("Using public prices as fallback")
                else:
                    # اگر هیچ قیمتی (نه سطح کاربری، نه عمومی) پیدا نشد، باز هم هتل را نمایش بده
                    # اما با کمترین قیمت از بین تمام قیمت‌های موجود
                    all_prices = price_qs
                    if all_prices.exists():
                        final_prices = all_prices
                        logger.debug("Using any available prices (no level or public prices found)")
                    else:
                        # اگر اصلاً هیچ قیمتی برای امروز نبود، هتل را حذف نکن
                        # بلکه با وضعیت بدون قیمت نمایش بده
                        logger.debug(f"Hotel {hotel.id} has no prices for today, but keeping it in list")
                        hotel_min_price_map[hotel.id] = {
                            'total_price': None,
                            'original_total_price': None,
                            'discount_type': 'none',
                            'discount_value': 0,
                            'discount_date': None,
                            'user_level': "بدون قیمت",
                            'has_price': False
                        }
                        valid_hotels.append(hotel)
                        continue

            # مرحله ۴: پیدا کردن کمترین قیمت
            min_price = float('inf')
            min_price_data = None

            for price_data in final_prices:
                base_price = price_data.price

                if (price_data.discount_type == 'percentage' and
                        price_data.discount_date and
                        price_data.discount_date >= today):
                    discounted_price = int(base_price * (100 - price_data.discount_value) / 100)
                    if discounted_price < min_price:
                        min_price = discounted_price
                        min_price_data = {
                            'total_price': discounted_price,
                            'original_total_price': base_price,
                            'discount_type': 'percentage',
                            'discount_value': price_data.discount_value,
                            'discount_date': price_data.discount_date.strftime('%Y/%m/%d'),
                            'user_level': price_data.user_level.title if price_data.user_level else "عمومی",
                            'has_price': True
                        }
                else:
                    if base_price < min_price:
                        min_price = base_price
                        min_price_data = {
                            'total_price': base_price,
                            'original_total_price': None,
                            'discount_type': 'none',
                            'discount_value': 0,
                            'discount_date': None,
                            'user_level': price_data.user_level.title if price_data.user_level else "عمومی",
                            'has_price': True
                        }

            if min_price_data:
                hotel_min_price_map[hotel.id] = min_price_data
                valid_hotels.append(hotel)

        # مرحله ۵: سریالایز
        context = {'hotel_min_price_map': hotel_min_price_map, 'request': request}
        best_sellers_data = []

        for hotel in valid_hotels:
            serialized = HotelListSerializer(hotel, context=context).data
            serialized['average_score'] = self.get_average_score(hotel)
            
            # اضافه کردن اطلاعات قیمت به صورت مستقیم
            price_info = hotel_min_price_map.get(hotel.id, {})
            serialized['price_info'] = price_info
            
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

    def calculate_discount_timer(self, discount_date):
        """محاسبه زمان باقی‌مانده تا انقضای تخفیف به ثانیه"""
        if not discount_date:
            return 0
        
        today_jd = jdatetime.date.today()
        if discount_date < today_jd:
            return 0  # تخفیف منقضی شده
        
        # ترکیب تاریخ با پایان روز (23:59:59)
        discount_datetime = jdatetime.datetime.combine(
            discount_date, 
            jdatetime.time(23, 59, 59)
        )
        
        # تبدیل به تاریخ میلادی
        discount_datetime_gregorian = discount_datetime.togregorian()
        
        # اطمینان از اینکه discount_datetime_gregorian آگاه از تایم‌زون باشد
        if timezone.is_naive(discount_datetime_gregorian):
            discount_datetime_gregorian = timezone.make_aware(discount_datetime_gregorian)
        
        # محاسبه زمان باقی‌مانده
        now = timezone.now()
        time_remaining = discount_datetime_gregorian - now
        
        return max(int(time_remaining.total_seconds()), 0)

    def get_hotel_min_price_map(self, hotels, user_level=None):
        """محاسبه کمترین قیمت و اطلاعات تخفیف برای هر هتل با در نظر گرفتن سطح کاربری"""
        today = jdatetime.date.today()
        hotel_min_price_map = {}

        for hotel in hotels:
            # فقط اتاق‌های با موجودی > 0
            active_rooms = hotel.rooms.filter(inventory__gt=0).distinct()
            
            if not active_rooms.exists():
                continue  # هتل بدون اتاق فعال را نمایش نده

            min_price = float('inf')
            min_price_data = None

            for room in active_rooms:
                # دریافت تمام قیمت‌های امروز برای این اتاق
                price_qs = RoomDatePrice.objects.filter(
                    room=room,
                    start_date__lte=today,
                    end_date__gte=today
                ).select_related('room', 'user_level')

                # انتخاب قیمت بر اساس سطح کاربری (اولویت با سطح کاربری، سپس عمومی)
                final_prices = None
                
                # اگر کاربر سطح دارد، اول قیمت سطح کاربری را بررسی کن
                if user_level:
                    level_prices = price_qs.filter(user_level=user_level)
                    if level_prices.exists():
                        final_prices = level_prices
                        logger.debug(f"Using level prices for user level: {user_level.title} in hotel {hotel.id}")
                
                # اگر قیمت سطح کاربری پیدا نشد یا کاربر سطح ندارد، قیمت عمومی را بررسی کن
                if not final_prices:
                    public_prices = price_qs.filter(user_level__isnull=True)
                    if public_prices.exists():
                        final_prices = public_prices
                        logger.debug(f"Using public prices for hotel {hotel.id}")
                    else:
                        # اگر هیچ قیمت عمومی نبود، از قیمت‌های سایر سطوح استفاده نکن
                        # چون کاربر حق دسترسی به آن سطوح را ندارد
                        logger.debug(f"No public prices found for hotel {hotel.id}, skipping")
                        continue

                # اگر هنوز final_prices مشخص نشده، یعنی هیچ قیمتی برای کاربر موجود نیست
                if not final_prices:
                    continue

                for price_data in final_prices:
                    base_price = price_data.price
                    
                    # اگر قیمت صفر یا منفی باشد، نادیده بگیر
                    if base_price <= 0:
                        continue

                    # محاسبه قیمت نهایی با تخفیف
                    final_price = base_price
                    discount_percentage = 0
                    timer_seconds = 0

                    if (price_data.discount_type == 'percentage' and
                            price_data.discount_date and
                            price_data.discount_date >= today):
                        # تخفیف درصدی معتبر
                        discount_percentage = price_data.discount_value
                        final_price = int(base_price * (100 - discount_percentage) / 100)
                        timer_seconds = self.calculate_discount_timer(price_data.discount_date)
                        
                    elif price_data.discount_type == 'fixed':
                        # تخفیف ثابت
                        final_price = max(base_price - price_data.discount_value, 0)
                        if base_price > 0:
                            discount_percentage = int((price_data.discount_value / base_price) * 100)
                    
                    # اگر قیمت نهایی صفر یا منفی شد، نمایش نده
                    if final_price <= 0:
                        continue

                    if final_price < min_price:
                        min_price = final_price
                        min_price_data = {
                            'total_price': final_price,
                            'original_total_price': base_price,
                            'discount_type': price_data.discount_type,
                            'discount_value': price_data.discount_value,
                            'discount_date': price_data.discount_date.strftime('%Y/%m/%d') if price_data.discount_date else None,
                            'discount_percentage': discount_percentage,
                            'timer_seconds': timer_seconds,
                            'user_level': price_data.user_level.title if price_data.user_level else "عمومی",
                            'has_price': True,
                            'is_accessible': True  # کاربر به این قیمت دسترسی دارد
                        }

            # فقط هتل‌هایی که قیمت معتبر و قابل دسترسی دارند را نمایش بده
            if min_price_data and min_price_data['total_price'] > 0:
                hotel_min_price_map[hotel.id] = min_price_data
            else:
                logger.debug(f"Hotel {hotel.id} has no accessible prices for user level: {user_level.title if user_level else 'public'}")

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
                            'timer_seconds': openapi.Schema(type=openapi.TYPE_INTEGER, description="زمان باقی‌مانده تا انقضای تخفیف به ثانیه"),
                            'is_accessible': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="آیا کاربر به این قیمت دسترسی دارد"),
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
            
            # تعیین سطح کاربری
            user_level = None
            if request.user.is_authenticated:
                try:
                    profile = request.user.natural_profile
                    if profile and profile.level:
                        user_level = profile.level
                        logger.info(f"User level detected: {user_level.title}")
                    else:
                        logger.info("User has no level, using public prices")
                except NaturalProfile.DoesNotExist:
                    logger.info("No natural profile found, using public prices")
                except Exception as e:
                    logger.warning(f"User level fetch failed in HomeHotelByHotelSlugView: {e}")
            else:
                logger.info("Anonymous user, using public prices")

            # دریافت هتل‌های همان شهر (به جز هتل فعلی)
            hotels = Hotel.objects.filter(city=city).exclude(slug=hotel_slug).select_related('city', 'type').distinct()
            
            # محاسبه قیمت‌ها با در نظر گرفتن سطح کاربری
            hotel_min_price_map = self.get_hotel_min_price_map(hotels, user_level)
            context = {'hotel_min_price_map': hotel_min_price_map, 'request': request}

            # فقط هتل‌هایی که قیمت معتبر دارند را سریالایز کن
            valid_hotels = []
            for hotel in hotels:
                if hotel.id in hotel_min_price_map:
                    serialized = HotelListSerializer(hotel, context=context).data
                    serialized['average_score'] = self.get_average_score(hotel)
                    
                    # اضافه کردن اطلاعات قیمت
                    price_info = hotel_min_price_map[hotel.id]
                    serialized['price_info'] = price_info
                    serialized['timer_seconds'] = price_info.get('timer_seconds', 0)
                    serialized['is_accessible'] = price_info.get('is_accessible', True)
                    
                    valid_hotels.append(serialized)

            logger.info(f"Returning {len(valid_hotels)} accessible hotels for user level: {user_level.title if user_level else 'public'}")
            return Response(valid_hotels)
        except Hotel.DoesNotExist:
            return Response({'error': 'Hotel not found'}, status=404)
        except Exception as e:
            logger.error(f"Unexpected error in HomeHotelByHotelSlugView: {str(e)}")
            return Response({'error': 'Internal server error'}, status=500)
        
        

#ای پی ای لیست هتل برای سرچ صفحه اول 
class HotelSearchAPI(ListCreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = HotelSearchSerializer

    def get_queryset(self):
        query = self.request.query_params.get('query', '').lower()
        if query:
            # وقتی کوئری وجود دارد، هم هتل‌ها و هم شهرها جستجو می‌شوند
            hotels = Hotel.objects.filter(name__icontains=query, status='published').select_related('city__province')
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
                "hotels_number": city.hotels.filter(status='published').count()
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
        operation_description="این API گالری‌های تصویری مربوط به یک هتل را بر اساس slug بازمی‌گرداند. هر گالری شامل id، عنوان و لیست مستقیم URL تصاویر است.",
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
            200: openapi.Response(
                description="گالری‌های هتل",
                schema=HotelGallerySerializer(many=True)
            ),
            404: 'هتل پیدا نشد.'
        }
    )
    def retrieve(self, request, *args, **kwargs):
        hotel = self.get_object()
        galleries = hotel.galleries.all()
        serializer = self.get_serializer(galleries, many=True, context={'request': request})
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

    def get_user_level(self, request):
        """تعیین سطح کاربری مانند HotelRoomsView"""
        user_level = None
        if request.user.is_authenticated:
            try:
                profile = request.user.natural_profile
                if profile.level:
                    user_level = profile.level
            except NaturalProfile.DoesNotExist:
                pass
        return user_level

    def get_price_data_for_date(self, room, date, user_level):
        """انتخاب قیمت بر اساس سطح کاربری مانند HotelRoomsView"""
        price_data_qs = room.date_prices.filter(
            start_date__lte=date,
            end_date__gte=date
        )

        # اولویت اول: قیمت سطح کاربری
        if user_level:
            level_prices = price_data_qs.filter(user_level=user_level)
            if level_prices.exists():
                return level_prices.order_by('-id').first()
        
        # اولویت دوم: قیمت عمومی
        public_prices = price_data_qs.filter(user_level__isnull=True)
        if public_prices.exists():
            return public_prices.order_by('-id').first()
        
        return None

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

    def get_room_data(self, hotel, start_date_obj, end_date_obj, passengers_list, user_level=None):
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
                # استفاده از منطق انتخاب قیمت بر اساس سطح کاربری
                price_data = self.get_price_data_for_date(room, date, user_level)
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
                        "user_level": price_data.user_level.title if price_data and price_data.user_level else "عمومی",
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

            # قیمت اولین روز با در نظر گرفتن سطح کاربری
            first_price_data = self.get_price_data_for_date(room, start_date_obj, user_level)
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
                    "user_level": first_price_data.user_level.title if first_price_data and first_price_data.user_level else "عمومی",
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
                'user_level': min_room['price']['user_level'],
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
                    'user_level': min_room['price']['user_level'],
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
                        pack_user_levels = set()
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
                            pack_user_levels.add(room['price']['user_level'])
                        packs.append({
                            "total_price": pack_total_price,
                            "original_total_price": pack_total_original,
                            "discount_percentage": list(pack_discount_percentages)[0] if len(pack_discount_percentages) == 1 else None,
                            "discount_date": list(pack_discount_dates)[0] if len(pack_discount_dates) == 1 else None,
                            "user_level": list(pack_user_levels)[0] if len(pack_user_levels) == 1 else "مختلط",
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
                    'user_level': min_pack['user_level'],
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

        # تعیین سطح کاربری
        user_level = self.get_user_level(request)

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

        hotels_qs = Hotel.objects.filter(status='published').select_related('city__province', 'type').prefetch_related(
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
            # ارسال user_level به متد get_room_data
            min_price_data = self.get_room_data(hotel, start_date_obj, end_date_obj, passenger_values, user_level)
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
                        'user_level': user_level.title if user_level else "عمومی",
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
    swagger_fake_view = True

    def get_user_level(self, request):
        """تعیین سطح کاربری"""
        user_level = None
        if request.user.is_authenticated:
            try:
                profile = request.user.natural_profile
                if profile.level:
                    user_level = profile.level
            except NaturalProfile.DoesNotExist:
                pass
        return user_level

    def get_price_data_for_date(self, room, date, user_level):
        """انتخاب قیمت بر اساس سطح کاربری"""
        price_data_qs = room.date_prices.filter(
            start_date__lte=date,
            end_date__gte=date
        )

        # اولویت اول: قیمت سطح کاربری
        if user_level:
            level_prices = price_data_qs.filter(user_level=user_level)
            if level_prices.exists():
                return level_prices.order_by('-id').first()
        
        # اولویت دوم: قیمت عمومی
        public_prices = price_data_qs.filter(user_level__isnull=True)
        if public_prices.exists():
            return public_prices.order_by('-id').first()
        
        return None

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

    def get_room_data(self, hotel, start_date_obj, end_date_obj, passengers_list, user_level=None):
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
                # استفاده از منطق انتخاب قیمت بر اساس سطح کاربری
                price_data = self.get_price_data_for_date(room, date, user_level)
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
                        "user_level": price_data.user_level.title if price_data and price_data.user_level else "عمومی",
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

            # قیمت اولین روز با در نظر گرفتن سطح کاربری
            first_price_data = self.get_price_data_for_date(room, start_date_obj, user_level)
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
                    "user_level": first_price_data.user_level.title if first_price_data and first_price_data.user_level else "عمومی",
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

        # تعیین سطح کاربری
        user_level = self.get_user_level(request)

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
            # ارسال user_level به متد get_room_data
            min_price_data = self.get_room_data(hotel, start_date, end_date, passenger_list, user_level)
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
        
        
        
        
        
# ==============================================================================
# API ایجاد رزرو موقت (پرسرعت، دوگانه: محلی + اسنپ‌تریپ - پاسخ زیر ۱ ثانیه)
# ==============================================================================
import threading

logger = logging.getLogger(__name__)


def _send_telegram_notification_background(tracking_code, buyer_name, hotel_name, capacity_status, rooms_text, final_price):
    """ارسال اعلان تلگرام در پس‌زمینه بدون مسدودسازی و معطل کردن مسافر"""
    try:
        from hotel_bot.bot import send_reservation_notification
        async_to_sync(send_reservation_notification)(
            tracking_code,
            buyer_name,
            hotel_name,
            capacity_status,
            rooms_text,
            final_price
        )
    except Exception:
        pass


class ReservationCreateAPIView(generics.CreateAPIView):
    """
    ایجاد رزرو موقت با حداکثر سرعت:
    - برای هتل‌های محلی: ظرفیت دیتابیس کسر شده و بدون دخالت اسنپ ثبت می‌شود.
    - برای هتل‌های اسنپ‌تریپ: پیش‌رزرو ثبت و اتاق‌های آنی ۱۵ دقیقه قفل (Lock) می‌شوند.
    - موجودی زنده کیف پول کاربر نیز از طریق وب‌سوکت به فرانت ارسال می‌شود.
    """
    serializer_class = ReservationCreateSerializer
    permission_classes = [AllowAny]
    authentication_classes = []  

    @swagger_auto_schema(
        operation_summary="ایجاد رزرو موقت",
        operation_description="""
        ایجاد رزرو موقت برای کاربر جاری و قفل موقت ظرفیت اتاق‌ها.
        - اگر اتاق آنی (Instant) باشد: capacity_status = confirmed و تایمر ۱۵ دقیقه پرداخت روشن می‌شود.
        - اگر اتاق نیازمند تایید باشد: capacity_status = pending (در انتظار تایید ادمین یا هتل اسنپ).
        """,
        tags=["reservation-api"],
        request_body=ReservationCreateSerializer,
        responses={
            200: openapi.Response(
                description="رزرو با موفقیت ایجاد شد.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'tracking_code': openapi.Schema(type=openapi.TYPE_STRING, example="sfa1234567890"),
                        'capacity_status': openapi.Schema(type=openapi.TYPE_STRING, example="confirmed"),
                        'wallet_balance': openapi.Schema(type=openapi.TYPE_INTEGER, example=1500000),
                    }
                )
            ),
            400: "درخواست نامعتبر یا عدم موجودی ظرفیت کافی",
        }
    )
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        from reservation.snapptrip_service import create_snapptrip_booking

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # تولید کد پیگیری رزرو یکتا
        tracking_code = 'sfa' + ''.join(str(random.randint(0, 9)) for _ in range(10))

        # تبدیل تاریخ شمسی به شیء jdatetime.date
        def parse_jdate(value):
            if isinstance(value, str):
                try:
                    return jdatetime.date.fromisoformat(value)
                except ValueError:
                    return jdatetime.date.fromgregorian(date=gdate.fromisoformat(value))
            elif isinstance(value, dict):
                year, month, day = int(value["year"]), int(value["month"]), int(value["day"])
                if value.get("calendar") == "gregorian":
                    return jdatetime.date.fromgregorian(date=gdate(year, month, day))
                return jdatetime.date(year, month, day)
            elif isinstance(value, gdate):
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

        # استخراج اطلاعات رزروکننده از حساب کاربری شخص واردشده (ایمن در برابر کاربر مهمان)
        is_logged_in = bool(request.user and request.user.is_authenticated)
        current_buyer = request.user if is_logged_in else None
        profile = getattr(current_buyer, 'natural_profile', None) if is_logged_in else None
        user_phone = str(getattr(current_buyer, 'phone_number', '') or '').strip() if is_logged_in else ''

        reserver_data = {
            'reserver_first_name': (profile.first_name if profile else '') or '',
            'reserver_last_name': (profile.last_name if profile else '') or '',
            'reserver_national_code': (profile.national_code if profile else '') or '',
            'reserver_phone_number': user_phone
        }

        # ذخیره خریدار
        reservation = Reservationhotel.objects.create(
            tracking_code=tracking_code,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            buyer=current_buyer,
            capacity_status='pending',
            payment_status='pending',
            **reserver_data
        )

        hotel_id = data.get('hotel_id')
        room_id = data.get('room_id')
        quantity = int(data.get('room_number', 1))
        nights = reservation.nights_count or 1

        # قفل رکورد اتاق در دیتابیس برای جلوگیری از رزرو همزمان (Race Condition)
        try:
            room = Room.objects.select_for_update().get(id=room_id, hotel_id=hotel_id)
        except Room.DoesNotExist:
            raise ValidationError("اتاق یا هتل مورد نظر یافت نشد.")

        # بررسی ظرفیت داخلی: آیا اتاق آنی است یا نیازمند تایید ادمین؟
        auto_approval = False
        if room.auto_approved_count >= quantity:
            auto_approval = True
        elif room.count >= quantity:
            auto_approval = False
        else:
            raise ValidationError(f"ظرفیت کافی برای اتاق «{room.title}» در دیتابیس موجود نیست.")

        # =========================================================================
        # تفکیک دقیق: اتاق اسنپ‌تریپ در برابر اتاق محلی
        # =========================================================================
        if room.is_snapptrip and room.snapptrip_room_id and room.hotel.snapptrip_hotel_id:
            # ارسال مستقیم پیش‌رزرو به وب‌سرویس اسنپ
            success_snapp, snapp_code, is_instant_snapp, snapp_stat = create_snapptrip_booking(
                reservation=reservation,
                room_snapp_id=room.snapptrip_room_id,
                hotel_snapp_id=room.hotel.snapptrip_hotel_id,
                quantity=quantity
            )
            if not success_snapp:
                raise ValidationError(f"خطای وب‌سرویس اسنپ‌تریپ: {snapp_stat}")

            reservation.is_snapptrip_reservation = True
            reservation.snapp_reservation_code = snapp_code
            reservation.snapp_status = snapp_stat
            auto_approval = is_instant_snapp
        else:
            # اتاق مربوط به هتل‌های خودتان است؛ بدون دخالت اسنپ پردازش می‌شود
            reservation.is_snapptrip_reservation = False
            reservation.snapp_reservation_code = None
            reservation.snapp_status = None

        # کسر ظرفیت موقت اتاق در دیتابیس
        room.adjust_inventory_for_reservation(quantity, auto_approval)

        # استخراج پرسرعت قیمت شب‌های اقامت در یک کوئری بهینه (حذف حلقه N+1)
        check_in_g = check_in_date.togregorian()
        check_out_g = check_out_date.togregorian()
        user_level = getattr(profile, 'level', None) if profile else None

        date_prices_qs = RoomDatePrice.objects.filter(
            room=room,
            start_date__lte=check_out_g,
            end_date__gte=check_in_g
        )
        if user_level:
            level_p = date_prices_qs.filter(user_level=user_level).first()
            price_obj = level_p or date_prices_qs.filter(user_level__isnull=True).first()
        else:
            price_obj = date_prices_qs.filter(user_level__isnull=True).first() or date_prices_qs.first()

        unit_night_price = Decimal(price_obj.price if price_obj else 0)
        single_room_subtotal = unit_night_price * nights

        # ثبت رکوردهای ReservationRoom
        reservation_rooms = []
        for _ in range(quantity):
            res_room = ReservationRoom(
                reservation=reservation,
                room=room,
                quantity=1,
                was_auto_approved=auto_approval,
                price_per_night=unit_night_price,
                subtotal=single_room_subtotal,
                primary_passengers_count=room.room_capacity,
                extra_passengers_count=room.extra_capacity,
            )
            reservation_rooms.append(res_room)
        ReservationRoom.objects.bulk_create(reservation_rooms)

        # وضعیت نهایی ظرفیت
        reservation.capacity_status = 'confirmed' if auto_approval else 'pending'

        # محاسبه کل مبالغ صورت‌حساب
        (total_price, total_extra, discount_amount, half_in, half_out,
         total_half, code_discount, final_price, room_fixed) = reservation.calculate_total_price()

        reservation.total_price = total_price
        reservation.final_price = final_price
        reservation.room_fixed_discount = room_fixed
        reservation.discount = code_discount
        reservation.half_day_in_charge = half_in
        reservation.half_day_out_charge = half_out
        reservation.total_half_day_charge = total_half
        reservation.total_extra_passenger_charge = total_extra
        reservation._skip_price_calculation_on_save = True
        reservation.save()

        # خواندن موجودی زنده کیف پول مسافر (فقط اگر کاربر لاگین بود)
        user_balance = int(current_buyer.wallet.balance) if (current_buyer and hasattr(current_buyer, 'wallet') and current_buyer.wallet) else 0

        # ارسال رویداد وب‌سوکت همراه با تایمر و موجودی کیف پول کاربر
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"reservation_{reservation.tracking_code}",
            {
                "type": "status_update",
                "message": {
                    "capacity_status": reservation.capacity_status,
                    "payment_status": reservation.payment_status,
                    "snapp_status": reservation.snapp_status,
                    "final_price": int(reservation.final_price),
                    "wallet_balance": user_balance,
                    "timer": 900 if reservation.capacity_status == 'confirmed' else None
                },
            },
        )

        # ارسال تلگرام در پس‌زمینه (Thread مجزا) تا کاربر به هیچ‌وجه معطل فیلترینگ تلگرام نشود
        buyer_name = f"{reserver_data.get('reserver_first_name', '')} {reserver_data.get('reserver_last_name', '')}".strip() or user_phone or "کاربر مهمان"
        hotel_name = room.hotel.name if room.hotel else 'نامشخص'
        rooms_text = f"{room.title} (تعداد: {quantity})"

        threading.Thread(
            target=_send_telegram_notification_background,
            args=(
                reservation.tracking_code,
                buyer_name,
                hotel_name,
                reservation.capacity_status,
                rooms_text,
                reservation.final_price or 0
            ),
            daemon=True
        ).start()

        # زمان‌بندی لغو خودکار در صورت عدم پرداخت پس از ۱۵ دقیقه
        try:
            from reservation.tasks import auto_cancel_unpaid_reservation
            auto_cancel_unpaid_reservation.apply_async(args=[reservation.id], countdown=900)
        except Exception as e:
            logger.error(f"خطا در ایجاد تسک انقضای خودکار رزرو: {e}")

        logger.info(f"✅ رزرو {tracking_code} با موفقیت ثبت شد (وضعیت: {reservation.capacity_status})")

        return Response({
            "tracking_code": tracking_code,
            "capacity_status": reservation.capacity_status,
            "wallet_balance": user_balance,
            "final_price": int(reservation.final_price)
        }, status=status.HTTP_200_OK)
        



# ==============================================================================
# API نمایش جزئیات کامل رزرو (همراه با موجودی زنده کیف پول و وضعیت تایید)
# ==============================================================================
logger = logging.getLogger(__name__)

# کلاس احراز هویت هوشمند: کاربر لاگین را شناسایی می‌کند و در صورت عدم لاگین، خطای ۴۰۱ نمی‌دهد
try:
    from rest_framework_simplejwt.authentication import JWTAuthentication
    class SafeJWTAuthentication(JWTAuthentication):
        def authenticate(self, request):
            try:
                return super().authenticate(request)
            except Exception:
                return None
except ImportError:
    SafeJWTAuthentication = None


class ReservationDetailAPIView(APIView):
    """
    نمایش جزئیات رزرو بر اساس tracking_code:
    - برای مسافر مهمان و لاگین‌شده همیشه اطلاعات را بدون مسدودسازی لود می‌کند.
    - اگر کاربر لاگین باشد و رزرو پرداخت‌نشده باشد، خودکار رزرو را به نام کاربر الصاق می‌کند.
    - هرگز با خطای ۴۰۳ صفحه مسافر را قفل نمی‌کند.
    """
    permission_classes = [AllowAny]
    authentication_classes = [SafeJWTAuthentication] if SafeJWTAuthentication else []

    @swagger_auto_schema(
        operation_summary="نمایش جزئیات رزرو",
        operation_description="این API جزئیات کامل یک رزرو را بر اساس کد پیگیری (tracking_code) بازمی‌گرداند.",
        tags=["reservation-api"],
        responses={
            200: openapi.Response(
                description="جزئیات رزرو با موفقیت برگردانده شد.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'tracking_code': openapi.Schema(type=openapi.TYPE_STRING, example='sfa1234567890'),
                        'capacity_status': openapi.Schema(type=openapi.TYPE_STRING, example='confirmed'),
                        'payment_status': openapi.Schema(type=openapi.TYPE_STRING, example='pending'),
                        'final_price': openapi.Schema(type=openapi.TYPE_INTEGER, example=2450000),
                        'user_wallet_balance': openapi.Schema(type=openapi.TYPE_INTEGER, example=1500000),
                    }
                )
            ),
            404: "رزرو یا اطلاعات هتل یافت نشد."
        }
    )
    def get(self, request, tracking_code, *args, **kwargs):
        # دریافت رزرو با تطابق بدون حساسیت به حروف بزرگ و کوچک (Case-Insensitive)
        reservation = get_object_or_404(Reservationhotel, tracking_code__iexact=str(tracking_code).strip())

        # اتصال خودکار رزرو پرداخت‌نشده به کاربری که در این مرحله لاگین است
        if request.user and request.user.is_authenticated:
            try:
                if reservation.buyer is None or (reservation.buyer_id != request.user.id and reservation.payment_status != 'paid'):
                    reservation.buyer = request.user
                    reservation._skip_price_calculation_on_save = True
                    reservation.save(update_fields=['buyer'])
            except Exception as e:
                logger.warning(f"عدم توانایی در به‌روزرسانی خریدار رزرو {tracking_code}: {e}")

        # دریافت ایمن هتل مرتبط
        hotel = reservation.get_hotel()
        if not hotel:
            first_room = reservation.reservation_rooms.select_related('room__hotel').first()
            if first_room and first_room.room and first_room.room.hotel:
                hotel = first_room.room.hotel
            else:
                return Response(
                    {"detail": "اطلاعات هتل یا اتاق برای این رزرو یافت نشد."},
                    status=status.HTTP_404_NOT_FOUND
                )

        city = getattr(hotel, 'city', None)
        province = getattr(city, 'province', None) if city else None

        # دریافت ایمن پروفایل کاربر
        profile = None
        if request.user and request.user.is_authenticated:
            try:
                profile = getattr(request.user, 'natural_profile', None)
            except Exception:
                profile = None

        reserver_first_name = reservation.reserver_first_name or (profile.first_name if profile else '') or ''
        reserver_last_name = reservation.reserver_last_name or (profile.last_name if profile else '') or ''
        reserver_phone = reservation.reserver_phone_number or (getattr(request.user, 'phone_number', '') if (request.user and request.user.is_authenticated) else '') or ''
        reserver_code = reservation.reserver_national_code or (getattr(profile, 'national_code', '') if profile else '') or ''

        reserver_data = {
            'first_name': reserver_first_name,
            'last_name': reserver_last_name,
            'phone_number': reserver_phone,
            'national_code': reserver_code
        }

        # دریافت ایمن موجودی کیف پول کاربر
        user_wallet_balance = 0
        if request.user and request.user.is_authenticated:
            try:
                if hasattr(request.user, 'wallet') and request.user.wallet:
                    user_wallet_balance = int(request.user.wallet.balance)
            except Exception:
                user_wallet_balance = 0

        # فرمت‌بندی ساعت ورود و خروج
        def format_time(t_val, default="14:00:00"):
            if not t_val:
                return default
            return t_val.strftime('%H:%M:%S') if hasattr(t_val, 'strftime') else str(t_val)

        # استخراج ایمن تاریخ‌ها
        enter_date = None
        exit_date = None
        if reservation.check_in_date:
            enter_date = reservation.check_in_date.isoformat() if hasattr(reservation.check_in_date, 'isoformat') else str(reservation.check_in_date)
        if reservation.check_out_date:
            exit_date = reservation.check_out_date.isoformat() if hasattr(reservation.check_out_date, 'isoformat') else str(reservation.check_out_date)

        response_data = {
            'tracking_code': reservation.tracking_code,
            'capacity_status': reservation.capacity_status,
            'payment_status': reservation.payment_status,
            'snapp_status': reservation.snapp_status,
            'is_snapptrip': reservation.is_snapptrip_reservation,
            'final_price': int(reservation.final_price or 0),
            'user_wallet_balance': user_wallet_balance,
            'reserver': reserver_data,
            'date': {
                'enter': enter_date,
                'exit': exit_date
            },
            'time': {
                'enter': format_time(getattr(hotel, 'check_in_time', None), "14:00:00"),
                'exit': format_time(getattr(hotel, 'check_out_time', None), "12:00:00")
            },
            'number_of_nights': reservation.nights_count or 0,
            'hotel_name': getattr(hotel, 'name', 'نامشخص'),
            'hotel_star': getattr(hotel, 'stars', 0),
            'city_name': getattr(city, 'name', None),
            'province_name': getattr(province, 'name', None),
            'number_of_rooms': reservation.total_rooms or 1,
            'half_charges': {
                'enter': {
                    'enabled': bool(getattr(hotel, 'has_check_in_half_day_charge', False))
                },
                'exit': {
                    'enabled': bool(getattr(hotel, 'has_check_out_half_day_charge', False))
                }
            }
        }

        return Response(response_data, status=status.HTTP_200_OK)



# ==============================================================================
# API نمایش عکس هتل برای رزرو 
# ==============================================================================
logger = logging.getLogger(__name__)


class HotelImageAPIView(APIView):
    """
    نمایش لینک عکس اصلی و اسلاگ هتل بر اساس tracking_code:
    - برای کاربران مهمان و لاگین‌شده مجاز است.
    - در صورت لاگین بودن کاربر، رزرو مهمان را به کاربر متصل می‌کند.
    """
    permission_classes = [AllowAny]
    authentication_classes = [SafeJWTAuthentication] if 'SafeJWTAuthentication' in globals() and SafeJWTAuthentication else []

    @swagger_auto_schema(
        operation_summary="نمایش لینک عکس هتل و اسلاگ هتل",
        operation_description="این API لینک عکس اصلی هتل و اسلاگ هتل را بر اساس کد پیگیری نمایش می‌دهد.",
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

        # اگر رزرو مهمان بود و کاربر الان لاگین است، متصل شود
        if reservation.buyer is None:
            if request.user and request.user.is_authenticated:
                reservation.buyer = request.user
                reservation.save(update_fields=['buyer'])
        elif reservation.buyer != request.user:
            return Response(
                {"detail": "شما اجازه دسترسی به این رزرو را ندارید."},
                status=status.HTTP_403_FORBIDDEN
            )

        # دریافت اتاق و هتل مرتبط
        reservation_room = reservation.reservation_rooms.select_related('room__hotel').first()
        if not reservation_room or not reservation_room.room or not reservation_room.room.hotel:
            return Response(
                {"detail": "اطلاعات هتل یا اتاق یافت نشد."},
                status=status.HTTP_404_NOT_FOUND
            )

        hotel = reservation_room.room.hotel

        # ساخت لینک کامل عکس به صورت ایمن
        site_url = getattr(settings, "SITE_URL", "https://zarvantrip.com")
        image_url = ""
        if hotel.main_image and hasattr(hotel.main_image, 'url'):
            image_url = f"{site_url}{hotel.main_image.url}"

        response_data = {
            'hotel_image': image_url,
            'hotel_slug': hotel.slug or ""
        }

        return Response(response_data, status=status.HTTP_200_OK)
    
    
    




# ==============================================================================
# ۳. صورت‌حساب رزرو (بدون خطای دسترسی)
# ==============================================================================
class ReservationInvoiceAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [SafeJWTAuthentication] if 'SafeJWTAuthentication' in globals() and SafeJWTAuthentication else []

    def parse_number(self, value):
        if value is None:
            return Decimal('0')
        try:
            return Decimal(str(value).replace(',', '').strip())
        except Exception:
            return Decimal('0')

    def get(self, request, tracking_code):
        reservation = get_object_or_404(Reservationhotel, tracking_code__iexact=tracking_code)

        # الصاق رزرو به کاربر لاگین‌شده
        if request.user and request.user.is_authenticated:
            if reservation.buyer != request.user:
                reservation.buyer = request.user
                reservation._skip_price_calculation_on_save = True
                reservation.save(update_fields=['buyer'])

        user_wallet_balance = 0
        if request.user and request.user.is_authenticated and hasattr(request.user, 'wallet') and request.user.wallet:
            user_wallet_balance = int(request.user.wallet.balance)

        response_data = {
            "tracking_code": reservation.tracking_code,
            "nights_count": reservation.nights_count or 0,
            "total_price": int(self.parse_number(reservation.total_price)),
            "extra_passengers": int(self.parse_number(reservation.total_extra_passenger_charge)),
            "half_charges": int(self.parse_number(reservation.total_half_day_charge)),
            "discount_on_purchase": int(self.parse_number(reservation.room_fixed_discount)),
            "discount_code": int(self.parse_number(reservation.discount)),
            "applied_discount_code": reservation.applied_discount_code or None,
            "wallet_withdraw": int(self.parse_number(reservation.wallet_withdrawal_amount)),
            "wallet_withdrawn": bool(reservation.wallet_withdrawn),
            "final_price": int(self.parse_number(reservation.final_price)),
            "user_wallet_balance": user_wallet_balance,
            "capacity_status": reservation.capacity_status,
            "payment_status": reservation.payment_status,
        }

        return Response(response_data, status=status.HTTP_200_OK)



# ==============================================================================
# API توضیحات تکمیلی رزرو (هماهنگ با کاربر مهمان و فیلد کاملاً اختیاری)
# ==============================================================================
class ReservationDescriptionAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [SafeJWTAuthentication] if 'SafeJWTAuthentication' in globals() and SafeJWTAuthentication else []

    @swagger_auto_schema(
        operation_summary="دریافت توضیحات رزرو",
        operation_description="دریافت توضیحات تکمیلی یک رزرو بر اساس کد پیگیری.",
        tags=["reservation-api"]
    )
    def get(self, request, tracking_code):
        reservation = get_object_or_404(Reservationhotel, tracking_code__iexact=tracking_code)

        # اگر رزرو قبلاً به کاربری الصاق شده باشد، غریبه اجازه مشاهده ندارد
        if reservation.buyer is not None and request.user.is_authenticated and reservation.buyer != request.user:
            return Response(
                {"detail": "شما اجازه دسترسی به این رزرو را ندارید.", "message": "شما اجازه دسترسی به این رزرو را ندارید."},
                status=status.HTTP_403_FORBIDDEN
            )

        return Response({
            'description': reservation.additional_notes or ''
        }, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="بروزرسانی توضیحات رزرو",
        operation_description="بروزرسانی توضیحات تکمیلی یک رزرو بر اساس کد پیگیری (توضیحات اختیاری است).",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'description': openapi.Schema(type=openapi.TYPE_STRING, description='توضیحات رزرو (اختیاری)')
            }
        ),
        tags=["reservation-api"]
    )
    def put(self, request, tracking_code):
        reservation = get_object_or_404(Reservationhotel, tracking_code__iexact=tracking_code)

        # اگر کاربر در این مرحله لاگین است و رزرو هنوز مالک ندارد، به کاربر الصاق شود
        if request.user and request.user.is_authenticated:
            if reservation.buyer is None:
                reservation.buyer = request.user
                reservation._skip_price_calculation_on_save = True
                reservation.save(update_fields=['buyer'])
            elif reservation.buyer != request.user:
                return Response(
                    {"detail": "شما اجازه دسترسی به این رزرو را ندارید.", "message": "شما اجازه دسترسی به این رزرو را ندارید."},
                    status=status.HTTP_403_FORBIDDEN
                )

        # فیلد توضیحات اختیاری است؛ در صورت خالی بودن رشته خالی ذخیره می‌شود و ارور ۴۰۰ نمی‌دهد
        notes = request.data.get('description', '')
        if notes is None:
            notes = ''

        reservation.additional_notes = str(notes).strip()
        reservation._skip_price_calculation_on_save = True
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





# ==============================================================================
# API دریافت و ویرایش مسافران، اتاق‌ها و نیم‌شارژهای رزرو (بدون مسدودسازی ۴۰۳)
# ==============================================================================
logger = logging.getLogger(__name__)


class ReservationRoomDetailAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [SafeJWTAuthentication] if 'SafeJWTAuthentication' in globals() and SafeJWTAuthentication else []

    def get(self, request, tracking_code):
        reservation = get_object_or_404(
            Reservationhotel.objects.prefetch_related(
                'reservation_rooms__room__hotel',
                'reservation_rooms__passengers'
            ),
            tracking_code__iexact=tracking_code
        )

        # اگر کاربر لاگین است، رزرو به نام کاربر الصاق می‌شود (بدون ارور ۴۰۳)
        if request.user and request.user.is_authenticated:
            if reservation.buyer != request.user:
                reservation.buyer = request.user
                reservation._skip_price_calculation_on_save = True
                reservation.save(update_fields=['buyer'])

        user_wallet_balance = 0
        if request.user and request.user.is_authenticated and hasattr(request.user, 'wallet') and request.user.wallet:
            user_wallet_balance = int(request.user.wallet.balance)

        profile = getattr(request.user, 'natural_profile', None) if (request.user and request.user.is_authenticated) else None
        reserver_data = {
            'first_name': reservation.reserver_first_name or (profile.first_name if profile else '') or '',
            'last_name': reservation.reserver_last_name or (profile.last_name if profile else '') or '',
            'phone_number': reservation.reserver_phone_number or (getattr(request.user, 'phone_number', '') if (request.user and request.user.is_authenticated) else '') or '',
            'national_code': reservation.reserver_national_code or (profile.national_code if profile else '') or ''
        }

        response_data = {
            "tracking_code": reservation.tracking_code,
            "capacity_status": reservation.capacity_status,
            "payment_status": reservation.payment_status,
            "final_price": int(reservation.final_price or 0),
            "user_wallet_balance": user_wallet_balance,
            "reserver": reserver_data,
            "rooms": []
        }

        for res_room in reservation.reservation_rooms.all():
            if not res_room.room:
                continue

            hotel = getattr(res_room.room, 'hotel', None)
            has_in_charge = bool(getattr(hotel, 'has_check_in_half_day_charge', False)) if hotel else False
            has_out_charge = bool(getattr(hotel, 'has_check_out_half_day_charge', False)) if hotel else False

            half_day_in_price = int(res_room.half_day_in_price or 0) if has_in_charge else 0
            half_day_out_price = int(res_room.half_day_out_price or 0) if has_out_charge else 0

            main_p = {
                "first_name": "",
                "last_name": "",
                "phone_number": "",
                "national_code": ""
            }
            other_p = []
            extra_p = []

            for passenger in res_room.passengers.all():
                p_data = {
                    "first_name": passenger.first_name or "",
                    "last_name": passenger.last_name or "",
                    "phone_number": passenger.mobile_number or "",
                    "national_code": passenger.national_code or ""
                }
                if passenger.passenger_type == "primary":
                    main_p = p_data
                elif passenger.passenger_type == "secondary":
                    other_p.append(p_data)
                elif passenger.passenger_type == "extra":
                    extra_p.append(p_data)

            room_data = {
                "id": res_room.room.id,
                "name": res_room.room.title or "",
                "capacity": int(res_room.room.room_capacity or 0),
                "extra_capacity": int(res_room.room.extra_capacity or 0),
                "extra_capacity_price": int(res_room.extra_passenger_price or 0),
                "discount_on_purchase": int(res_room.fixed_discount or 0),
                "passengers": {
                    "main_passenger": main_p,
                    "other_passengers": other_p,
                    "extra_capacity_passengers": extra_p
                },
                "half_charges": {
                    "enter": {
                        "enabled": bool(res_room.half_day_in_selected and has_in_charge),
                        "price": half_day_in_price,
                        "available": has_in_charge
                    },
                    "exit": {
                        "enabled": bool(res_room.half_day_out_selected and has_out_charge),
                        "price": half_day_out_price,
                        "available": has_out_charge
                    }
                }
            }

            response_data["rooms"].append(room_data)

        return Response(response_data, status=status.HTTP_200_OK)

    def put(self, request, tracking_code):
        try:
            with transaction.atomic():
                reservation = get_object_or_404(Reservationhotel, tracking_code__iexact=tracking_code)

                # 👇 الصاق مستقیم رزرو به کاربر لاگین‌شده بدون هیچ شرط مسدودکننده
                if request.user and request.user.is_authenticated:
                    reservation.buyer = request.user

                if reservation.payment_status == 'paid':
                    return Response(
                        {"detail": "این رزرو قبلاً پرداخت شده است.", "message": "این رزرو قبلاً پرداخت شده است."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                data = request.data
                reserver_data = data.get('reserver', {})
                rooms_data = data.get('rooms', [])

                def clean_str(val):
                    s = str(val or '').strip()
                    return s if s else None

                # ثبت مشخصات رزروکننده
                res_first = clean_str(reserver_data.get('first_name')) or reservation.reserver_first_name or "رزروکننده"
                res_last = clean_str(reserver_data.get('last_name')) or reservation.reserver_last_name or "اصلی"
                res_phone = clean_str(reserver_data.get('phone_number')) or reservation.reserver_phone_number or ""
                res_code = clean_str(reserver_data.get('national_code'))

                reservation.reserver_first_name = res_first
                reservation.reserver_last_name = res_last
                reservation.reserver_phone_number = res_phone
                reservation.reserver_national_code = res_code
                reservation._skip_price_calculation_on_save = True

                save_fields = ['reserver_first_name', 'reserver_last_name', 'reserver_phone_number', 'reserver_national_code']
                if reservation.buyer:
                    save_fields.append('buyer')
                reservation.save(update_fields=save_fields)

                # ثبت مشخصات اتاق‌ها و مسافران
                res_rooms_list = list(reservation.reservation_rooms.all())
                used_res_rooms = []

                for room_data in rooms_data:
                    room_id = room_data.get('id')
                    res_room = next((r for r in res_rooms_list if r.room_id == room_id and r not in used_res_rooms), None)

                    if not res_room and res_rooms_list:
                        res_room = next((r for r in res_rooms_list if r not in used_res_rooms), None)

                    if not res_room:
                        continue

                    used_res_rooms.append(res_room)
                    passengers_data = room_data.get('passengers', {})
                    half_charges = room_data.get('half_charges', {})
                    hotel = res_room.room.hotel if res_room.room else None

                    if hotel:
                        res_room.half_day_in_selected = bool(half_charges.get('enter', {}).get('enabled', False) and getattr(hotel, 'has_check_in_half_day_charge', False))
                        res_room.half_day_out_selected = bool(half_charges.get('exit', {}).get('enabled', False) and getattr(hotel, 'has_check_out_half_day_charge', False))
                        try:
                            res_room.calculate_half_day_prices()
                        except Exception:
                            pass

                    res_room.save(update_fields=[
                        'half_day_in_selected', 'half_day_out_selected',
                        'half_day_in_price', 'half_day_out_price'
                    ])

                    # ذخیره مسافران اتاق
                    res_room.passengers.all().delete()
                    main_p = passengers_data.get('main_passenger', {})
                    main_fn = clean_str(main_p.get('first_name')) or res_first
                    main_ln = clean_str(main_p.get('last_name')) or res_last
                    main_phone = clean_str(main_p.get('phone_number')) or res_phone
                    main_nat = clean_str(main_p.get('national_code'))

                    ReservationRoomPassenger.objects.create(
                        reservation_room=res_room,
                        passenger_type='primary',
                        first_name=main_fn,
                        last_name=main_ln,
                        mobile_number=main_phone,
                        national_code=main_nat,
                        is_primary=True
                    )

                    # ذخیره سایر مسافران
                    for p_type in ['other_passengers', 'extra_capacity_passengers']:
                        p_db = 'secondary' if p_type == 'other_passengers' else 'extra'
                        for p in passengers_data.get(p_type, []):
                            p_fn = clean_str(p.get('first_name'))
                            p_ln = clean_str(p.get('last_name'))
                            p_phone = clean_str(p.get('phone_number'))
                            p_nat = clean_str(p.get('national_code'))

                            if p_fn or p_ln:
                                ReservationRoomPassenger.objects.create(
                                    reservation_room=res_room,
                                    passenger_type=p_db,
                                    first_name=p_fn or "همراه",
                                    last_name=p_ln or "مسافر",
                                    mobile_number=p_phone,
                                    national_code=p_nat,
                                    is_primary=False
                                )

                # بازمحاسبه نهایی مبالغ با پوشش خطا
                try:
                    (total_price, total_extra, discount_amount, half_in, half_out,
                     total_half, code_discount, final_price, room_fixed) = reservation.calculate_total_price()

                    reservation.total_price = total_price
                    reservation.total_extra_passenger_charge = total_extra
                    reservation.discount = code_discount
                    reservation.room_fixed_discount = room_fixed
                    reservation.half_day_in_charge = half_in
                    reservation.half_day_out_charge = half_out
                    reservation.total_half_day_charge = total_half
                    reservation.final_price = final_price
                except Exception as calc_err:
                    logger.warning(f"محاسبه قیمت: {calc_err}")

                reservation._skip_price_calculation_on_save = True
                save_fields = [
                    'total_price', 'total_extra_passenger_charge', 'discount',
                    'room_fixed_discount', 'half_day_in_charge',
                    'half_day_out_charge', 'total_half_day_charge', 'final_price'
                ]
                if reservation.buyer:
                    save_fields.append('buyer')
                reservation.save(update_fields=save_fields)

            user_wallet_balance = int(request.user.wallet.balance) if (request.user and request.user.is_authenticated and hasattr(request.user, 'wallet') and request.user.wallet) else 0

            # ارسال وب‌سوکت
            try:
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f"reservation_{reservation.tracking_code}",
                    {
                        "type": "status_update",
                        "message": {
                            "capacity_status": reservation.capacity_status,
                            "payment_status": reservation.payment_status,
                            "final_price": int(reservation.final_price),
                            "wallet_balance": user_wallet_balance,
                        },
                    },
                )
            except Exception:
                pass

            return Response({
                'detail': 'اطلاعات با موفقیت ذخیره شد.',
                'tracking_code': reservation.tracking_code,
                'final_price': int(reservation.final_price),
                'user_wallet_balance': user_wallet_balance
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception(f"خطا در متد put رزرو {tracking_code}: {e}")
            return Response({
                "detail": f"خطا در ثبت اطلاعات: {str(e)}",
                "message": f"خطا در ثبت اطلاعات: {str(e)}"
            }, status=status.HTTP_400_BAD_REQUEST)


    
# ------------------------------------------------------------------------------
# احراز هویت امن: در صورت لاگین کاربر شناسایی می‌شود و در صورت عدم لاگین، خطای ۴۰۱ نمی‌دهد
# ------------------------------------------------------------------------------
from rest_framework_simplejwt.authentication import JWTAuthentication

class SafeJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        try:
            return super().authenticate(request)
        except Exception:
            return None


# لیست مسافران برای بخش رزرو (پشتیبانی از کاربر مهمان و لاگین‌شده)
class PassengerListForReservationView(generics.GenericAPIView):
    """
    API لیست مسافران برای بخش رزرواسیون بدون صفحه‌بندی:
    - برای کاربران واردشده: لیست دفترچه مسافران ذخیره‌شده را برمی‌گرداند.
    - برای کاربران مهمان: بدون پرتاب خطای ۴۰۱، یک آرایه خالی [] با وضعیت ۲۰۰ بازمی‌گرداند.
    """
    permission_classes = [AllowAny]
    authentication_classes = [SafeJWTAuthentication]
    serializer_class = PassengerSerializer

    def get_queryset(self):
        if self.request.user and self.request.user.is_authenticated:
            return Passenger.objects.filter(user=self.request.user)
        return Passenger.objects.none()

    @swagger_auto_schema(
        tags=["reservation-api"],
        operation_summary="لیست مسافران برای رزرواسیون",
        operation_description="مسافران ذخیره‌شده کاربر جاری را برمی‌گرداند (برای کاربر مهمان لیست خالی ارسال می‌شود).",
        responses={200: PassengerSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        try:
            # اگر کاربر هنوز لاگین نکرده است، لیست خالی برگردان تا فرم مسافران بدون خطا لود شود
            if not request.user or not request.user.is_authenticated:
                return Response([], status=status.HTTP_200_OK)

            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as exc:
            logger.error(f"خطا در دریافت لیست مسافران برای رزرو: {exc}")
            # بازگرداندن آرایه خالی در صورت هرگونه خطا تا فرانت‌اند کرش نکند
            return Response([], status=status.HTTP_200_OK)


# استفاده از تابع کنترل سیگنال‌های مدل به جای تعریف thread_local موازی
try:
    from .models import set_skip_points_and_sms, get_skip_points_and_sms
except ImportError:
    _thread_locals = local()
    def set_skip_points_and_sms(value):
        setattr(_thread_locals, 'skip_points_and_sms', value)
    def get_skip_points_and_sms():
        return getattr(_thread_locals, 'skip_points_and_sms', False)



# ==============================================================================
# ۶. API اعمال و حذف کدهای تخفیف روی رزرو (هماهنگ با رزروهای جدید)
# ==============================================================================
class ApplyDiscountCodeAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [SafeJWTAuthentication] if 'SafeJWTAuthentication' in globals() and SafeJWTAuthentication else []

    def post(self, request, tracking_code, *args, **kwargs):
        code = request.data.get("discount_code", "").strip().upper()
        if not code:
            return Response({"error": "فیلد discount_code الزامی است."}, status=status.HTTP_400_BAD_REQUEST)

        reservation = get_object_or_404(Reservationhotel, tracking_code__iexact=tracking_code)

        if request.user and request.user.is_authenticated:
            reservation.buyer = request.user

        if reservation.payment_status == 'paid':
            return Response(
                {"error": "این رزرو پرداخت شده است و امکان تغییر کد تخفیف وجود ندارد."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # پیدا کردن کد تخفیف
        discount_obj = None
        discount_type = None
        try:
            discount_obj = RoomDiscountCode.objects.get(code__iexact=code)
            discount_type = 'room'
        except RoomDiscountCode.DoesNotExist:
            try:
                discount_obj = HotelDiscountCode.objects.get(code__iexact=code)
                discount_type = 'hotel'
            except HotelDiscountCode.DoesNotExist:
                try:
                    discount_obj = PersonalDiscountCode.objects.get(code__iexact=code)
                    discount_type = 'personal'
                except PersonalDiscountCode.DoesNotExist:
                    return Response({"error": "کد تخفیف وارد شده معتبر نیست."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            reservation.discount = Decimal('0')
            (total, total_extra, _, half_day_in_charge, half_day_out_charge,
             total_half_day_charge, _, base_payable, room_fixed_discount) = reservation.calculate_total_price()

            gross_amount = total + total_extra + total_half_day_charge - room_fixed_discount
            discount_value = min(Decimal(discount_obj.discount_value), max(Decimal('0'), gross_amount))

            reservation.applied_discount_code = code
            reservation.discount = discount_value
            reservation.total_price = total
            reservation.total_extra_passenger_charge = total_extra
            reservation.room_fixed_discount = room_fixed_discount
            reservation.half_day_in_charge = half_day_in_charge
            reservation.half_day_out_charge = half_day_out_charge
            reservation.total_half_day_charge = total_half_day_charge

            price_after_promo = max(Decimal('0'), gross_amount - discount_value)
            reservation.final_price = max(Decimal('0'), price_after_promo - (reservation.wallet_withdrawal_amount or Decimal('0')))

            reservation._skip_price_calculation_on_save = True
            save_fields = [
                'applied_discount_code', 'discount', 'final_price', 'total_price',
                'room_fixed_discount', 'half_day_in_charge', 'half_day_out_charge',
                'total_half_day_charge', 'total_extra_passenger_charge'
            ]
            if reservation.buyer:
                save_fields.append('buyer')
            reservation.save(update_fields=save_fields)

        user_wallet_balance = int(request.user.wallet.balance) if (request.user and hasattr(request.user, 'wallet') and request.user.wallet) else 0

        return Response({
            "status": "ok",
            "tracking_code": reservation.tracking_code,
            "discount_code": code,
            "discount_value": int(discount_value),
            "final_price": int(reservation.final_price),
            "total_discount": int(reservation.discount),
            "user_wallet_balance": user_wallet_balance
        }, status=status.HTTP_200_OK)

    def delete(self, request, tracking_code, *args, **kwargs):
        reservation = get_object_or_404(Reservationhotel, tracking_code__iexact=tracking_code)

        if reservation.payment_status == 'paid':
            return Response({"error": "رزرو پرداخت شده است."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            reservation.discount = Decimal('0')
            reservation.applied_discount_code = None

            (total, total_extra, _, half_day_in_charge, half_day_out_charge,
             total_half_day_charge, _, final_pay, room_fixed_discount) = reservation.calculate_total_price()

            reservation.total_price = total
            reservation.total_extra_passenger_charge = total_extra
            reservation.room_fixed_discount = room_fixed_discount
            reservation.half_day_in_charge = half_in_charge
            reservation.half_day_out_charge = half_out_charge
            reservation.total_half_day_charge = total_half_day_charge
            reservation.final_price = final_pay

            reservation._skip_price_calculation_on_save = True
            reservation.save(update_fields=[
                'applied_discount_code', 'discount', 'final_price', 'total_price',
                'room_fixed_discount', 'half_day_in_charge', 'half_day_out_charge',
                'total_half_day_charge', 'total_extra_passenger_charge'
            ])

        user_wallet_balance = int(request.user.wallet.balance) if (request.user and hasattr(request.user, 'wallet') and request.user.wallet) else 0

        return Response({
            "status": "ok",
            "tracking_code": reservation.tracking_code,
            "discount_code": None,
            "final_price": int(reservation.final_price),
            "total_discount": 0,
            "user_wallet_balance": user_wallet_balance
        }, status=status.HTTP_200_OK)
        
        


# ==============================================================================
# API تنظیم و حذف برداشت از کیف پول کاربر (همراه با وب‌سوکت و اعتبارسنجی دقیق)
# ==============================================================================
logger = logging.getLogger(__name__)


class WalletWithdrawAPIView(APIView):
    """
    تنظیم یا حذف کسر وجه از کیف پول کاربر برای رزرو مشخص:
    - بررسی مالکیت رزرو و باز بودن وضعیت پرداخت (pending)
    - اعتبارسنجی سقف موجودی کیف پول کاربر و سقف صورت‌حساب
    - بازمحاسبه دقیق مبلغ نهایی (final_price) بدون کسر مضاعف
    - ارسال پیام زنده وب‌سوکت برای به‌روزرسانی فاکتور مسافر در فرانت‌اند
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="تنظیم برداشت از کیف پول برای رزرو",
        operation_description="""
        این API به کاربر احراز هویت‌شده اجازه می‌دهد مبلغ برداشت از کیف پول را برای یک رزرو مشخص تنظیم یا حذف کند.
        - مبلغ ارسالی به تومان است.
        - ارسال عدد ۰ به معنای حذف برداشت از کیف پول است.
        - مبلغ فقط در صورت پرداخت نهایی (payment_status='paid') قطعی از حساب کسر خواهد شد.
        """,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'amount': openapi.Schema(type=openapi.TYPE_INTEGER, description='مبلغ برداشت به تومان (۰ برای حذف)'),
            },
            required=['amount']
        ),
        responses={
            200: openapi.Response(
                description="برداشت با موفقیت تنظیم یا حذف شد.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'detail': openapi.Schema(type=openapi.TYPE_STRING),
                        'wallet_balance': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'wallet_withdrawal_amount': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'final_price': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'total_price': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'extra_passengers': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'half_charges': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'discount_code_amount': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'room_fixed_discount': openapi.Schema(type=openapi.TYPE_INTEGER),
                    }
                )
            ),
            400: "خطای اعتبارسنجی (مبلغ نامعتبر، رزرو رد شده یا پرداخت‌شده)",
            403: "عدم دسترسی به رزرو",
            404: "رزرو یا کیف پول یافت نشد",
        },
        tags=["reservation-api"]
    )
    def post(self, request, tracking_code):
        reservation = get_object_or_404(Reservationhotel, tracking_code=tracking_code)

        # ۱. اعتبارسنجی مالکیت رزرو
        if reservation.buyer != request.user:
            logger.warning(f"کاربر {request.user.phone_number} تلاش کرد به رزرو {tracking_code} دسترسی پیدا کند.")
            return Response({"detail": "شما به این رزرو دسترسی ندارید."}, status=status.HTTP_403_FORBIDDEN)

        # ۲. بررسی وضعیت پرداخت و ظرفیت
        if reservation.payment_status != 'pending':
            return Response({"detail": "امکان تغییر برداشت کیف پول برای رزرو پرداخت‌شده وجود ندارد."}, status=status.HTTP_400_BAD_REQUEST)

        if reservation.capacity_status == 'rejected':
            return Response({"detail": "این رزرو لغو شده است و امکان تغییر کیف پول وجود ندارد."}, status=status.HTTP_400_BAD_REQUEST)

        # ۳. اعتبارسنجی مقدار ارسالی
        amount_raw = request.data.get('amount')
        try:
            amount = Decimal(str(amount_raw).replace(',', '').strip())
        except Exception:
            return Response({"detail": "مبلغ ارسالی نامعتبر است."}, status=status.HTTP_400_BAD_REQUEST)

        if amount < 0:
            return Response({"detail": "مبلغ برداشت نمی‌تواند منفی باشد."}, status=status.HTTP_400_BAD_REQUEST)

        if 0 < amount < 10000:
            return Response({"detail": "حداقل مبلغ برداشت از کیف پول ۱۰,۰۰۰ تومان است."}, status=status.HTTP_400_BAD_REQUEST)

        wallet = getattr(request.user, "wallet", None)
        if not wallet:
            return Response({"detail": "کیف پول کاربر یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

        if amount > wallet.balance:
            return Response({"detail": "مبلغ انتخابی بیشتر از موجودی کیف پول شما است."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # موقتاً برداشت قبلی را صفر می‌کنیم تا سقف قابل پرداخت خالص محاسبه شود
            reservation.wallet_withdrawal_amount = Decimal('0')
            (total, total_extra, disc_field, half_in, half_out,
             tot_half, code_discount, price_before_wallet, r_fixed) = reservation.calculate_total_price()

            if amount > price_before_wallet:
                return Response({
                    "detail": f"مبلغ برداشت ({int(amount):,} تومان) نمی‌تواند بیشتر از کل مبلغ صورت‌حساب ({int(price_before_wallet):,} تومان) باشد."
                }, status=status.HTTP_400_BAD_REQUEST)

            # تنظیم مقادیر جدید
            reservation.wallet_withdrawal_amount = amount
            reservation.wallet_withdrawn = False
            reservation.total_price = total
            reservation.total_extra_passenger_charge = total_extra
            reservation.discount = disc_field
            reservation.room_fixed_discount = r_fixed
            reservation.half_day_in_charge = half_in
            reservation.half_day_out_charge = half_out
            reservation.total_half_day_charge = tot_half
            reservation.final_price = max(Decimal('0'), price_before_wallet - amount)

            # استفاده از نام صحیح فلگ جهت جلوگیری از دوباره‌نویسی اشتباه مدل
            reservation._skip_price_calculation_on_save = True
            reservation.save(update_fields=[
                "wallet_withdrawal_amount", "wallet_withdrawn",
                "total_price", "total_extra_passenger_charge", "discount",
                "room_fixed_discount", "half_day_in_charge", "half_day_out_charge",
                "total_half_day_charge", "final_price"
            ])

        # ارسال به‌روزرسانی زنده به وب‌سوکت فرانت‌اند
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"reservation_{reservation.tracking_code}",
            {
                "type": "status_update",
                "message": {
                    "capacity_status": reservation.capacity_status,
                    "payment_status": reservation.payment_status,
                    "final_price": int(reservation.final_price),
                    "wallet_withdrawal_amount": int(reservation.wallet_withdrawal_amount),
                    "wallet_balance": int(wallet.balance),
                },
            },
        )

        message = "برداشت از کیف پول حذف شد." if amount == 0 else "برداشت از کیف پول با موفقیت تنظیم شد."
        logger.info(f"کیف پول رزرو {tracking_code} بروز شد: مبلغ={amount}، مانده نهایی={reservation.final_price}")

        return Response({
            "detail": message,
            "wallet_balance": int(wallet.balance),
            "wallet_withdrawal_amount": int(reservation.wallet_withdrawal_amount),
            "final_price": int(reservation.final_price),
            "discount_code_amount": int(code_discount or 0),
            "room_fixed_discount": int(r_fixed or 0),
            "total_price": int(total),
            "extra_passengers": int(total_extra),
            "half_charges": int(tot_half),
        }, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="حذف برداشت از کیف پول برای رزرو",
        operation_description="این API برداشت از کیف پول را برای رزرو مشخص به طور کامل صفر می‌کند.",
        responses={
            200: "برداشت از کیف پول حذف شد.",
            400: "وضعیت پرداخت یا رزرو اجازه حذف نمی‌دهد.",
            403: "عدم دسترسی به رزرو",
            404: "رزرو یافت نشد.",
        },
        tags=["reservation-api"]
    )
    def delete(self, request, tracking_code):
        reservation = get_object_or_404(Reservationhotel, tracking_code=tracking_code)

        if reservation.buyer != request.user:
            return Response({"detail": "شما به این رزرو دسترسی ندارید."}, status=status.HTTP_403_FORBIDDEN)

        if reservation.payment_status != 'pending':
            return Response({"detail": "امکان حذف برداشت برای رزرو پرداخت‌شده وجود ندارد."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            reservation.wallet_withdrawal_amount = Decimal('0')
            reservation.wallet_withdrawn = False

            # بازمحاسبه قیمت بدون کسر کیف پول
            (total, total_extra, disc_field, half_in, half_out,
             tot_half, code_discount, final_no_w, r_fixed) = reservation.calculate_total_price()

            reservation.total_price = total
            reservation.total_extra_passenger_charge = total_extra
            reservation.discount = disc_field
            reservation.room_fixed_discount = r_fixed
            reservation.half_day_in_charge = half_in
            reservation.half_day_out_charge = half_out
            reservation.total_half_day_charge = tot_half
            reservation.final_price = max(Decimal('0'), final_no_w)

            reservation._skip_price_calculation_on_save = True
            reservation.save(update_fields=[
                "wallet_withdrawal_amount", "wallet_withdrawn",
                "total_price", "total_extra_passenger_charge", "discount",
                "room_fixed_discount", "half_day_in_charge", "half_day_out_charge",
                "total_half_day_charge", "final_price"
            ])

        wallet = getattr(request.user, "wallet", None)
        user_balance = int(wallet.balance) if wallet else 0

        # ارسال به‌روزرسانی به وب‌سوکت
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"reservation_{reservation.tracking_code}",
            {
                "type": "status_update",
                "message": {
                    "capacity_status": reservation.capacity_status,
                    "payment_status": reservation.payment_status,
                    "final_price": int(reservation.final_price),
                    "wallet_withdrawal_amount": 0,
                    "wallet_balance": user_balance,
                },
            },
        )

        logger.info(f"برداشت کیف پول برای رزرو {tracking_code} به صفر بازگردانده شد.")

        return Response({
            "detail": "برداشت از کیف پول حذف شد.",
            "wallet_balance": user_balance,
            "wallet_withdrawal_amount": 0,
            "final_price": int(reservation.final_price),
            "total_price": int(total),
            "extra_passengers": int(total_extra),
            "half_charges": int(tot_half),
            "discount_code_amount": int(code_discount or 0),
            "room_fixed_discount": int(r_fixed or 0),
        }, status=status.HTTP_200_OK)
        
        
        




    
# ای پی ای سئو هتل ها 
class HotelSEOView(APIView):
    """
    API برای دریافت اطلاعات سئوی یک هتل
    """
    permission_classes = ()  # عمومی

    @swagger_auto_schema(
        operation_summary="دریافت متا سئو هتل با slug",
        operation_description="""
        این API اطلاعات سئو یک هتل را برمی‌گرداند، شامل:
        - title_tag: عنوان سئو
        - description: توضیحات متا
        - keywords: کلمات کلیدی به صورت لیست
        """,
        responses={
            200: openapi.Response(
                description="اطلاعات سئو هتل با موفقیت بازگشت داده شد",
                examples={
                    "application/json": {
                        "title_tag": "هتل لوکس تهران",
                        "description": "بهترین هتل لوکس تهران با امکانات عالی",
                        "keywords": ["هتل", "لوکس", "تهران"]
                    }
                }
            ),
            404: "هتل یا سئو پیدا نشد"
        },
        tags=["hotel-seo"]
    )
    def get(self, request, hotel_slug):
        try:
            hotel = Hotel.objects.get(slug=hotel_slug)
        except Hotel.DoesNotExist:
            return Response({"detail": "هتل پیدا نشد."}, status=status.HTTP_404_NOT_FOUND)

        try:
            seo = hotel.seo_meta
        except SEOMeta.DoesNotExist:
            return Response({"detail": "سئوی هتل یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

        # تبدیل رشته keywords با "-" به لیست
        if isinstance(seo.keywords, str):
            keywords_list = [k.strip() for k in seo.keywords.split('-') if k.strip()]
        else:
            # اگر قبلاً JSON بود، مستقیم استفاده می‌کنیم
            keywords_list = seo.keywords

        return Response(
            {
                "title_tag": seo.title_tag,
                "description": seo.description,
                "keywords": keywords_list
            },
            status=status.HTTP_200_OK
        )
        
        


#ای پی ای لیست رزرو های کاربران در داشبورد 
class UserReservationListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="دریافت لیست رزروهای کاربر",
        operation_description="""
        لیست رزروهای کاربر احراز هویت‌شده با صفحه‌بندی سفارشی.
        
        پارامترها:
        - p: شماره صفحه (مثلاً p=1)
        - page_size: تعداد آیتم در هر صفحه (پیش‌فرض: 10، حداکثر: 100)
        
        فیلدهای بازگشتی:
        - tracking_code
        - hotel_name
        - check_in_date (جلالی)
        - check_out_date (جلالی)
        - total_guests (لیست تعداد مسافران هر اتاق)
        - payment_status
        - cancellation_status (وضعیت کنسلی: true=تایید شده, false=عدم تایید, null=بدون درخواست)
        - created_at (جلالی: 1403/06/15 14:30)
        """,
        manual_parameters=[
            openapi.Parameter('p', openapi.IN_QUERY, description="شماره صفحه", type=openapi.TYPE_INTEGER, example=1),
            openapi.Parameter('page_size', openapi.IN_QUERY, description="تعداد آیتم در صفحه (حداکثر 100)", type=openapi.TYPE_INTEGER, example=10),
        ],
        responses={
            200: openapi.Response(
                description="لیست رزروها با صفحه‌بندی",
                examples={
                    "application/json": {
                        "count": 23,
                        "total_pages": 3,
                        "current_page": 1,
                        "results": [
                            {
                                "tracking_code": "RSV123456",
                                "hotel_name": "هتل آزادی تهران",
                                "check_in_date": "1403-07-01",
                                "check_out_date": "1403-07-05",
                                "total_guests": [2, 3],
                                "payment_status": "paid",
                                "cancellation_status": True,
                                "created_at": "1403/06/15 14:30"
                            }
                        ]
                    }
                }
            ),
            401: "احراز هویت لازم است.",
            503: "خطا در اتصال به پایگاه داده. لطفاً稍后 تلاش کنید."
        },
        tags=["reservedashboard-api"]
    )
    def get(self, request):
        max_retries = 3
        retry_delay = 2  # ثانیه
        
        for attempt in range(max_retries):
            try:
                print(f"Attempt {attempt + 1}/{max_retries} to fetch reservations...")
                
                # تست اتصال به دیتابیس قبل از اجرای کوئری
                self._test_database_connection()
                print("Database connection successful")
                
                # اجرای منطق اصلی
                return self._get_reservations(request)
                
            except (OperationalError, DatabaseError) as e:
                print(f"Database connection failed (attempt {attempt + 1}/{max_retries}): {str(e)}")
                print(f"Error type: {type(e).__name__}")
                
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # exponential backoff
                else:
                    # بعد از آخرین تلاش ناموفق
                    print("All retry attempts failed")
                    return Response(
                        {
                            "error": "خطا در اتصال به پایگاه داده",
                            "detail": "لطفاً چند لحظه دیگر تلاش کنید",
                            "code": "database_connection_error"
                        },
                        status=status.HTTP_503_SERVICE_UNAVAILABLE
                    )
            except Exception as e:
                # برای سایر خطاها
                print(f"Unexpected error: {str(e)}")
                print(f"Error type: {type(e).__name__}")
                print("Traceback:")
                print(traceback.format_exc())
                
                return Response(
                    {
                        "error": "خطای سرور",
                        "detail": f"خطای غیرمنتظره رخ داده است: {str(e)}",
                        "code": "server_error",
                        "error_type": type(e).__name__
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

    def _test_database_connection(self):
        """تست اتصال به دیتابیس"""
        try:
            from django.db import connections
            connection = connections['default']
            if not connection.is_usable():
                connection.close()
            connection.ensure_connection()
            print("Database connection test passed")
        except Exception as e:
            print(f"Database connection test failed: {str(e)}")
            raise

    def _get_reservations(self, request):
        """منطق اصلی دریافت رزروها"""
        print("Starting to fetch reservations...")
        
        # ابتدا وضعیت پرداخت رزروهای در حال انتظار را بررسی و به روز کنیم
        print("Updating expired payments...")
        self.update_expired_payments(request.user)

        # زیرکوئری برای دریافت آخرین وضعیت کنسلی
        print("Creating cancellation subquery...")
        latest_cancellation_subquery = Subquery(
            UserCancellation.objects.filter(
                reservation=OuterRef('pk')
            ).order_by('-created_at').values('status')[:1]
        )

        # کوئری‌ست اصلی با annotate برای وضعیت کنسلی
        print("Building main queryset...")
        queryset = Reservationhotel.objects.filter(
            buyer=request.user
        ).select_related('buyer').prefetch_related(
            'reservation_rooms__room__hotel',
            'cancellations'
        ).annotate(
            latest_cancellation_status=latest_cancellation_subquery
        ).order_by('-created_at')

        print(f"Total reservations found: {queryset.count()}")

        # دریافت پارامترهای صفحه‌بندی
        page = request.query_params.get('p', 1)
        page_size = request.query_params.get('page_size', 18)
        print(f"Pagination parameters - page: {page}, page_size: {page_size}")

        # اعتبارسنجی page_size
        try:
            page_size = int(page_size)
            if page_size < 1:
                page_size = 18
            elif page_size > 100:
                page_size = 100
        except (TypeError, ValueError):
            page_size = 18

        # اعتبارسنجی page
        try:
            page = int(page)
            if page < 1:
                page = 1
        except (TypeError, ValueError):
            page = 1

        print(f"Final pagination - page: {page}, page_size: {page_size}")

        # پجینیشن با Django Paginator
        print("Creating paginator...")
        paginator = DjangoPaginator(queryset, page_size)
        
        try:
            reservations_page = paginator.page(page)
            print(f"Page {page} retrieved successfully")
        except PageNotAnInteger:
            print("Page not integer, using page 1")
            reservations_page = paginator.page(1)
        except EmptyPage:
            print("Empty page, using last page")
            reservations_page = paginator.page(paginator.num_pages)

        # سریالایز کردن دستی داده‌ها
        print("Serializing data...")
        data = []
        for i, reservation in enumerate(reservations_page):
            print(f"Processing reservation {i + 1}: {reservation.tracking_code}")
            
            hotel_name = self.get_hotel_name(reservation)
            cancellation_status = self.get_cancellation_status(reservation)
            formatted_created_at = self.format_created_at(reservation.created_at)

            # محاسبه تعداد مسافران هر اتاق
            room_guests = []
            for room in reservation.reservation_rooms.all():
                main_count = room.passengers.filter(is_primary=True).count()
                primary_count = room.passengers.filter(passenger_type='primary').count()
                extra_count = room.passengers.filter(passenger_type='extra').count()
                total_room_guests = max(main_count, primary_count) + extra_count
                room_guests.append(total_room_guests)

            data.append({
                "tracking_code": reservation.tracking_code,
                "hotel_name": hotel_name,
                "check_in_date": str(reservation.check_in_date),
                "check_out_date": str(reservation.check_out_date),
                "total_guests": room_guests,
                "payment_status": reservation.payment_status,
                "cancellation_status": cancellation_status.get('status') if isinstance(cancellation_status, dict) else cancellation_status,
                "cancellation_status_display": cancellation_status.get('status_display') if isinstance(cancellation_status, dict) else None,
                "created_at": formatted_created_at,
            })

        # ساختار پاسخ Paginator سفارشی
        response_data = {
            'count': paginator.count,
            'total_pages': paginator.num_pages,
            'current_page': reservations_page.number,
            'results': data
        }

        print(f"Successfully returning {len(data)} reservations")
        return Response(response_data, status=status.HTTP_200_OK)

    def update_expired_payments(self, user):
        """
        به روزرسانی وضعیت پرداخت رزروهایی که بیش از 20 دقیقه در حالت pending مانده‌اند
        """
        try:
            twenty_minutes_ago = timezone.now() - timedelta(minutes=20)
            print(f"Looking for expired payments before: {twenty_minutes_ago}")
            
            # پیدا کردن رزروهای در حال انتظار که بیش از 20 دقیقه گذشته ایجاد شده‌اند
            expired_reservations = Reservationhotel.objects.filter(
                buyer=user,
                payment_status='pending',
                created_at__lte=twenty_minutes_ago
            )
            
            expired_count = expired_reservations.count()
            print(f"Found {expired_count} expired reservations")
            
            # به روزرسانی وضعیت به 'failed'
            updated_count = expired_reservations.update(payment_status='failed')
            
            if updated_count > 0:
                print(f"Updated {updated_count} expired reservations to 'failed' status")
            else:
                print("No expired reservations to update")
                
        except Exception as e:
            print(f"Error in update_expired_payments: {str(e)}")
            print(traceback.format_exc())

    def get_hotel_name(self, reservation):
        """استخراج نام هتل از رزرو"""
        try:
            first_room = reservation.reservation_rooms.first()
            if first_room and first_room.room and first_room.room.hotel:
                hotel_name = first_room.room.hotel.name
                print(f"Hotel name found: {hotel_name}")
                return hotel_name
            print("Hotel name not found")
            return "نامشخص"
        except Exception as e:
            print(f"Error getting hotel name: {str(e)}")
            return "نامشخص"

    def get_cancellation_status(self, reservation):
        """
        محاسبه وضعیت کنسلی برای یک رزرو
        """
        try:
            # استفاده از فیلد annotate شده
            if hasattr(reservation, 'latest_cancellation_status'):
                latest_status = reservation.latest_cancellation_status
                print(f"Latest cancellation status from annotation: {latest_status}")
                # بازگرداندن وضعیت به صورت رشته و نمایش فارسی
                if latest_status == 'approved':
                    return {'status': 'approved', 'status_display': 'تأیید شده'}
                elif latest_status == 'rejected':
                    return {'status': 'rejected', 'status_display': 'عدم تأیید'}
                elif latest_status == 'pending':
                    return {'status': 'pending', 'status_display': 'در انتظار بررسی'}
            
            # fallback: بررسی از طریق relation در صورت عدم وجود annotate
            latest_cancellation = reservation.cancellations.order_by('-created_at').first()
            if latest_cancellation:
                print(f"Latest cancellation from relation: {latest_cancellation.status}")
                status_val = getattr(latest_cancellation, 'status', None)
                if status_val == 'approved':
                    return {'status': 'approved', 'status_display': 'تأیید شده'}
                elif status_val == 'rejected':
                    return {'status': 'rejected', 'status_display': 'عدم تأیید'}
                elif status_val == 'pending':
                    return {'status': 'pending', 'status_display': 'در انتظار بررسی'}
            
            print("No cancellation found")
            return {'status': None, 'status_display': None}
        except Exception as e:
            print(f"Error getting cancellation status: {str(e)}")
            return {'status': None, 'status_display': None}

    def format_created_at(self, created_at):
        """فرمت‌دهی تاریخ ایجاد به صورت جلالی"""
        if not created_at:
            print("created_at is None")
            return None
        
        try:
            print(f"Original created_at: {created_at}, type: {type(created_at)}")
            
            # از آنجایی که created_at از نوع jDateTimeField است، مستقیماً از آن استفاده می‌کنیم
            if hasattr(created_at, 'strftime'):
                formatted = created_at.strftime('%Y/%m/%d %H:%M')
                print(f"Formatted created_at: {formatted}")
                return formatted
            else:
                # اگر رشته است یا فرمت دیگری دارد
                formatted = str(created_at)
                print(f"Created_at as string: {formatted}")
                return formatted
                
        except Exception as e:
            # در صورت بروز خطا، تاریخ اصلی را برگردان
            print(f"Error formatting created_at: {str(e)}")
            print(traceback.format_exc())
            return str(created_at) if created_at else None
        



# ای پی ای دلایل کنسلی 
class CancellationReasonListAPIView(APIView):
    """
    API برای دریافت لیست دلایل کنسلی
    """
    permission_classes = [AllowAny]  # هر کاربری می‌تواند مشاهده کند

    @swagger_auto_schema(
        operation_summary="دریافت لیست دلایل کنسلی",
        operation_description="""
        این API لیست تمام دلایل کنسلی رزرو را برمی‌گرداند.
        هر دلیل شامل موارد زیر است:
        - id: شناسه دلیل کنسلی
        - title: عنوان دلیل کنسلی
        """,
        responses={
            200: openapi.Response(
                description="لیست دلایل کنسلی با موفقیت بازگشت داده شد",
                examples={
                    "application/json": {
                        "cancellation_reasons": [
                            {"id": 1, "title": "لغو توسط کاربر"},
                            {"id": 2, "title": "عدم حضور مهمان"}
                        ]
                    }
                }
            )
        },
        tags=["reservedashboard-api"]
    )
    def get(self, request):
        reasons = CancellationReason.objects.all()
        data = [{"id": r.id, "title": r.title} for r in reasons]
        return Response({"cancellation_reasons": data}, status=status.HTTP_200_OK)
    
    
    
    
    
#ای پی ای کنسلی کاربر 
class UserCancellationCreateAPIView(APIView):
    """
    API برای ثبت درخواست کنسلی رزرو توسط کاربر
    کاربر فقط می‌تواند رزروهای تأیید شده و پرداخت شده خود را کنسل کند.
    وضعیت اولیه درخواست: pending (در انتظار بررسی ادمین)
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="ثبت درخواست کنسلی رزرو",
        operation_description="""
        کاربر فقط می‌تواند رزروهای **تأیید شده و پرداخت شده** خود را کنسل کند.
        - وضعیت اولیه: `pending` (در انتظار بررسی)
        - فقط یک درخواست در حال بررسی یا تأیید شده برای هر رزرو مجاز است.
        - پس از تایید ادمین، جریمه کنسلی محاسبه و مبلغ باقیمانده به کیف پول برگشت داده می‌شود.
        """,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['tracking_code', 'reasons'],
            properties={
                'tracking_code': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    description='کد پیگیری رزرو'
                ),
                'reasons': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_INTEGER),
                    description='لیست شناسه دلایل کنسلی (حداقل یک دلیل)'
                ),
                'description': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    description='توضیحات اختیاری کاربر'
                )
            }
        ),
        responses={
            201: openapi.Response(
                description="درخواست با موفقیت ثبت شد",
                examples={
                    "application/json": {
                        "id": 1,
                        "tracking_code": "RES-123",
                        "status": "pending",
                        "status_display": "در انتظار بررسی",
                        "reasons": ["تغییر برنامه", "مشکل مالی"],
                        "description": "سفر لغو شد",
                        "created_at": "1403/08/27 ساعت 14:30"
                    }
                }
            ),
            400: openapi.Response(
                description="خطا در ورودی یا قوانین کنسلی",
                examples={
                    "application/json": {
                        "detail": "درخواست کنسلی برای این رزرو قبلاً ثبت شده."
                    }
                }
            ),
            404: openapi.Response(
                description="رزرو یافت نشد",
                examples={
                    "application/json": {
                        "detail": "رزرو قابل کنسلی یافت نشد یا متعلق به شما نیست."
                    }
                }
            )
        },
        tags=["reservedashboard-api"]
    )
    def post(self, request):
        user = request.user
        tracking_code = request.data.get('tracking_code')
        reasons_ids = request.data.get('reasons', [])
        description = request.data.get('description', '')

        # --- اعتبارسنجی ورودی‌ها ---
        if not tracking_code:
            return Response(
                {"detail": "tracking_code الزامی است."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not reasons_ids or not isinstance(reasons_ids, list) or len(reasons_ids) == 0:
            return Response(
                {"detail": "حداقل یک دلیل کنسلی باید انتخاب شود."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # --- پیدا کردن رزرو ---
        try:
            reservation = Reservationhotel.objects.get(
                tracking_code=tracking_code,
                buyer=user,
                capacity_status='confirmed',
                payment_status='paid'
            )
        except Reservationhotel.DoesNotExist:
            return Response(
                {"detail": "رزرو قابل کنسلی یافت نشد یا متعلق به شما نیست. فقط رزروهای تأیید شده و پرداخت شده قابل کنسل هستند."},
                status=status.HTTP_404_NOT_FOUND
            )

        # --- اعتبارسنجی دلایل کنسلی ---
        reasons = CancellationReason.objects.filter(id__in=reasons_ids)
        if reasons.count() != len(reasons_ids):
            return Response(
                {"detail": "یک یا چند دلیل نامعتبر هستند."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # --- بررسی درخواست کنسلی قبلی ---
        existing_cancellation = UserCancellation.objects.filter(
            reservation=reservation,
            status__in=[UserCancellation.Status.PENDING, UserCancellation.Status.APPROVED]
        ).first()
        
        if existing_cancellation:
            return Response(
                {
                    "detail": f"درخواست کنسلی برای این رزرو قبلاً با وضعیت '{existing_cancellation.get_status_display()}' ثبت شده است."
                }, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # --- ایجاد درخواست کنسلی جدید ---
        cancellation = UserCancellation.objects.create(
            reservation=reservation,
            description=description or None,
            status=UserCancellation.Status.PENDING
        )
        cancellation.reasons.set(reasons)

        # --- آماده‌سازی پاسخ ---
        created_at_jalali = None
        if cancellation.created_at:
            import jdatetime
            dt = jdatetime.datetime.fromgregorian(datetime=cancellation.created_at)
            created_at_jalali = dt.strftime('%Y/%m/%d ساعت %H:%M')

        return Response({
            "id": cancellation.id,
            "tracking_code": reservation.tracking_code,
            "status": cancellation.status,
            "status_display": cancellation.get_status_display(),
            "reasons": [r.title for r in reasons],
            "description": description or "",
            "created_at": created_at_jalali,
            "message": "درخواست کنسلی شما با موفقیت ثبت شد و در انتظار بررسی ادمین است."
        }, status=status.HTTP_201_CREATED)




# ای پی ای امضا در فاکتور 
class ReservationInvoiceSettingsAPIView(APIView):
    """
    API برای دریافت تنظیمات فاکتور رزرو
    شامل عنوان فاکتور، شماره تماس‌ها، آدرس پستی و لینک کامل عکس امضا با دامنه zarvantrip.com
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="دریافت تنظیمات فاکتور رزرو",
        operation_description="""
        این API تنظیمات فاکتور رزرو را برمی‌گرداند که شامل:
        - عنوان فاکتور
        - شماره تماس ۱
        - شماره تماس ۲
        - آدرس پستی
        - لینک کامل عکس امضا (با دامنه اصلی: `https://zarvantrip.com`)

        **نکته مهم**: لینک عکس همیشه با دامنه اصلی `zarvantrip.com` برگردانده می‌شود.
        اگر تنظیماتی وجود نداشته باشد، مقدار `null` برمی‌گردد.
        """,
        responses={
            200: openapi.Response(
                description="تنظیمات فاکتور با موفقیت بازگشت داده شد",
                examples={
                    "application/json": {
                        "invoice_settings": {
                            "title": "فاکتور رسمی رزرو هتل",
                            "contact_number_1": "021-12345678",
                            "contact_number_2": "0912-1234567",
                            "postal_address": "تهران، خیابان آزادی، پلاک ۱۲۳",
                            "signature_image": "https://zarvantrip.com/media/signatures/signature.png"
                        }
                    }
                }
            ),
            404: openapi.Response(
                description="تنظیمات فاکتور یافت نشد",
                examples={
                    "application/json": {
                        "invoice_settings": None,
                        "detail": "تنظیمات فاکتور رزرو تعریف نشده است."
                    }
                }
            )
        },
        tags=["reservedashboard-api"]
    )
    def get(self, request):
        settings_obj = ReservationInvoiceSettings.objects.first()

        if not settings_obj:
            return Response(
                {
                    "invoice_settings": None,
                    "detail": "تنظیمات فاکتور رزرو تعریف نشده است."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        # ساخت لینک کامل با دامنه اصلی
        signature_url = None
        if settings_obj.signature_image:
            base_url = "https://zarvantrip.com"
            signature_url = f"{base_url}{settings_obj.signature_image.url}"

        data = {
            "title": settings_obj.title,
            "contact_number_1": settings_obj.contact_number_1,
            "contact_number_2": settings_obj.contact_number_2,
            "postal_address": settings_obj.postal_address,
            "signature_image": signature_url
        }

        return Response({"invoice_settings": data}, status=status.HTTP_200_OK)




# ==============================================================================
# API فاکتور نهایی و واچر رزرو (شامل عکس کامل هتل و هماهنگ با فرانت‌اند)
# ==============================================================================
class ReservationInvoiceDetailAPIView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="دریافت اطلاعات فاکتور و واچر رزرو",
        operation_description="این API تمام اطلاعات لازم برای نمایش فاکتور و واچر رزرو (شامل عکس هتل) را بر اساس کد پیگیری برمی‌گرداند.",
        manual_parameters=[
            openapi.Parameter(
                'tracking_code',
                openapi.IN_PATH,
                description="کد پیگیری رزرو (مثلاً: sfa1234567890)",
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        responses={
            200: "فاکتور با موفقیت بازگشت داده شد",
            404: "رزرو یا هتل یافت نشد"
        },
        tags=["reservedashboard-api"]
    )
    def get(self, request, tracking_code):
        # دریافت رزرو با تطابق حروف کوچک و بزرگ
        reservation = get_object_or_404(Reservationhotel, tracking_code__iexact=str(tracking_code).strip())

        # دریافت هتل مرتبط
        hotel = reservation.get_hotel()
        if not hotel:
            first_room = reservation.reservation_rooms.select_related('room__hotel').first()
            if first_room and first_room.room and first_room.room.hotel:
                hotel = first_room.room.hotel
            else:
                return Response(
                    {"detail": "هتل مرتبط با این رزرو یافت نشد."},
                    status=status.HTTP_404_NOT_FOUND
                )

        # ساخت لینک کامل و معتبر تصویر اصلی هتل برای نمایش در واچر
        site_url = getattr(settings, "SITE_URL", "https://zarvantrip.com")
        image_url = ""
        if hotel.main_image and hasattr(hotel.main_image, 'url'):
            image_url = f"{site_url}{hotel.main_image.url}"

        # تبدیل تاریخ‌های شمسی به رشته استاندارد
        try:
            created_iso = reservation.created_at.strftime('%Y-%m-%dT%H:%M:%S') if reservation.created_at else None
        except Exception:
            created_iso = str(reservation.created_at) if reservation.created_at else None

        try:
            check_in_iso = reservation.check_in_date.strftime('%Y-%m-%dT%H:%M:%S') if reservation.check_in_date else None
        except Exception:
            check_in_iso = str(reservation.check_in_date) if reservation.check_in_date else None

        try:
            check_out_iso = reservation.check_out_date.strftime('%Y-%m-%dT%H:%M:%S') if reservation.check_out_date else None
        except Exception:
            check_out_iso = str(reservation.check_out_date) if reservation.check_out_date else None

        # لیست اتاق‌ها
        rooms_data = []
        for res_room in reservation.reservation_rooms.select_related('room').all():
            room = res_room.room
            services = [service.title for service in room.services.all()] if hasattr(room, 'services') else []

            rooms_data.append({
                "room_name": room.title,
                "nights": reservation.nights_count,
                "services": services,
                "half_day_in": res_room.half_day_in_selected,
                "half_day_out": res_room.half_day_out_selected,
            })

        # لیست مسافران
        passengers_data = []
        for passenger in ReservationRoomPassenger.objects.filter(reservation_room__reservation=reservation):
            type_map = {
                'primary': 'اصلی',
                'extra': 'اضافه',
                'child': 'کودک',
                'infant': 'نوزاد'
            }
            p_type = type_map.get(passenger.passenger_type, 'سایر')
            passengers_data.append({
                "name": f"{passenger.first_name} {passenger.last_name}".strip(),
                "type": p_type
            })

        # ساختار نهایی خروجی همراه با لینک عکس هتل در تمام کلیدهای احتمالی فرانت‌اند
        data = {
            "reservation": {
                "reserver_name": f"{reservation.reserver_first_name} {reservation.reserver_last_name}".strip(),
                "reserver_phone": reservation.reserver_phone_number,
                "tracking_code": reservation.tracking_code,
                "created_at": created_iso,
                "check_in_date": check_in_iso,
                "check_out_date": check_out_iso,
                "hotel": {
                    "name": hotel.name,
                    "address": hotel.address,
                    "image": image_url,        # 👈 فیلد عکس برای واچر
                    "main_image": image_url,   # 👈 برای پشتیبانی کامل
                },
                "hotel_image": image_url,      # 👈 در سطح اول آبجکت
                "hotel_slug": getattr(hotel, 'slug', '') or "",
                "rooms": rooms_data,
                "passengers": passengers_data,
                "hotel_rules": hotel.rules or "قوانین ثبت نشده است."
            }
        }

        return Response(data, status=status.HTTP_200_OK)
    
    
    
    #ای پی ای مشخصات هتل برای چت بات 
class HotelChatBotListView(APIView):
    permission_classes = (AllowAny,)

    @swagger_auto_schema(
        operation_summary="لیست تمام هتل‌ها برای چت‌بات",
        operation_description="""
        این API لیست تمام هتل‌های موجود در سایت را با نام و لینک اصلی برمی‌گرداند.

        **لینک خروجی**: `https://zarvantrip.com/best-hotels/{slug}/`

        مناسب برای:
        - نمایش لیست هتل‌ها در چت‌بات
        - دکمه‌های پیشنهادی
        - جستجوی سریع
        """,
        tags=['chat-bot'],
        responses={
            200: openapi.Response(
                description="لیست هتل‌ها با موفقیت برگردانده شد",
                schema=HotelLinkSerializer(many=True),
                examples={
                    "application/json": [
                        {
                            "name": "هتل عباسی",
                            "url": "https://zarvantrip.com/best-hotels/hotel-abbasi/"
                        },
                        {
                            "name": "هتل پارسیان کوثر",
                            "url": "https://zarvantrip.com/best-hotels/hotel-parsian-kowsar/"
                        }
                    ]
                }
            )
        }
    )
    def get(self, request):
        hotels = Hotel.objects.all().order_by('name')
        serializer = HotelLinkSerializer(hotels, many=True)
        return Response(serializer.data)