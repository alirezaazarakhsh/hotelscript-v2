from collections import defaultdict
from datetime import datetime
from rest_framework.permissions import AllowAny
from rest_framework.generics import (
    ListAPIView,
)
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from django.db.models import (
    Q,
    F,
    Sum,
    Count,
    Avg,
)
from django.db.models.functions import Round
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import (
    Hotel,
    RoomDate,
    City,
    HotelType,
)
from .serializers import (
    HotelListSerializer,
    CitySerializer,
    HotelTypeSerializer,
)

# Create your views here.

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
            raise ValidationError({
                'start_date': 'لطفا تاریخ ورود را به درستی وارد نمایید'
            })
        try:
            end_date = datetime.strptime(self.request.query_params.get('end_date'), "%Y-%m-%d").date()
        except:
            raise ValidationError({
                'end_date': 'لطفا تاریخ خروج را به درستی وارد نمایید'
            })
        if not city_or_hotel:
            raise ValidationError({
                'q': 'نام هتل یا شهر الزامی است'
            })
        if not passenger_count:
            raise ValidationError({
                'passenger_count': 'تعداد مسافران الزامی است'
            })
        if not start_date:
            raise ValidationError({
                'start_date': 'تاریخ ورود الزامی است'
            })
        if not end_date:
            raise ValidationError({
                'end_date': 'تاریخ خروج الزامی است'
            })

        available_room_dates = RoomDate.objects.select_related('room').annotate(
            occupied_count=RoomDate.get_occupied_statuses_count_expression(),
            original_price=F('price'),
            final_price=RoomDate.get_final_price_expression(),
        ).filter(
            date__gte=max(start_date, timezone.localdate()),
            date__lte=end_date,
            room__capacity=passenger_count,
            room__count__gt=F('occupied_count'),
        )

        matching_rooms_data = available_room_dates.values('room_id').annotate(
            hotel_id=F('room__hotel_id'),
            days_count=Count('date', distinct=True),
            original_total_price=Sum('original_price'),
            total_price=Sum('final_price'),
        ).filter(
            days_count=(end_date - max(start_date, timezone.localdate())).days + 1,
        )

        if has_discount:
            matching_rooms_data = matching_rooms_data.filter(
                total_price__lt=F('original_total_price')
            )

        if min_price:
            matching_rooms_data = matching_rooms_data.filter(
                total_price__gte=min_price,
            )
        if max_price:
            matching_rooms_data = matching_rooms_data.filter(
                total_price__lte=max_price,
            )

        self.hotel_price_map = defaultdict(list)

        for room_data in matching_rooms_data:
            hotel_id = room_data['hotel_id']
            self.hotel_price_map[hotel_id].append({
                'total_price': room_data['total_price'],
                'original_total_price': room_data['original_total_price'],
            })

        self.hotel_price_map = dict(self.hotel_price_map)

        queryset = Hotel.objects.prefetch_related('rooms')\
            .select_related('city')\
            .select_related('city__province')\
            .select_related('type')\
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
                type_ids = [id for id in type.split(',') if id.strip().isdigit()]
                queryset = queryset.filter(
                    type__id__in=type_ids,
                )
            except ValueError:
                raise ValidationError({
                    'type': 'فرمت نوع هتل صحیح نیست.'
                })

        if stars:
            try:
                stars = [star for star in stars.split(',') if star.strip().isdigit()]
                queryset = queryset.filter(
                    stars__in=stars,
                )
            except ValueError:
                raise ValidationError({
                    'type': 'فرمت تعداد ستاره هتل صحیح نیست.'
                })

        if is_special_offer:
            queryset = queryset.filter(
                is_special_offer=is_special_offer,
            )

        # TODO: filter by facilities
        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()

        context['hotel_min_price_map'] = {
            hotel_id: min(items, key=lambda x: x['total_price'])
            for hotel_id, items in self.hotel_price_map.items()
        }
        return context

    @swagger_auto_schema(manual_parameters=[
        openapi.Parameter(
            'q',
            openapi.IN_QUERY,
            description="city or hotel name/slug",
            type=openapi.TYPE_STRING,
            required=True,
        ),
        openapi.Parameter(
            'passenger_count',
            openapi.IN_QUERY,
            description="number of passengers, adults and children",
            type=openapi.TYPE_INTEGER,
            required=True,
        ),
        openapi.Parameter(
            'start_date',
            openapi.IN_QUERY,
            description="start date",
            type=openapi.TYPE_STRING,
            required=True,
        ),
        openapi.Parameter(
            'end_date',
            openapi.IN_QUERY,
            description="end date",
            type=openapi.TYPE_STRING,
            required=True,
        ),
        openapi.Parameter(
            'type',
            openapi.IN_QUERY,
            description="hotel types separated by commas. (e.g. 1,2,3)",
            type=openapi.TYPE_STRING,
            required=False,
        ),
        openapi.Parameter(
            'stars',
            openapi.IN_QUERY,
            description="hotel stars separated by commas. (e.g. 1,2,3)",
            type=openapi.TYPE_STRING,
            required=False,
        ),
        openapi.Parameter(
            'min_price',
            openapi.IN_QUERY,
            description="minimum price",
            type=openapi.TYPE_INTEGER,
            required=False,
        ),
        openapi.Parameter(
            'max_price',
            openapi.IN_QUERY,
            description="maximum price",
            type=openapi.TYPE_INTEGER,
            required=False,
        ),
        openapi.Parameter(
            'special_offer',
            openapi.IN_QUERY,
            description="is special offer",
            type=openapi.TYPE_BOOLEAN,
            required=False,
        ),
        openapi.Parameter(
            'discount',
            openapi.IN_QUERY,
            description="has discount",
            type=openapi.TYPE_BOOLEAN,
            required=False,
        ),
    ])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

class CityListView(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = CitySerializer

    def get_queryset(self):
        queryset = City.objects.select_related('province')

        if q := self.request.query_params.get('q'):
            queryset = queryset.filter(
                Q(name__contains=q) | 
                Q(slug__icontains=q)
            )

        return queryset
    
    @swagger_auto_schema(manual_parameters=[
        openapi.Parameter(
            'q',
            openapi.IN_QUERY,
            description="city name/slug",
            type=openapi.TYPE_STRING,
            required=False,
        ),
    ])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

class HotelTypeListView(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = HotelTypeSerializer
    queryset = HotelType.objects.all()
