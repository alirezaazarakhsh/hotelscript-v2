from collections import defaultdict
from itertools import product
from datetime import datetime
from rest_framework.generics import RetrieveUpdateDestroyAPIView
from rest_framework.exceptions import PermissionDenied
from safarname24.pagination import FacilitiesPaginator, RoomFacilitiesPaginator
from .utils import Round
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
    Comment,
    CommentPoint,
    CommentPointItem,
    Passenger,
    
)
from .serializers import (
    BestHotelsSerializer,
    ClosedDateSerializer,
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
    RoomServiceSerializer,
    HotelFAQListSerializer,
    NearbyPlaceListSerializer,
    CommentListSerializer,
    RatingSummarySerializer,
    RoomListSerializer,
    RoomDateListSerializer,
    PassengerSerializer,
    FacilitiesSerializer, 
    HotelFacilitiesSerializer
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
    
    
    

# ای پی ای های مربوط به کامنت هتل
class HotelCommentListCreateView(ListCreateAPIView):
    permission_classes = (IsAuthenticatedOrReadOnly,)
    serializer_class = CommentListSerializer

    def get_queryset(self):
        hotel_slug = self.kwargs.get('slug')

        queryset = Comment.objects\
            .select_related('user')\
            .prefetch_related('points')\
            .filter(
                hotel__slug=hotel_slug,
                is_approved=True,
            ).annotate(
                rating=Round(Avg('points__point'), 1)
            ).order_by('-created')

        return queryset

    @transaction.atomic
    def perform_create(self, serializer):
        slug = self.kwargs.get('slug')
        hotel = get_object_or_404(Hotel, slug=slug)
        comment = serializer.save(user=self.request.user, hotel=hotel)

        ratings_data = self.request.data.get('ratings', [])
        comment_points = []
        for rating_data in ratings_data:
            item_id = rating_data.get('item')
            rating = rating_data.get('rating')

            comment_point_item = get_object_or_404(CommentPointItem, id=item_id)
            comment_points.append(CommentPoint(
                comment=comment,
                comment_point_item=comment_point_item,
                point=rating
            ))

        CommentPoint.objects.bulk_create(comment_points)

    @swagger_auto_schema(
        operation_summary="لیست نظرات هتل",
        operation_description="نمایش نظرات تاییدشده‌ی یک هتل بر اساس slug.",
        tags=['hotel comments'],
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
            200: CommentListSerializer(many=True),
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="ثبت نظر جدید برای هتل",
        operation_description="ثبت نظر به همراه امتیازدهی به آیتم‌های مختلف توسط کاربر لاگین‌شده.",
        tags=['hotel comments'],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['text', 'ratings'],
            properties={
                'text': openapi.Schema(type=openapi.TYPE_STRING, description='متن نظر'),
                'strengths': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), description='نقاط قوت'),
                'weaknesses': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), description='نقاط ضعف'),
                'ratings': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'item': openapi.Schema(type=openapi.TYPE_INTEGER, description='شناسه معیار امتیازدهی'),
                            'rating': openapi.Schema(type=openapi.TYPE_INTEGER, description='مقدار امتیاز بین ۱ تا ۵'),
                        }
                    ),
                    description='لیست امتیازات'
                )
            }
        ),
        responses={
            201: "نظر با موفقیت ثبت شد.",
            400: "خطا در داده‌های ورودی",
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            try:
                self.perform_create(serializer)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


#ای پی ای خلاصه امتیاز های هتل
class HotelRatingSummaryListView(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = RatingSummarySerializer
    pagination_class = None

    def get_queryset(self):
        hotel_slug = self.kwargs.get('slug')

        queryset = CommentPointItem.objects.annotate(
            avg_rating=Round(Avg(
                'points__point',
                filter=Q(
                    points__comment__hotel__slug=hotel_slug,
                    points__comment__is_approved=True
                )
            ), 1)
        ).order_by('id')

        return queryset

    @swagger_auto_schema(
        operation_summary="خلاصه امتیازهای هتل",
        operation_description=(
            "این API میانگین امتیاز هر آیتم (مانند تمیزی، موقعیت مکانی و...) را برای یک هتل مشخص شده با استفاده از slug بازمی‌گرداند. "
            "فقط نظرات تأیید شده در محاسبه لحاظ می‌شوند."
        ),
        tags=['hotel'],
        manual_parameters=[
            openapi.Parameter(
                name='slug',
                in_=openapi.IN_PATH,
                description='slug مربوط به هتل',
                type=openapi.TYPE_STRING,
                required=True,
            )
        ],
        responses={
            200: RatingSummarySerializer(many=True),
            400: "درخواست نامعتبر"
        }
    )
    def get(self, request, *args, **kwargs):
       
        return super().get(request, *args, **kwargs)
    
    
    
    
    
    

class RoomListView(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = RoomListSerializer
    pagination_class = None

    def get_queryset(self):
        hotel_slug = self.kwargs.get('slug')
        start_date, end_date, passenger_counts = self._parse_query_params()

        available_room_dates = RoomDate.objects.select_related('room')\
            .annotate(
                occupied_count=RoomDate.get_occupied_statuses_count_expression(),
                discount_count=RoomDate.get_discount_count_expression(),
                original_price=F('price'),
                discounted_price=RoomDate.get_discounted_price_expression(),
                capacity=F('room__capacity'),
            ).filter(
                room__hotel__slug=hotel_slug,
                date__range=(start_date, end_date),
                room__capacity__in=passenger_counts,
                room__count__gt=F('occupied_count'),
            )

        total_days = (end_date - start_date).days + 1

        matching_rooms_data = available_room_dates.values('room_id').annotate(
            days_count=Count('date', distinct=True),
            original_total_price=Sum('original_price'),
            discounted_total_price=Sum('discounted_price'),
            occupied_count=F('occupied_count'),
            discount_count=F('discount_count'),
            capacity=F('capacity'),
        ).filter(
            days_count=total_days,
        )

        self.room_data_map = {
            room_data['room_id']: {
                'discount_count': room_data['discount_count'],
                'occupied_count': room_data['occupied_count'],
                'total_price': (
                    room_data['discounted_total_price']
                    if room_data['occupied_count'] < room_data['discount_count']
                    else room_data['original_total_price']
                ),
                'original_total_price': room_data['original_total_price'],
            }
            for room_data in matching_rooms_data
        }

        return Room.objects.prefetch_related('services')\
            .filter(id__in=self.room_data_map.keys())\
            .order_by('id')

    def _parse_query_params(self):
        request = self.request
        passenger_count_raw = request.query_params.get('passenger_count')
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

        if not passenger_count_raw:
            raise ValidationError({'passenger_count': 'تعداد مسافران الزامی است'})

        if not start_date_str:
            raise ValidationError({'start_date': 'تاریخ ورود الزامی است'})

        if not end_date_str:
            raise ValidationError({'end_date': 'تاریخ خروج الزامی است'})

        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        except:
            raise ValidationError({'start_date': 'فرمت تاریخ ورود اشتباه است'})

        try:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except:
            raise ValidationError({'end_date': 'فرمت تاریخ خروج اشتباه است'})

        if start_date < timezone.localdate():
            raise ValidationError({'start_date': 'تاریخ ورود نمی‌تواند قبل از امروز باشد.'})

        if end_date < start_date:
            raise ValidationError({'end_date': 'تاریخ خروج نمی‌تواند از تاریخ ورود کمتر باشد.'})

        try:
            passenger_counts = [
                int(count) for count in passenger_count_raw.split(',')
                if count.strip().isdigit()
            ]
        except ValueError:
            raise ValidationError({'passenger_count': 'فرمت تعداد مسافران نادرست است'})

        return start_date, end_date, passenger_counts

    def list(self, request, *args, **kwargs):
        _, _, passenger_counts = self._parse_query_params()
        queryset = self.get_queryset()
        rooms = list(queryset)

        options = [
            [
                room for room in rooms
                if room.capacity == count and self.room_data_map[room.id]['occupied_count'] + i < room.count
            ]
            for i, count in enumerate(passenger_counts)
        ]

        raw_combos = product(*options)
        unique_combos = {
            tuple(sorted(combo, key=lambda room: room.id))
            for combo in raw_combos
        }

        serialized = []
        for combo in unique_combos:
            context = self.get_serializer_context()
            context['room_data_map'] = self.room_data_map.copy()

            combo_serialized = []
            for room in combo:
                room_data = context['room_data_map'][room.id]
                current_room_count = sum(1 for r in combo_serialized if r['id'] == room.id)

                room_data['total_price'] = (
                    room_data['total_price']
                    if room_data['occupied_count'] + current_room_count < room_data['discount_count']
                    else room_data['original_total_price']
                )

                context['room_data_map'][room.id] = room_data
                combo_serialized.append(RoomListSerializer(room, context=context).data)

            serialized.append(combo_serialized)

        return Response(serialized)

    @swagger_auto_schema(
        operation_summary="دریافت لیست اتاق‌های قابل رزرو",
        operation_description=(
            "بر اساس slug هتل، تاریخ ورود، تاریخ خروج، و تعداد مسافران، "
            "اتاق‌های موجود را همراه با قیمت نهایی و تخفیف‌ها باز می‌گرداند."
        ),
        tags=['hotel'],
        manual_parameters=[
            openapi.Parameter(
                'passenger_count',
                openapi.IN_QUERY,
                description="تعداد مسافران به صورت لیست ظرفیت برای هر اتاق، مانند: 2,2",
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                'start_date',
                openapi.IN_QUERY,
                description="تاریخ ورود (YYYY-MM-DD)",
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                'end_date',
                openapi.IN_QUERY,
                description="تاریخ خروج (YYYY-MM-DD)",
                type=openapi.TYPE_STRING,
                required=True,
            ),
        ],
        responses={
            200: 'لیست اتاق‌های در دسترس',
            400: 'درخواست نادرست یا تاریخ اشتباه'
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    
    
    

class RoomDateListView(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = RoomDateListSerializer
    pagination_class = None

    def get_queryset(self):
        room_id = self.kwargs.get('room_id')
        today = timezone.localdate()

        queryset = RoomDate.objects.annotate(
            occupied_count=RoomDate.get_occupied_statuses_count_expression(),
            discount_count=RoomDate.get_discount_count_expression(),
            original_price=F('price'),
            discounted_price=Case(
                When(
                    discount_count__gt=F('occupied_count'),
                    then=RoomDate.get_discounted_price_expression()
                ),
                default=F('price'),
                output_field=PositiveBigIntegerField(),
            ),
        ).filter(
            room__id=room_id,
            room__count__gt=F('occupied_count'),  # فقط اتاق‌هایی که ظرفیت دارند
            date__gte=today,
        ).order_by('date')

        return queryset

    @swagger_auto_schema(
        operation_summary="دریافت تاریخ‌های قابل رزرو برای اتاق",
        operation_description="""
        این API لیستی از تاریخ‌هایی که اتاق هنوز ظرفیت خالی دارد را برمی‌گرداند.  
        - شامل قیمت اصلی و قیمت تخفیف‌خورده (در صورت اعمال تخفیف)  
        - فقط تاریخ‌های آینده نمایش داده می‌شوند  
        - اتاق باید ظرفیت خالی داشته باشد  
        """,
        manual_parameters=[
            openapi.Parameter(
                'room_id',
                openapi.IN_PATH,
                description="شناسه اتاق مورد نظر",
                type=openapi.TYPE_INTEGER,
                required=True
            ),
        ],
        responses={200: RoomDateListSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    
    
    
    
# ای پی ای ثبت مسافر جدید 
class PassengerListCreateView(ListCreateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = PassengerSerializer

    def get_queryset(self):
        """
        بازگرداندن لیست مسافران متعلق به کاربر فعلی.
        """
        user = self.request.user
        queryset = Passenger.objects.filter(user=user)
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @swagger_auto_schema(
        operation_summary="لیست  مسافران",
        operation_description="""
        این API به کاربر اجازه می‌دهد تا:
        - لیست مسافرانی که قبلاً ثبت کرده را ببیند
        
        
        این عملیات فقط برای کاربران لاگین‌کرده در دسترس است.
        """,
        responses={
            200: PassengerSerializer(many=True),
            201: PassengerSerializer(),
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
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
    
    
    
    
class ClosedDateListCreateView(ListCreateAPIView):
        permission_classes = (AllowAny,)
        serializer_class = ClosedDateSerializer

        def get_queryset(self):
            """
            بازگرداندن لیست تاریخ‌های بسته شده به ترتیب تاریخ.
            """
            return ClosedDate.objects.all().order_by('date')

        @swagger_auto_schema(
            operation_summary="لیست تاریخ‌های بسته شده بازه‌های زمانی",
            operation_description="""
            این API به کاربر اجازه می‌دهد تا:
            - لیست تاریخ‌های بسته شده بازه‌های زمانی را مشاهده کند
            - تاریخ بسته شده جدیدی را ثبت کند
            """,
            responses={
                200: ClosedDateSerializer(many=True),
                201: ClosedDateSerializer(),
            }
        )
        def get(self, request, *args, **kwargs):
            return super().get(request, *args, **kwargs)

        @swagger_auto_schema(
            operation_summary="ثبت تاریخ بسته شده جدید",
            operation_description="""
            با استفاده از این API می‌توانید تاریخ بسته شده جدیدی برای یک بازه زمانی اتاق ثبت کنید.
            """,
            request_body=ClosedDateSerializer,
            responses={201: ClosedDateSerializer()}
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