from collections import defaultdict
from itertools import product
from datetime import datetime, timedelta
import logging
import jdatetime
from rest_framework.views import APIView
from rest_framework.generics import RetrieveUpdateDestroyAPIView
from rest_framework.exceptions import PermissionDenied
from safarname24.pagination import FacilitiesPaginator, RoomFacilitiesPaginator
from .utils import Round
from rest_framework.generics import CreateAPIView
from rest_framework.generics import ListCreateAPIView
from rest_framework import generics
from itertools import combinations

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
from .utils import Round  # فرض بر این است که Round در utils تعریف شده
from datetime import datetime



#ای پی ای لیست هتل ها 
class HotelListView(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = HotelListSerializer

    def get_queryset(self):
        city_or_hotel = self.request.query_params.get('q')
        passenger_count = self.request.query_params.get('passenger_count')
        type = self.request.query_params.get('type')
        stars = self.request.query_params.get('stars')
        is_special_offer = self.request.query_params.get('special_offer')
        has_discount = self.request.query_params.get('discount')
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')

        try:
            start_date = datetime.strptime(self.request.query_params.get('start_date'), "%Y-%m-%d").date()
        except:
            raise ValidationError({'start_date': 'لطفا تاریخ ورود را به درستی وارد نمایید'})

        try:
            end_date = datetime.strptime(self.request.query_params.get('end_date'), "%Y-%m-%d").date()
        except:
            raise ValidationError({'end_date': 'لطفا تاریخ خروج را به درستی وارد نمایید'})

        if not city_or_hotel:
            raise ValidationError({'q': 'نام هتل یا شهر الزامی است'})
        if not passenger_count:
            raise ValidationError({'passenger_count': 'تعداد مسافران الزامی است'})
        if start_date < timezone.localdate():
            raise ValidationError({'start_date': 'تاریخ ورود نمی‌تواند قبل از امروز باشد.'})
        if end_date < start_date:
            raise ValidationError({'end_date': 'تاریخ خروج نمی‌تواند از تاریخ ورود کمتر باشد.'})

        available_room_dates = RoomDate.objects.select_related('room')\
            .annotate(
                occupied_count=RoomDate.get_occupied_statuses_count_expression(),
                discount_count=RoomDate.get_discount_count_expression(),
                original_price=F('price'),
                discounted_price=RoomDate.get_discounted_price_expression(),
            ).filter(
                date__gte=start_date,
                date__lte=end_date,
                room__capacity=passenger_count,
                room__count__gt=F('occupied_count'),
            )

        matching_rooms_data = available_room_dates.values('room_id').annotate(
            hotel_id=F('room__hotel_id'),
            days_count=Count('date', distinct=True),
            original_total_price=Sum('original_price'),
            discounted_total_price=Sum('discounted_price'),
            occupied_count=F('occupied_count'),
            discount_count=F('discount_count'),
        ).filter(
            days_count=(end_date - start_date).days + 1,
        )

        if has_discount:
            matching_rooms_data = matching_rooms_data.filter(
                discounted_total_price__lt=F('original_total_price')
            )

        if min_price:
            matching_rooms_data = matching_rooms_data.filter(
                discounted_total_price__gte=min_price,
            )
        if max_price:
            matching_rooms_data = matching_rooms_data.filter(
                discounted_total_price__lte=max_price,
            )

        self.hotel_price_map = defaultdict(list)

        for room_data in matching_rooms_data:
            hotel_id = room_data['hotel_id']
            total_price = room_data['discounted_total_price'] \
                if room_data['occupied_count'] < room_data['discount_count'] \
                else room_data['original_total_price']

            self.hotel_price_map[hotel_id].append({
                'total_price': total_price,
                'original_total_price': room_data['original_total_price'],
            })

        self.hotel_price_map = dict(self.hotel_price_map)

        queryset = Hotel.objects.prefetch_related('rooms')\
            .select_related('city', 'city__province', 'type')\
            .prefetch_related('comments__points')\
            .annotate(
                rating=Round(
                    Avg('comments__points__point', filter=Q(comments__is_approved=True)),
                    precision=1
                )
            ).filter(
                Q(city__name__contains=city_or_hotel) | 
                Q(city__slug__icontains=city_or_hotel) | 
                Q(name__contains=city_or_hotel) |
                Q(slug__icontains=city_or_hotel),
                rooms__id__in=[item['room_id'] for item in matching_rooms_data],
            ).distinct()

        if type:
            try:
                type_ids = [int(id) for id in type.split(',') if id.strip().isdigit()]
                queryset = queryset.filter(type__id__in=type_ids)
            except ValueError:
                raise ValidationError({'type': 'فرمت نوع هتل صحیح نیست.'})

        if stars:
            try:
                star_values = [int(star) for star in stars.split(',') if star.strip().isdigit()]
                queryset = queryset.filter(stars__in=star_values)
            except ValueError:
                raise ValidationError({'stars': 'فرمت تعداد ستاره هتل صحیح نیست.'})

        if is_special_offer in ['true', 'True', '1']:
            queryset = queryset.filter(is_special_offer=True)
        elif is_special_offer in ['false', 'False', '0']:
            queryset = queryset.filter(is_special_offer=False)

        queryset = queryset.order_by('id')
        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        hotel_price_map = getattr(self, 'hotel_price_map', {})

        if self.request.user.is_authenticated:
            context['hotel_min_price_map'] = {
                hotel_id: min(items, key=lambda x: x['total_price'])
                for hotel_id, items in hotel_price_map.items()
            }
        else:
            context['hotel_min_price_map'] = {}

        return context

    @swagger_auto_schema(
        operation_summary="لیست هتل‌ها",
        operation_description="این API لیستی از هتل‌ها را بر اساس فیلترهای مختلف مانند شهر یا نام هتل، تعداد مسافر، تاریخ ورود و خروج، نوع هتل، تعداد ستاره، بازه قیمتی، تخفیف‌دار بودن و ویژه بودن باز می‌گرداند.",
        tags=['hotel'],
        manual_parameters=[
            openapi.Parameter('q', openapi.IN_QUERY, description="نام یا اسلاگ هتل یا شهر", type=openapi.TYPE_STRING, required=True),
            openapi.Parameter('passenger_count', openapi.IN_QUERY, description="تعداد مسافران", type=openapi.TYPE_INTEGER, required=True),
            openapi.Parameter('start_date', openapi.IN_QUERY, description="تاریخ ورود (YYYY-MM-DD)", type=openapi.TYPE_STRING, required=True),
            openapi.Parameter('end_date', openapi.IN_QUERY, description="تاریخ خروج (YYYY-MM-DD)", type=openapi.TYPE_STRING, required=True),
            openapi.Parameter('type', openapi.IN_QUERY, description="شناسه نوع هتل‌ها به صورت کاما جدا (مثلاً 1,2)", type=openapi.TYPE_STRING),
            openapi.Parameter('stars', openapi.IN_QUERY, description="تعداد ستاره هتل‌ها به صورت کاما جدا (مثلاً 3,4,5)", type=openapi.TYPE_STRING),
            openapi.Parameter('min_price', openapi.IN_QUERY, description="کمترین قیمت کل", type=openapi.TYPE_INTEGER),
            openapi.Parameter('max_price', openapi.IN_QUERY, description="بیشترین قیمت کل", type=openapi.TYPE_INTEGER),
            openapi.Parameter('special_offer', openapi.IN_QUERY, description="آیا ویژه باشد؟", type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('discount', openapi.IN_QUERY, description="آیا شامل تخفیف باشد؟", type=openapi.TYPE_BOOLEAN),
        ]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    
        
class CityListView(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = CitySerializer
    pagination_class = None  # اگر پجینیشن نمی‌خواهی

    def get_queryset(self):
        queryset = City.objects.select_related('province')

        if q := self.request.query_params.get('q'):
            queryset = queryset.filter(
                Q(name__icontains=q) | 
                Q(slug__icontains=q)
            )

        return queryset
    
    @swagger_auto_schema(
        operation_summary="دریافت لیست شهرها",
        operation_description="این API لیستی از شهرها را باز می‌گرداند و امکان جستجو بر اساس نام یا slug شهر وجود دارد.",
        manual_parameters=[
            openapi.Parameter(
                'q',
                openapi.IN_QUERY,
                description="نام یا slug شهر برای جستجو (فیلتر بر اساس q)",
                type=openapi.TYPE_STRING,
                required=False,
            ),
        ],
        responses={},  # ✅ حذف Response samples
        tags=['hotel']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    




# ای پی ای لیست شهر های مربوط یه صفحه اصلی 
class HomePageCityListView(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = CitySerializer
    pagination_class = None  # اگر پجینیشن نمی‌خوای

    def get_queryset(self):
        return City.objects.filter(show_in_homepage=True).select_related('province')

    @swagger_auto_schema(
        operation_summary="دریافت لیست شهرهای مخصوص صفحه اصلی",
        operation_description="این API فقط شهرهایی را باز می‌گرداند که گزینه 'نمایش در صفحه اصلی' آن‌ها فعال است.",
        responses={},  # حذف Response samples
        tags=["hotel-home"]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    
    
    
#ای پی ای نوع اقامتگاه
class HotelTypeListView(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = HotelTypeSerializer
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
    import sys
    def logger_fallback(*args, **kwargs):
        print(*args, file=sys.stderr)
    logger = type('Logger', (), {'info': logger_fallback, 'warning': logger_fallback})()

class HotelRoomsView(generics.RetrieveAPIView):
    permission_classes = (AllowAny,)
    serializer_class = RoomSerializer
    queryset = Hotel.objects.all()
    lookup_field = 'slug'
    lookup_url_kwarg = 'slug'

    @swagger_auto_schema(
        operation_summary="دریافت لیست اتاق‌های هتل به همراه قیمت و تقویم قیمتی",
        operation_description=(
            "این API لیست اتاق‌های هتل مشخص شده توسط slug را به همراه قیمت‌های روزانه، تخفیف‌ها، و وضعیت دسترسی باز می‌گرداند. "
            "در حالت بدون فیلتر، فقط اتاق‌هایی که حداقل یک بازه قیمتی معتبر دارند نمایش داده می‌شوند، همراه با تقویم قیمتی برای بازه پیش‌فرض (امروز تا ۳۰ روز بعد). "
            "در حالت فیلترشده، همه اتاق‌ها یا پک‌هایی که موجودی دارند نمایش داده می‌شوند، حتی اگر برخی روزها بسته یا تکمیل باشند. بازه رزرو نمی‌تواند بیشتر از ۳۰ روز باشد.\n\n"
            "پارامترهای ورودی:\n"
            "- slug (اجباری): شناسه slug هتل\n"
            "- start_date (اختیاری): تاریخ شروع به فرمت yyyy-mm-dd\n"
            "- end_date (اختیاری): تاریخ پایان به فرمت yyyy-mm-dd\n"
            "- passenger_count (اختیاری): تعداد مسافران، پیش‌فرض ۱، حداکثر ۸\n"
            "- room_count (اختیاری): تعداد اتاق‌ها، پیش‌فرض ۱، حداکثر ۳\n\n"
            "خروجی:\n"
            "- بدون فیلتر: لیست اتاق‌هایی که حداقل یک بازه قیمتی دارند با تقویم قیمتی\n"
            "- با فیلتر: لیست اتاق‌ها یا پک‌های اتاق با قیمت و تقویم قیمتی برای تمام روزها\n"
            "- در صورت عدم وجود اتاق یا پک: پیام با جزئیات روزهای غیرقابل دسترس"
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
                name='passenger_count', in_=openapi.IN_QUERY, description='تعداد مسافران، پیش‌فرض ۱، حداکثر ۸', type=openapi.TYPE_INTEGER, required=False
            ),
            openapi.Parameter(
                name='room_count', in_=openapi.IN_QUERY, description='تعداد اتاق‌ها، پیش‌فرض ۱، حداکثر ۳', type=openapi.TYPE_INTEGER, required=False
            ),
        ],
        responses={
            200: "لیست اتاق‌ها یا پک‌های اتاق با یا بدون فیلتر",
            400: "خطا در پارامترهای ورودی",
            404: "هیچ اتاق یا پکی با موجودی یافت نشد"
        }
    )
    def get(self, request, *args, **kwargs):
        from itertools import combinations
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        passenger_count = request.query_params.get('passenger_count')
        room_count = request.query_params.get('room_count')

        hotel = self.get_object()
        logger.info(f"Processing request for hotel {hotel.slug}")

        has_filters = any([start_date, end_date, passenger_count, room_count])

        persian_days = ['شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنجشنبه', 'جمعه']
        persian_months = ['فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور', 'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند']
        default_user_level = "میهمان"

        if not has_filters:
            # حالت بدون فیلتر: فقط اتاق‌هایی با حداقل یک داده قیمتی
            start_date_obj = jdatetime.date.today()
            end_date_obj = start_date_obj + jdatetime.timedelta(days=30)
            passenger_count_int = 1  # پیش‌فرض برای محاسبه قیمت
            room_count_int = 1
            rooms_qs = hotel.rooms.filter(date_prices__isnull=False, inventory__gte=1).distinct()
            logger.info(f"No filters applied, found {rooms_qs.count()} rooms with price data, using default range {start_date_obj} to {end_date_obj}")

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
                for date in date_range:
                    price_data = room.date_prices.filter(
                        start_date__lte=date,
                        end_date__gte=date
                    ).order_by('-id').select_related('user_level').first()

                    closed_date = closed.filter(date=date).first()
                    status = "open"

                    if not price_data:
                        status = "close"
                    elif closed_date:
                        status = "complate"
                    elif room.inventory == 0:
                        status = "close"

                    discount_amount = 0
                    if price_data and price_data.discount_type != 'none' and price_data.discount_date and price_data.discount_date >= date:
                        if price_data.discount_type == 'percentage':
                            discount_amount = price_data.price * price_data.discount_value / 100
                        elif price_data.discount_type == 'fixed':
                            discount_amount = price_data.discount_value

                    price_after_discount = max(price_data.price - discount_amount, 0) if price_data else None

                    price_calendar.append({
                        "date": date.strftime('%Y/%m/%d'),
                        "month": persian_months[date.month - 1],
                        "day": persian_days[date.weekday()],
                        "status": status,
                        "price": {
                            "price": price_data.price if price_data else None,
                            "price_after_discount": price_after_discount,
                            "discount_percentage": price_data.discount_value if price_data and price_data.discount_type == 'percentage' else None,
                            "discount_amount": price_data.discount_value if price_data and price_data.discount_type == 'fixed' else None,
                            "discount_date": price_data.discount_date.strftime('%Y/%m/%d') if price_data and price_data.discount_date else None,
                            "is_fixed_discount_one_time": price_data.is_fixed_discount_one_time if price_data else False,
                            "user_level": price_data.user_level.title if price_data and price_data.user_level else default_user_level,
                            "extra_capacity_price": price_data.extra_passenger_price if price_data else 0,
                            "tourist_price": price_data.foreign_passenger_price or 0 if price_data else 0
                        } if status == "open" else None
                    })

                first_price_data = room.date_prices.filter(
                    start_date__lte=start_date_obj,
                    end_date__gte=start_date_obj
                ).order_by('-id').select_related('user_level').first()

                if not first_price_data:
                    logger.info(f"Room {room.id} skipped: No valid price data in default range")
                    continue

                discount_amount = 0
                if first_price_data.discount_type != 'none':
                    if first_price_data.discount_date and first_price_data.discount_date >= start_date_obj:
                        if first_price_data.discount_type == 'percentage':
                            discount_amount = first_price_data.price * first_price_data.discount_value / 100
                        elif first_price_data.discount_type == 'fixed':
                            discount_amount = first_price_data.discount_value
                price_after_discount_first = max(first_price_data.price - discount_amount, 0)

                total_price = sum(
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
                        "price": first_price_data.price,
                        "price_after_discount": price_after_discount_first,
                        "total_price": total_price,
                        "discount_percentage": first_price_data.discount_value if first_price_data.discount_type == 'percentage' else None,
                        "discount_amount": first_price_data.discount_value if first_price_data.discount_type == 'fixed' else None,
                        "discount_date": first_price_data.discount_date.strftime('%Y/%m/%d') if first_price_data.discount_date else None,
                        "is_fixed_discount_one_time": first_price_data.is_fixed_discount_one_time,
                        "user_level": first_price_data.user_level.title if first_price_data.user_level else default_user_level,
                        "extra_capacity_price": first_price_data.extra_passenger_price,
                        "tourist_price": first_price_data.foreign_passenger_price or 0
                    },
                    "night_count": night_count,
                    "price_calendar": price_calendar
                }

            room_data = list(room_dict.values())

            if not room_data:
                logger.warning(f"No rooms with price data found for hotel {hotel.slug}")
                return Response({
                    'detail': 'هیچ اتاقی با داده قیمتی برای این هتل یافت نشد.',
                    'rooms': [],
                    'price_calendar': [
                        {"date": (start_date_obj + jdatetime.timedelta(days=i)).strftime('%Y/%m/%d'), "status": "close"}
                        for i in range((end_date_obj - start_date_obj).days)
                    ]
                }, status=200)

            return Response(room_data)

        # حالت فیلترشده
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

        try:
            passenger_count_int = int(passenger_count) if passenger_count else 1
            if passenger_count_int > 8:
                return Response({'detail': 'تعداد مسافران نمی‌تواند بیشتر از ۸ نفر باشد.'}, status=400)
            room_count_int = int(room_count) if room_count else 1
            room_count_int = min(max(1, room_count_int), 3)
        except Exception:
            return Response({'detail': 'پارامترهای passenger_count و room_count باید عدد صحیح باشند.'}, status=400)

        logger.info(f"Applying filters: passenger_count={passenger_count_int}, room_count={room_count_int}, start_date={start_date}, end_date={end_date}")

        rooms_qs = hotel.rooms.filter(
            date_prices__start_date__lte=end_date_obj,
            date_prices__end_date__gte=start_date_obj,
            inventory__gte=1,
        ).distinct()
        logger.info(f"Found {rooms_qs.count()} rooms with inventory >= 1 and valid price data")

        date_range = [start_date_obj + jdatetime.timedelta(days=i) for i in range((end_date_obj - start_date_obj).days)]
        night_count = (end_date_obj - start_date_obj).days

        room_data = []
        room_dict = {}

        for room in rooms_qs:
            if room.inventory == 0:
                logger.info(f"Room {room.id} skipped: inventory=0")
                continue

            room_services = ", ".join([service.title for service in room.services.all()]) or "خدمات ندارد"
            closed = ClosedDate.objects.filter(
                room_date__room=room,
                date__range=(start_date_obj, end_date_obj)
            ).select_related('room_date')

            price_calendar = []
            for date in date_range:
                price_data = room.date_prices.filter(
                    start_date__lte=date,
                    end_date__gte=date
                ).order_by('-id').select_related('user_level').first()

                closed_date = closed.filter(date=date).first()
                status = "open"

                if not price_data:
                    status = "close"
                    logger.debug(f"Room {room.id} on {date}: No price data")
                elif closed_date:
                    status = "complate"
                    logger.debug(f"Room {room.id} on {date}: Closed")
                elif room.inventory == 0:
                    status = "close"
                    logger.debug(f"Room {room.id} on {date}: Inventory=0")

                discount_amount = 0
                if price_data and price_data.discount_type != 'none' and price_data.discount_date and price_data.discount_date >= date:
                    if price_data.discount_type == 'percentage':
                        discount_amount = price_data.price * price_data.discount_value / 100
                    elif price_data.discount_type == 'fixed':
                        discount_amount = price_data.discount_value

                price_after_discount = max(price_data.price - discount_amount, 0) if price_data else None

                price_calendar.append({
                    "date": date.strftime('%Y/%m/%d'),
                    "month": persian_months[date.month - 1],
                    "day": persian_days[date.weekday()],
                    "status": status,
                    "price": {
                        "price": price_data.price if price_data else None,
                        "price_after_discount": price_after_discount,
                        "discount_percentage": price_data.discount_value if price_data and price_data.discount_type == 'percentage' else None,
                        "discount_amount": price_data.discount_value if price_data and price_data.discount_type == 'fixed' else None,
                        "discount_date": price_data.discount_date.strftime('%Y/%m/%d') if price_data and price_data.discount_date else None,
                        "is_fixed_discount_one_time": price_data.is_fixed_discount_one_time if price_data else False,
                        "user_level": price_data.user_level.title if price_data and price_data.user_level else default_user_level,
                        "extra_capacity_price": price_data.extra_passenger_price if price_data else 0,
                        "tourist_price": price_data.foreign_passenger_price or 0 if price_data else 0
                    } if status == "open" else None
                })

            first_price_data = room.date_prices.filter(
                start_date__lte=start_date_obj,
                end_date__gte=start_date_obj
            ).order_by('-id').select_related('user_level').first()
            if not first_price_data:
                logger.info(f"Room {room.id} skipped: No valid first_price_data")
                continue

            discount_amount = 0
            if first_price_data.discount_type != 'none':
                if first_price_data.discount_date and first_price_data.discount_date >= start_date_obj:
                    if first_price_data.discount_type == 'percentage':
                        discount_amount = first_price_data.price * first_price_data.discount_value / 100
                    elif first_price_data.discount_type == 'fixed':
                        discount_amount = first_price_data.discount_value
            price_after_discount_first = max(first_price_data.price - discount_amount, 0)

            total_price = sum(
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
                    "price": first_price_data.price,
                    "price_after_discount": price_after_discount_first,
                    "total_price": total_price,
                    "discount_percentage": first_price_data.discount_value if first_price_data.discount_type == 'percentage' else None,
                    "discount_amount": first_price_data.discount_value if first_price_data.discount_type == 'fixed' else None,
                    "discount_date": first_price_data.discount_date.strftime('%Y/%m/%d') if first_price_data.discount_date else None,
                    "is_fixed_discount_one_time": first_price_data.is_fixed_discount_one_time,
                    "user_level": first_price_data.user_level.title if first_price_data.user_level else default_user_level,
                    "extra_capacity_price": first_price_data.extra_passenger_price,
                    "tourist_price": first_price_data.foreign_passenger_price or 0
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

        if room_count_int == 1:
            return Response(room_data)

        packs = []
        for combo in combinations(room_data, room_count_int):
            pack_rooms = list(combo)
            total_capacity = sum(r['capacity'] for r in pack_rooms)
            total_extra_capacity = sum(r['extra_capacity'] for r in pack_rooms)
            room_ids = [r['id'] for r in pack_rooms]
            logger.info(f"Evaluating pack with rooms {room_ids}: total_capacity={total_capacity}, total_extra_capacity={total_extra_capacity}, passenger_count={passenger_count_int}")
            
            if all(r['room_number'] > 0 for r in pack_rooms):
                pack_total_price = sum(r['price']['total_price'] for r in pack_rooms)
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
            logger.warning(f"No packs formed for hotel {hotel.slug}, passenger_count={passenger_count_int}, room_count={room_count_int}")
            return Response({
                'detail': 'پک مناسب با تعداد اتاق‌های درخواستی و موجودی یافت نشد.',
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
class PassengerListCreateView(ListCreateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = PassengerSerializer

    def get_queryset(self):
        user = self.request.user
        return Passenger.objects.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @swagger_auto_schema(
        tags=["Passenger-user"],
        operation_summary="لیست مسافران",
        operation_description="""
        این API به کاربر اجازه می‌دهد تا:
        - لیست مسافرانی که قبلاً ثبت کرده را ببیند
        این عملیات فقط برای کاربران لاگین‌کرده در دسترس است.
        """,
        responses={200: PassengerSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=["Passenger-user"],
        operation_summary="ثبت مسافر جدید",
        operation_description="""
        با استفاده از این متد می‌توان یک مسافر جدید را ثبت کرد.  
        اطلاعات مسافر شامل نام، نام خانوادگی، شماره موبایل، ملیت و سایر اطلاعات مرتبط است.  
        پس از ثبت، این مسافر به حساب کاربری شما متصل خواهد شد.
        """,
        request_body=PassengerSerializer,
        responses={201: PassengerSerializer()}
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)



# ای پی ای حذف و ویرایش مسافران

class PassengerRetrieveUpdateDestroyView(RetrieveUpdateDestroyAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = PassengerSerializer
    queryset = Passenger.objects.all()

    def get_object(self):
        obj = super().get_object()
        if obj.user != self.request.user:
            raise PermissionDenied("شما اجازه دسترسی به این مسافر را ندارید.")
        return obj

    @swagger_auto_schema(
        tags=["Passenger-user"],
        operation_summary="دریافت اطلاعات یک مسافر",
        operation_description="""
        این API به کاربر اجازه می‌دهد تا اطلاعات یک مسافر خاص را که قبلاً ثبت کرده است، مشاهده کند.  
        دسترسی به مسافران متعلق به خود کاربر محدود شده است.
        """,
        responses={200: PassengerSerializer()}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=["Passenger-user"],
        operation_summary="ویرایش کامل اطلاعات یک مسافر",
        operation_description="""
        
        با استفاده از این متد می‌توان اطلاعات یک مسافر خاص را به صورت کامل ویرایش کرد.  
        تغییرات شامل نام، نام خانوادگی، شماره موبایل، ملیت و سایر اطلاعات مرتبط است.
        فقط مسافرانی که متعلق به کاربر فعلی هستند قابل ویرایش‌اند.
        """,
        request_body=PassengerSerializer,
        responses={200: PassengerSerializer()}
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=["Passenger-user"],
        operation_summary="ویرایش جزئی اطلاعات یک مسافر",
        operation_description="""
        با استفاده از این متد می‌توان بخشی از اطلاعات یک مسافر خاص را ویرایش کرد.  
        مثلا فقط شماره موبایل یا ملیت را تغییر داد بدون نیاز به ارسال تمام اطلاعات.
        فقط مسافرانی که متعلق به کاربر فعلی هستند قابل ویرایش‌اند.
        """,
        request_body=PassengerSerializer,
        responses={200: PassengerSerializer()}
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=["Passenger-user"],
        operation_summary="حذف یک مسافر",
        operation_description="""
        این متد برای حذف یک مسافر خاص استفاده می‌شود.  
        تنها مسافرانی که متعلق به کاربر فعلی هستند قابل حذف‌اند.
        پس از حذف، اطلاعات مسافر دیگر در دسترس نخواهد بود.
        """,
        responses={204: 'Deleted successfully'}
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)




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
        


class SpecialOfferHotelListView(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = HotelListSerializer
    queryset = Hotel.objects.filter(is_special_offer=True)
    pagination_class = None

    @swagger_auto_schema(
        operation_summary="دریافت لیست هتل‌های پیشنهاد ویژه",
        operation_description="این API لیستی از هتل‌هایی که در حالت پیشنهاد ویژه هستند را بدون صفحه‌بندی باز می‌گرداند.",
        tags=['hotel-home']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class FlashSaleHotelListView(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = HotelListSerializer
    queryset = Hotel.objects.filter(is_flash_sale=True)
    pagination_class = None

    @swagger_auto_schema(
        operation_summary="دریافت لیست هتل‌های شگفت‌انگیز",
        operation_description="این API لیستی از هتل‌هایی که در حالت شگفت‌انگیز هستند را بدون صفحه‌بندی باز می‌گرداند.",
        tags=['hotel-home']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class BestSellerHotelListView(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = HotelListSerializer
    queryset = Hotel.objects.filter(is_best_seller=True)
    pagination_class = None

    @swagger_auto_schema(
        operation_summary="دریافت لیست هتل‌های پرفروش",
        operation_description="این API لیستی از هتل‌هایی که در حالت پرفروش هستند را بدون صفحه‌بندی باز می‌گرداند.",
        tags=['hotel-home']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    
    
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

        all_points = CommentPoint.objects.filter(comment__in=comments)

        items = (
            all_points
            .values("comment_point_item__id", "comment_point_item__title")
            .annotate(average=Avg("point"))
            .order_by("comment_point_item__id")
        )

        # میانگین کلی از همه امتیازها
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