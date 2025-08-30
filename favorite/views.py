from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from drf_yasg.utils import swagger_auto_schema
from django.shortcuts import get_object_or_404
from drf_yasg import openapi
from django.contrib.contenttypes.models import ContentType
from rest_framework.pagination import PageNumberPagination
from reservation.models import Hotel
from .serializers import (
    FavoriteCollectionCreateSerializer,
    FavoriteCollectionDetailSerializer,
    BaseFavoriteCollectionSerializer,
    FavoriteItemSerializer,
    HotelSummarySerializer,  # ایمپورت از .serializers به جای reservation.serializers
)
from django.db.models import Avg
from datetime import timedelta, datetime
from .models import FavoriteCollection, Favorite
from django.utils import timezone
from jalali_date import date2jalali
import logging

logger = logging.getLogger(__name__)

# ------------------ لیست کالکشن‌ها ------------------
class FavoriteCollectionPagination(PageNumberPagination):
    page_size = 10  # Number of collections per page
    page_size_query_param = 'page_size'
    max_page_size = 100

class FavoriteCollectionListCreateAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = FavoriteCollectionPagination

    @swagger_auto_schema(
        operation_summary="دریافت لیست کالکشن‌های علاقه‌مندی",
        operation_description="""
        این API تمامی کالکشن‌های علاقه‌مندی (چه هتل و چه مقاله) را نمایش می‌دهد.
        هر کالکشن شامل شناسه، عنوان و تعدادی تصویر thumbnail از آیتم‌های داخل لیست است.
        پاسخ‌ها به صورت صفحه‌بندی شده ارائه می‌شوند.
        """,
        tags=["favorite-panel"],
        responses={200: BaseFavoriteCollectionSerializer(many=True)},
    )
    def get(self, request):
        collections = FavoriteCollection.objects.filter(user=request.user)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(collections, request)
        serializer = BaseFavoriteCollectionSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)

    @swagger_auto_schema(
        operation_summary="ایجاد کالکشن علاقه‌مندی جدید",
        operation_description="""
        با این API می‌توانید یک لیست علاقه‌مندی جدید ایجاد کنید.
        فقط کافی است عنوان (title) لیست را ارسال نمایید.
        """,
        tags=["favorite-panel"],
        request_body=FavoriteCollectionCreateSerializer,
        responses={201: BaseFavoriteCollectionSerializer},
    )
    def post(self, request):
        serializer = FavoriteCollectionCreateSerializer(data=request.data)
        if serializer.is_valid():
            collection = serializer.save(user=request.user)
            return Response(BaseFavoriteCollectionSerializer(collection, context={"request": request}).data, status=201)
        return Response(serializer.errors, status=400)

