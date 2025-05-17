from collections import defaultdict
from itertools import product
from datetime import datetime
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
    HotelListSerializer,
    CitySerializer,
    HotelTypeSerializer,
    FacilitiesSerializer,
    RoomFacilitiesSerializer,
    RoomServiceSerializer,
    HotelRetrieveSerializer,
    HotelFAQListSerializer,
    NearbyPlaceListSerializer,
    CommentListSerializer,
    RatingSummarySerializer,
    RoomListSerializer,
    RoomDateListSerializer,
    PassengerSerializer,
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
        
        if start_date < timezone.localdate():
            raise ValidationError({
                'start_date': 'تاریخ ورود نمی‌تواند قبل از امروز باشد.'
            })

        if end_date < start_date:
            raise ValidationError({
                'end_date': 'تاریخ خروج نمی‌تواند از تاریخ ورود کمتر باشد.'
            })

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
                'total_price': room_data['discounted_total_price'] if room_data['occupied_count'] < room_data['discount_count'] else room_data['original_total_price'],
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
        # TODO: order by
        queryset = queryset.order_by('id')
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
    pagination_class = None

class FacilitiesListView(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = FacilitiesSerializer
    queryset = Facilities.objects.all()
    pagination_class = None

class RoomFacilitiesListView(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = RoomFacilitiesSerializer
    queryset = RoomFacilities.objects.all()
    pagination_class = None

class RoomServiceListView(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = RoomServiceSerializer
    queryset = RoomService.objects.all()
    pagination_class = None

class HotelRetrieveView(RetrieveAPIView):
    permission_classes = (AllowAny,)
    serializer_class = HotelRetrieveSerializer
    queryset = Hotel.objects.select_related('city')\
            .select_related('city__province')\
            .select_related('type')\
            .prefetch_related('tags')\
            .all()
    lookup_field = 'slug'
    lookup_url_kwarg = 'slug'

class HotelFAQListView(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = HotelFAQListSerializer
    pagination_class = None

    def get_queryset(self):
        hotel_slug = self.kwargs.get('slug')

        queryset = HotelFAQ.objects.filter(
            hotel__slug=hotel_slug
        )

        return queryset

class HotelFacilitiesListView(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = FacilitiesSerializer

    def get_queryset(self):
        hotel_slug = self.kwargs.get('slug')

        queryset = Facilities.objects.filter(
            hotels__slug=hotel_slug
        ).order_by('id')

        return queryset

class HotelRoomFacilitiesListView(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = RoomFacilitiesSerializer

    def get_queryset(self):
        hotel_slug = self.kwargs.get('slug')

        queryset = RoomFacilities.objects.filter(
            hotels__slug=hotel_slug
        ).order_by('id')

        return queryset

class HotelNearbyPlaceListView(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = NearbyPlaceListSerializer

    def get_queryset(self):
        hotel_slug = self.kwargs.get('slug')

        queryset = NearbyPlace.objects.filter(
            hotel__slug=hotel_slug
        ).order_by('id')

        return queryset

class HotelCommentListCreateView(ListCreateAPIView):
    permission_classes = (IsAuthenticatedOrReadOnly,)
    serializer_class = CommentListSerializer

    def get_queryset(self):
        hotel_slug = self.kwargs.get('slug')

        queryset = Comment.objects\
            .select_related('user__natural_profile')\
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

        hotel = get_object_or_404(
            Hotel,
            slug=slug,
        )

        comment = serializer.save(user=self.request.user, hotel=hotel)

        ratings_data = self.request.data.get('ratings', [])

        comment_points = []
        for rating_data in ratings_data:
            item_id = rating_data.get('item')
            rating = rating_data.get('rating')

            comment_point_item = CommentPointItem.objects.get(id=item_id)

            comment_points.append({
                'comment': comment,
                'comment_point_item': comment_point_item,
                'point': rating,
            })

        CommentPoint.objects.bulk_create(
            [CommentPoint(**rating) for rating in comment_points]
        )

    def post(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)

            if serializer.is_valid():
                self.perform_create(serializer)

                return Response(serializer.data, status=status.HTTP_201_CREATED)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class HotelRatingSummaryListView(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = RatingSummarySerializer
    pagination_class = None

    def get_queryset(self):
        hotel_slug = self.kwargs.get('slug')

        queryset = CommentPointItem.objects.annotate(
            avg_rating=Round(Avg(
                'points__point',
                filter=Q(points__comment__hotel__slug=hotel_slug, points__comment__is_approved=True)
            ), 1)
        ).order_by('id')

        return queryset

class RoomListView(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = RoomListSerializer
    pagination_class = None

    def get_queryset(self):
        hotel_slug = self.kwargs.get('slug')

        passenger_count = self.request.query_params.get('passenger_count')
       
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
        
        if start_date < timezone.localdate():
            raise ValidationError({
                'start_date': 'تاریخ ورود نمی‌تواند قبل از امروز باشد.'
            })

        if end_date < start_date:
            raise ValidationError({
                'end_date': 'تاریخ خروج نمی‌تواند از تاریخ ورود کمتر باشد.'
            })
        
        try:
            passenger_count = [count for count in passenger_count.split(',') if count.strip().isdigit()]
        except ValueError:
            raise ValidationError({
                'type': 'فرمت تعداد مسافران صحیح نیست.'
            })

        available_room_dates = RoomDate.objects.select_related('room')\
            .annotate(
                occupied_count=RoomDate.get_occupied_statuses_count_expression(),
                discount_count=RoomDate.get_discount_count_expression(),
                original_price=F('price'),
                discounted_price=RoomDate.get_discounted_price_expression(),
                capacity=F('room__capacity'),
            ).filter(
                room__hotel__slug=hotel_slug,
                date__gte=start_date,
                date__lte=end_date,
                room__capacity__in=passenger_count,
                room__count__gt=F('occupied_count'),
            )

        matching_rooms_data = available_room_dates.values('room_id').annotate(
            days_count=Count('date', distinct=True),
            original_total_price=Sum('original_price'),
            discounted_total_price=Sum('discounted_price'),
            occupied_count=F('occupied_count'),
            discount_count=F('discount_count'),
            capacity=F('capacity'),
        ).filter(
            days_count=(end_date - start_date).days + 1,
        )

        self.room_data_map = defaultdict(dict)

        for room_data in matching_rooms_data:
            room_id = room_data['room_id']

            self.room_data_map[room_id] = {
                'discount_count': room_data['discount_count'],
                'occupied_count': room_data['occupied_count'],
                'total_price': room_data['discounted_total_price'] if room_data['occupied_count'] < room_data['discount_count'] else room_data['original_total_price'],
                'original_total_price': room_data['original_total_price'],
            }

        queryset = Room.objects.prefetch_related('services')\
            .filter(
                id__in=[item['room_id'] for item in matching_rooms_data],
            ).distinct()

        queryset = queryset.order_by('id')
        return queryset
    
    def list(self, request, *args, **kwargs):
        passenger_count = request.query_params.get('passenger_count')
        passenger_counts = [int(count) for count in passenger_count.split(',') if count.strip().isdigit()]

        queryset = self.get_queryset()

        rooms = list(queryset)

        options = [
            [room for room in rooms if room.capacity == passenger_count and self.room_data_map[room.id]['occupied_count'] + i < room.count]
            for i, passenger_count in enumerate(passenger_counts)
        ]

        raw_combos = product(*options)

        unique_combos = set()
        for combo in raw_combos:
            ordered_pair = tuple(sorted(combo, key=lambda room: room.id))
            unique_combos.add(ordered_pair)

        serialized = []
        for combo in unique_combos:
            context = self.get_serializer_context()
            context['room_data_map'] = self.room_data_map.copy()

            rooms = []
            for room in combo:
                room_data = self.room_data_map[room.id].copy()
                current_room_count_in_pack = len(list(filter(lambda r: r['id'] == room.id, rooms)))
                room_data['total_price'] = room_data['total_price'] if room_data['occupied_count'] + current_room_count_in_pack < room_data['discount_count'] else room_data['original_total_price']
                context['room_data_map'][room.id] = room_data
                rooms.append(
                    RoomListSerializer(room, context=context).data
                )

            serialized.append(
                rooms
            )

        return Response(serialized)

    @swagger_auto_schema(manual_parameters=[
        openapi.Parameter(
            'passenger_count',
            openapi.IN_QUERY,
            description="number of passengers, adults and children. For pack separated by comma e.g. 2,2",
            type=openapi.TYPE_STRING,
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
    ])
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
            room__count__gt=F('occupied_count'),
            date__gte=today,
        ).order_by('date')

        return queryset

class PassengerListCreateView(ListCreateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = PassengerSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = Passenger.objects.filter(
            user=user
        )

        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