# ------------------ جزئیات کالکشن ------------------
class FavoriteCollectionDetailPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class FavoriteCollectionDetailAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = FavoriteCollectionDetailPagination

    def get_hotel_min_price_map(self, hotels):
        hotel_min_price_map = {}
        today = date2jalali(timezone.now().date())
        check_in = self.request.query_params.get('check_in')
        check_out = self.request.query_params.get('check_out')
        start_date = today
        end_date = today + timedelta(days=1)  # پیش‌فرض: یک شب

        if check_in and check_out:
            try:
                start_date = date2jalali(datetime.strptime(check_in, '%Y-%m-%d').date())
                end_date = date2jalali(datetime.strptime(check_out, '%Y-%m-%d').date())
            except ValueError:
                logger.warning(f"Invalid date format: check_in={check_in}, check_out={check_out}")
                start_date = today
                end_date = today + timedelta(days=1)

        user_level = getattr(self.request.user, 'user_level', None) if self.request.user.is_authenticated else None
        logger.debug(f"User level: {user_level}")

        for hotel in hotels:
            rooms = hotel.rooms.all()
            min_total_price = float('inf')
            min_price_data = {
                'total_price': 0,
                'original_total_price': 0,
                'discount_type': 'none',
                'discount_value': 0,
                'discount_date': None,
                'is_flash_sale': hotel.is_flash_sale
            }

            for room in rooms:
                date_prices = room.date_prices.filter(
                    start_date__lte=start_date,
                    end_date__gte=end_date,
                    user_level=user_level if user_level else None
                )
                logger.debug(f"Hotel {hotel.id}, Room {room.id}: Found {date_prices.count()} date prices with user_level={user_level}")

                if not date_prices.exists() and user_level:
                    date_prices = room.date_prices.filter(
                        start_date__lte=start_date,
                        end_date__gte=end_date,
                        user_level__isnull=True
                    )
                    logger.debug(f"Hotel {hotel.id}, Room {room.id}: Fallback to {date_prices.count()} date prices with user_level=None")

                if not date_prices.exists():
                    date_prices = room.date_prices.filter(
                        end_date__gte=today,
                        user_level__isnull=True
                    ).order_by('price')
                    logger.debug(f"Hotel {hotel.id}, Room {room.id}: Fallback to {date_prices.count()} valid date prices")

                if hotel.is_flash_sale:
                    date_prices = date_prices.filter(is_flash_sale=True)
                    logger.debug(f"Hotel {hotel.id} is flash sale, filtering for flash sale prices: {date_prices.count()}")

                for date_price in date_prices:
                    original_price = date_price.price or 0
                    discount_type = date_price.discount_type or 'none'
                    discount_value = date_price.discount_value or 0
                    total_price = original_price

                    if discount_type == 'percentage' and date_price.discount_date and date_price.discount_date >= today:
                        total_price = original_price * (1 - discount_value / 100)
                    elif discount_type == 'fixed' and date_price.is_fixed_discount_one_time:
                        total_price = max(0, original_price - discount_value)
                    elif hotel.is_flash_sale and hasattr(date_price, 'flash_sale_discount'):
                        total_price = max(0, original_price - date_price.flash_sale_discount)

                    if total_price < min_total_price:
                        min_total_price = total_price
                        min_price_data = {
                            'total_price': int(total_price),
                            'original_total_price': int(original_price),
                            'discount_type': discount_type,
                            'discount_value': discount_value,
                            'discount_date': date_price.discount_date,
                            'is_flash_sale': hotel.is_flash_sale
                        }

                if min_total_price == float('inf'):
                    logger.warning(f"Hotel {hotel.id}: No valid RoomDatePrice found")
                else:
                    logger.debug(f"Hotel {hotel.id}: Min price data: {min_price_data}")

            hotel_min_price_map[hotel.id] = min_price_data

        return hotel_min_price_map

    def get_average_score(self, hotel):
        return hotel.comments.aggregate(Avg('stars'))['stars__avg'] or 0.0

    def get_comment_count(self, hotel):
        return hotel.comments.count()

    @swagger_auto_schema(
        operation_summary="جزئیات یک کالکشن",
        operation_description="""
        این API جزئیات کامل یک کالکشن خاص را برمی‌گرداند.
        شامل لیست کامل هتل‌ها به همراه اطلاعات خلاصه هر هتل (مشابه لیست فروش شگفت‌انگیز).
        آیتم‌ها به صورت صفحه‌بندی شده ارائه می‌شوند.
        """,
        tags=["favorite-panel"],
        responses={200: FavoriteCollectionDetailSerializer},
    )
    def get(self, request, pk):
        collection = get_object_or_404(FavoriteCollection, id=pk, user=request.user)
        hotel_content_type = ContentType.objects.get_for_model(Hotel)
        favorite_hotels = Favorite.objects.filter(
            list=collection,
            item_content_type=hotel_content_type
        ).values_list('item_object_id', flat=True)
        hotels = Hotel.objects.filter(id__in=favorite_hotels).select_related('city', 'type').distinct()

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(hotels, request)

        hotel_min_price_map = self.get_hotel_min_price_map(page)
        context = {
            'request': request,
            'hotel_min_price_map': hotel_min_price_map,
            'view': self
        }

        # سریال‌سازی هتل‌ها با اضافه کردن average_score و comment_count
        hotels_data = []
        for hotel in page:
            serialized = HotelSummarySerializer(hotel, context=context).data
            serialized['average_score'] = self.get_average_score(hotel)
            serialized['comment_count'] = self.get_comment_count(hotel)
            hotels_data.append(serialized)

        # سریال‌سازی کل کالکشن
        serializer = FavoriteCollectionDetailSerializer(collection, context=context)
        response_data = serializer.data
        response_data['hotels'] = hotels_data

        return paginator.get_paginated_response(response_data)

    @swagger_auto_schema(
        operation_summary="حذف یک کالکشن",
        operation_description="با این API می‌توانید یک کالکشن کامل را حذف کنید.",
        tags=["favorite-panel"],
    )
    def delete(self, request, pk):
        collection = get_object_or_404(FavoriteCollection, id=pk, user=request.user)
        collection.delete()
        return Response(status=204)

# ------------------ مدیریت آیتم‌های داخل کالکشن ------------------
class FavoriteItemListCreateAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_hotel_min_price_map(self, hotels):
        hotel_min_price_map = {}
        today = date2jalali(timezone.now().date())
        check_in = self.request.query_params.get('check_in')
        check_out = self.request.query_params.get('check_out')
        start_date = today
        end_date = today

        # Parse check_in and check_out if provided
        if check_in and check_out:
            try:
                start_date = date2jalali(datetime.strptime(check_in, '%Y-%m-%d').date())
                end_date = date2jalali(datetime.strptime(check_out, '%Y-%m-%d').date())
            except ValueError:
                logger.warning(f"Invalid date format: check_in={check_in}, check_out={check_out}")

        # Get user level if authenticated
        user_level = getattr(self.request.user, 'user_level', None) if self.request.user.is_authenticated else None
        logger.debug(f"User level: {user_level}")

        for hotel in hotels:
            rooms = hotel.rooms.all()
            min_total_price = float('inf')
            min_price_data = {
                'total_price': 0,
                'original_total_price': 0,
                'discount_type': 'none',
                'discount_value': 0,
                'discount_date': None,
            }

            for room in rooms:
                date_prices = room.date_prices.filter(
                    start_date__lte=start_date,
                    end_date__gte=end_date,
                    user_level=user_level if user_level else None
                )
                logger.debug(f"Hotel {hotel.id}, Room {room.id}: Found {date_prices.count()} date prices with user_level={user_level}")

                if not date_prices.exists() and user_level:
                    date_prices = room.date_prices.filter(
                        start_date__lte=start_date,
                        end_date__gte=end_date,
                        user_level__isnull=True
                    )
                    logger.debug(f"Hotel {hotel.id}, Room {room.id}: Fallback to {date_prices.count()} date prices with user_level=None")

                if not date_prices.exists():
                    date_prices = room.date_prices.filter(
                        end_date__gte=today,
                        user_level__isnull=True
                    ).order_by('price')
                    logger.debug(f"Hotel {hotel.id}, Room {room.id}: Fallback to {date_prices.count()} valid date prices")

                for date_price in date_prices:
                    original_price = date_price.price or 0
                    discount_type = date_price.discount_type or 'none'
                    discount_value = date_price.discount_value or 0
                    total_price = original_price

                    if discount_type == 'percentage' and date_price.discount_date and date_price.discount_date >= today:
                        total_price = original_price * (1 - discount_value / 100)
                    elif discount_type == 'fixed' and date_price.is_fixed_discount_one_time:
                        total_price = max(0, original_price - discount_value)

                    if total_price < min_total_price:
                        min_total_price = total_price
                        min_price_data = {
                            'total_price': int(total_price),
                            'original_total_price': int(original_price),
                            'discount_type': discount_type,
                            'discount_value': discount_value,
                            'discount_date': date_price.discount_date,
                        }

            if min_total_price == float('inf'):
                logger.warning(f"Hotel {hotel.id}: No valid RoomDatePrice found")
            else:
                logger.debug(f"Hotel {hotel.id}: Min price data: {min_price_data}")

            hotel_min_price_map[hotel.id] = min_price_data

        return hotel_min_price_map

    def get_average_score(self, hotel):
        from django.db.models import Avg
        return hotel.comments.aggregate(Avg('stars'))['stars__avg'] or 0.0

    def get_comment_count(self, hotel):
        return hotel.comments.count()

    @swagger_auto_schema(
        operation_summary="دریافت آیتم‌های داخل یک کالکشن",
        operation_description="این API تمامی آیتم‌های (هتل یا مقاله) داخل یک کالکشن خاص را نمایش می‌دهد.",
        tags=["favorite-panel"],
        responses={200: FavoriteItemSerializer(many=True)},
    )
    def get(self, request, pk):
        collection = get_object_or_404(FavoriteCollection, id=pk, user=request.user)
        hotel_content_type = ContentType.objects.get_for_model(Hotel)
        favorite_hotels = Favorite.objects.filter(
            list=collection,
            item_content_type=hotel_content_type
        ).values_list('item_object_id', flat=True)
        hotels = Hotel.objects.filter(id__in=favorite_hotels).select_related('city', 'type').distinct()
        hotel_min_price_map = self.get_hotel_min_price_map(hotels)
        context = {
            'request': request,
            'hotel_min_price_map': hotel_min_price_map,
            'view': self
        }
        return Response(FavoriteItemSerializer(collection.favorites.all(), many=True, context=context).data)

    @swagger_auto_schema(
        operation_summary="افزودن آیتم به یک کالکشن",
        operation_description="""
        برای افزودن آیتم جدید به یک کالکشن باید نوع (type) و شناسه (id) آیتم را ارسال کنید.
        - type: hotel یا article
        - id: شناسه آیتم
        """,
        tags=["favorite-panel"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "type": openapi.Schema(type=openapi.TYPE_STRING, description="نوع آیتم: hotel یا article"),
                "id": openapi.Schema(type=openapi.TYPE_INTEGER, description="شناسه آیتم"),
            },
            required=["type", "id"]
        ),
        responses={201: FavoriteItemSerializer},
    )
    def post(self, request, pk):
        collection = get_object_or_404(FavoriteCollection, id=pk, user=request.user)
        item_type = request.data.get("type")
        item_id = request.data.get("id")

        if item_type not in ["hotel", "article"]:
            return Response({"error": "نوع آیتم نامعتبر است"}, status=400)

        content_type = get_object_or_404(ContentType, model=item_type)
        model_class = content_type.model_class()
        if not model_class.objects.filter(id=item_id).exists():
            return Response({"error": "آیتم با این شناسه یافت نشد"}, status=404)

        favorite = Favorite.objects.create(list=collection, item_content_type=content_type, item_object_id=item_id)
        hotels = Hotel.objects.filter(id=item_id) if item_type == "hotel" else Hotel.objects.none()
        hotel_min_price_map = self.get_hotel_min_price_map(hotels)
        context = {
            'request': request,
            'hotel_min_price_map': hotel_min_price_map,
            'view': self
        }
        return Response(FavoriteItemSerializer(favorite, context=context).data, status=201)


class FavoriteItemDetailAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="حذف آیتم از کالکشن",
        operation_description="این API یک آیتم خاص (هتل یا مقاله) را از داخل کالکشن حذف می‌کند.",
        tags=["favorite-panel"],
    )
    def delete(self, request, pk, item_id):
        favorite = get_object_or_404(Favorite, id=item_id, list__id=pk, list__user=request.user)
        favorite.delete()
        return Response(status=204)