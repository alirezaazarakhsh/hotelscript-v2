from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from drf_yasg.utils import swagger_auto_schema
from django.shortcuts import get_object_or_404
from drf_yasg import openapi
from django.contrib.contenttypes.models import ContentType
from rest_framework.pagination import PageNumberPagination
from blog.models import Article
from reservation.models import Hotel
from .serializers import (
    FavoriteCollectionCreateSerializer,
    FavoriteCollectionDetailSerializer,
    BaseFavoriteCollectionSerializer,
    FavoriteItemSerializer,
    HotelSummarySerializer,
)
from django.db.models import Avg
from datetime import timedelta, datetime
from .models import FavoriteCollection, Favorite
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

# ------------------ لیست کالکشن‌ها ------------------
class FavoriteCollectionPagination(PageNumberPagination):
    page_size = 10  # Number of collections per page
    page_size_query_param = 'page_size'
    max_page_size = 100

class FavoriteCollectionListCreateAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="دریافت لیست کالکشن‌های علاقه‌مندی",
        operation_description="""
        این API تمامی کالکشن‌های علاقه‌مندی (چه هتل و چه مقاله) را نمایش می‌دهد.
        هر کالکشن شامل شناسه، عنوان و تعدادی تصویر thumbnail از آیتم‌های داخل لیست است.
        """,
        tags=["favorite-panel"],
        responses={200: BaseFavoriteCollectionSerializer(many=True)},
    )
    def get(self, request):
        collections = FavoriteCollection.objects.filter(user=request.user)
        serializer = BaseFavoriteCollectionSerializer(collections, many=True, context={"request": request})
        return Response(serializer.data)

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
        # چک محدودیت تعداد کالکشن‌ها
        if FavoriteCollection.objects.filter(user=request.user).count() >= 10:
            return Response({"error": "شما نمی‌توانید بیش از ۱۰ کالکشن ایجاد کنید."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = FavoriteCollectionCreateSerializer(data=request.data)
        if serializer.is_valid():
            title = serializer.validated_data['title']
            # چک عنوان تکراری
            if FavoriteCollection.objects.filter(user=request.user, title=title).exists():
                return Response({"error": "کالکشن با این عنوان قبلاً وجود دارد."}, status=status.HTTP_400_BAD_REQUEST)
            
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
        today = timezone.now().date()
        check_in = self.request.query_params.get('check_in')
        check_out = self.request.query_params.get('check_out')
        start_date = today
        end_date = today + timedelta(days=1)

        if check_in and check_out:
            try:
                start_date = datetime.strptime(check_in, '%Y-%m-%d').date()
                end_date = datetime.strptime(check_out, '%Y-%m-%d').date()
            except ValueError:
                logger.warning(f"Invalid date format: check_in={check_in}, check_out={check_out}")
                start_date = today
                end_date = today + timedelta(days=1)

        logger.debug(f"Processing hotels for price calculation. Start date: {start_date}, End date: {end_date}")

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
                    start_date__lte=end_date,
                    end_date__gte=start_date
                )
                logger.debug(f"Hotel {hotel.id}, Room {room.id}: Found {date_prices.count()} date prices for range {start_date} to {end_date}")

                if not date_prices.exists():
                    date_prices = room.date_prices.filter(
                        end_date__gte=today
                    ).order_by('price')
                    logger.debug(f"Hotel {hotel.id}, Room {room.id}: Fallback to {date_prices.count()} valid date prices after {today}")

                for date_price in date_prices:
                    original_price = date_price.price or 0
                    logger.debug(f"Hotel {hotel.id}, Room {room.id}: Found price {original_price} for date range")
                    total_price = original_price
                    discount_type = getattr(date_price, 'discount_type', 'none')
                    discount_value = getattr(date_price, 'discount_value', 0)
                    discount_date = getattr(date_price, 'discount_date', None)

                    if original_price > 0:
                        if discount_type == 'percentage' and discount_date and discount_date >= today:
                            total_price = original_price * (1 - discount_value / 100)
                        elif discount_type == 'fixed' and getattr(date_price, 'is_fixed_discount_one_time', False):
                            total_price = max(0, original_price - discount_value)

                        if total_price < min_total_price:
                            min_total_price = total_price
                            min_price_data = {
                                'total_price': int(total_price),
                                'original_total_price': int(original_price),
                                'discount_type': discount_type,
                                'discount_value': discount_value,
                                'discount_date': discount_date,
                            }

            if min_total_price == float('inf'):
                logger.warning(f"Hotel {hotel.id}: No valid RoomDatePrice found with non-zero price")
                fallback_prices = room.date_prices.filter(price__gt=0).order_by('price').first()
                if fallback_prices:
                    min_price_data = {
                        'total_price': int(fallback_prices.price),
                        'original_total_price': int(fallback_prices.price),
                        'discount_type': 'none',
                        'discount_value': 0,
                        'discount_date': None,
                    }
                    logger.debug(f"Hotel {hotel.id}: Using fallback price {fallback_prices.price}")
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
        شامل لیست کامل آیتم‌ها (هتل یا مقاله) به همراه اطلاعات خلاصه هر آیتم.
        آیتم‌ها به صورت صفحه‌بندی شده ارائه می‌شوند.
        """,
        tags=["favorite-panel"],
        responses={200: FavoriteCollectionDetailSerializer},
    )
    def get(self, request, pk):
        collection = get_object_or_404(FavoriteCollection, id=pk, user=request.user)
        favorites = Favorite.objects.filter(list=collection).select_related('item_content_type')

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(favorites, request)

        hotel_ids = [f.item_object_id for f in page if isinstance(f.item, Hotel)]
        hotel_min_price_map = {}
        if hotel_ids:
            hotels = Hotel.objects.filter(id__in=hotel_ids).select_related('city', 'type').distinct()
            hotel_min_price_map = self.get_hotel_min_price_map(hotels)

        context = {
            'request': request,
            'hotel_min_price_map': hotel_min_price_map,
            'view': self
        }

        serializer = FavoriteCollectionDetailSerializer(collection, context=context)
        return paginator.get_paginated_response(serializer.data)

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
class FavoriteItemPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class FavoriteItemListCreateAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = FavoriteItemPagination

    def get_hotel_min_price_map(self, hotels):
        hotel_min_price_map = {}
        today = timezone.now().date()
        check_in = self.request.query_params.get('check_in')
        check_out = self.request.query_params.get('check_out')
        start_date = today
        end_date = today + timedelta(days=1)

        if check_in and check_out:
            try:
                start_date = datetime.strptime(check_in, '%Y-%m-%d').date()
                end_date = datetime.strptime(check_out, '%Y-%m-%d').date()
            except ValueError:
                logger.warning(f"Invalid date format: check_in={check_in}, check_out={check_out}")

        logger.debug(f"Processing hotels for price calculation. Start date: {start_date}, End date: {end_date}")

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
                    start_date__lte=end_date,
                    end_date__gte=start_date
                )
                logger.debug(f"Hotel {hotel.id}, Room {room.id}: Found {date_prices.count()} date prices for range {start_date} to {end_date}")

                if not date_prices.exists():
                    date_prices = room.date_prices.filter(
                        end_date__gte=today
                    ).order_by('price')
                    logger.debug(f"Hotel {hotel.id}, Room {room.id}: Fallback to {date_prices.count()} valid date prices after {today}")

                for date_price in date_prices:
                    original_price = date_price.price or 0
                    logger.debug(f"Hotel {hotel.id}, Room {room.id}: Found price {original_price} for date range")
                    total_price = original_price
                    discount_type = getattr(date_price, 'discount_type', 'none')
                    discount_value = getattr(date_price, 'discount_value', 0)
                    discount_date = getattr(date_price, 'discount_date', None)

                    if original_price > 0:
                        if discount_type == 'percentage' and discount_date and discount_date >= today:
                            total_price = original_price * (1 - discount_value / 100)
                        elif discount_type == 'fixed' and getattr(date_price, 'is_fixed_discount_one_time', False):
                            total_price = max(0, original_price - discount_value)

                        if total_price < min_total_price:
                            min_total_price = total_price
                            min_price_data = {
                                'total_price': int(total_price),
                                'original_total_price': int(original_price),
                                'discount_type': discount_type,
                                'discount_value': discount_value,
                                'discount_date': discount_date,
                            }

            if min_total_price == float('inf'):
                logger.warning(f"Hotel {hotel.id}: No valid RoomDatePrice found with non-zero price")
                fallback_prices = room.date_prices.filter(price__gt=0).order_by('price').first()
                if fallback_prices:
                    min_price_data = {
                        'total_price': int(fallback_prices.price),
                        'original_total_price': int(fallback_prices.price),
                        'discount_type': 'none',
                        'discount_value': 0,
                        'discount_date': None,
                    }
                    logger.debug(f"Hotel {hotel.id}: Using fallback price {fallback_prices.price}")
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
        operation_description="این API تمامی آیتم‌های (هتل یا مقاله) داخل یک کالکشن خاص را نمایش می‌دهد. آیتم‌ها به صورت صفحه‌بندی شده ارائه می‌شوند.",
        tags=["favorite-panel"],
        responses={200: FavoriteItemSerializer(many=True)},
    )
    def get(self, request, pk):
        collection = get_object_or_404(FavoriteCollection, id=pk, user=request.user)
        favorites = collection.favorites.all()

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(favorites, request)

        hotel_content_type = ContentType.objects.get_for_model(Hotel)
        favorite_hotels = [f.item_object_id for f in page if f.item_content_type == hotel_content_type]
        hotels = Hotel.objects.filter(id__in=favorite_hotels).select_related('city', 'type').distinct()
        hotel_min_price_map = self.get_hotel_min_price_map(hotels)
        context = {
            'request': request,
            'hotel_min_price_map': hotel_min_price_map,
            'view': self
        }
        serializer = FavoriteItemSerializer(page, many=True, context=context)
        return paginator.get_paginated_response(serializer.data)

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

# ------------------ حذف آیتم از کالکشن در پنل ------------------
class FavoriteItemDetailAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="حذف آیتم از کالکشن",
        operation_description="""
        این API یک آیتم خاص (هتل یا مقاله) را از یک کالکشن مشخص حذف می‌کند.
        - `pk`: شناسه کالکشن (مثل 322).
        - `item_id`: شناسه ردیف Favorite (مثل 14، همان id نمایش‌داده‌شده در لیست آیتم‌ها).
        - `type`: نوع آیتم (hotel یا article) که باید به صورت پارامتر کویری در URL ارسال شود.
        مثال درخواست:
        ```
        DELETE /api/v1/favorite/collections/322/items/14/?type=hotel
        ```
        """,
        tags=["favorite-panel"],
        manual_parameters=[
            openapi.Parameter(
                "type", openapi.IN_QUERY, description="نوع آیتم: hotel یا article", type=openapi.TYPE_STRING, required=True
            )
        ],
        responses={
            204: openapi.Schema(type=openapi.TYPE_OBJECT, description="آیتم با موفقیت حذف شد"),
            400: openapi.Schema(type=openapi.TYPE_OBJECT, description="نوع آیتم نامعتبر است"),
            404: openapi.Schema(type=openapi.TYPE_OBJECT, description="آیتم یا کالکشن یافت نشد")
        }
    )
    def delete(self, request, pk, item_id):
        item_type = request.query_params.get("type")
        if item_type not in ["hotel", "article"]:
            return Response({"error": "نوع آیتم نامعتبر است"}, status=status.HTTP_400_BAD_REQUEST)

        content_type = get_object_or_404(ContentType, model=item_type)
        favorite = get_object_or_404(Favorite, id=item_id, list__id=pk, list__user=request.user, item_content_type=content_type)
        favorite.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    
    
#------------------- حذف ایتم کالکشن در سایت ------------------------
class FavoriteItemDeleteAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="حذف آیتم از کالکشن در سایت",
        operation_description="""
        این API یک آیتم خاص (هتل یا مقاله) را بر اساس شناسه هتل یا مقاله از کالکشن‌های کاربر در سایت حذف می‌کند.
        اگر آیتم در چندین کالکشن وجود داشته باشد، از همه حذف می‌شود.
        - `item_id`: شناسه هتل یا مقاله (مثل 3 برای هتل).
        - `type`: نوع آیتم (hotel یا article) که باید به صورت پارامتر کویری در URL ارسال شود.
        مثال درخواست:
        ```
        DELETE /api/v1/favorite/items/3/?type=hotel
        ```
        """,
        tags=["favorite-website"],
        manual_parameters=[
            openapi.Parameter(
                "type", openapi.IN_QUERY, description="نوع آیتم: hotel یا article", type=openapi.TYPE_STRING, required=True
            )
        ],
        responses={
            204: openapi.Schema(type=openapi.TYPE_OBJECT, description="آیتم با موفقیت حذف شد"),
            400: openapi.Schema(type=openapi.TYPE_OBJECT, description="نوع آیتم نامعتبر است"),
            404: openapi.Schema(type=openapi.TYPE_OBJECT, description="آیتم یافت نشد")
        }
    )
    def delete(self, request, item_id):
        item_type = request.query_params.get("type")
        if item_type not in ["hotel", "article"]:
            return Response({"error": "نوع آیتم نامعتبر است"}, status=status.HTTP_400_BAD_REQUEST)

        content_type = get_object_or_404(ContentType, model=item_type)
        favorites = Favorite.objects.filter(item_object_id=item_id, item_content_type=content_type, list__user=request.user)
        
        if not favorites.exists():
            return Response({"error": "آیتم یافت نشد"}, status=status.HTTP_404_NOT_FOUND)
        
        favorites.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# ------------------ به‌روزرسانی عنوان کالکشن ------------------
class FavoriteCollectionUpdateTitleAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="به‌روزرسانی عنوان کالکشن",
        operation_description="این API امکان تغییر عنوان یک کالکشن علاقه‌مندی را فراهم می‌کند.",
        tags=["favorite-panel"],
        request_body=FavoriteCollectionCreateSerializer,
        responses={200: FavoriteCollectionCreateSerializer},
    )
    def put(self, request, pk):
        collection = get_object_or_404(FavoriteCollection, id=pk, user=request.user)
        serializer = FavoriteCollectionCreateSerializer(collection, data=request.data, partial=True)
        if serializer.is_valid():
            title = serializer.validated_data.get('title')
            if title and FavoriteCollection.objects.filter(user=request.user, title=title).exclude(id=pk).exists():
                return Response({"error": "کالکشن با این عنوان قبلاً وجود دارد."}, status=status.HTTP_400_BAD_REQUEST)
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)
    
    
    
#---------------------- لیست ایتم های علاقه مندی در وب سایت ------------------------------------
logger = logging.getLogger(__name__)

class FavoriteCollectionWebsiteListAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="دریافت لیست کالکشن‌های علاقه‌مندی در وب‌سایت",
        operation_description="""
        این API لیست تمام کالکشن‌های علاقه‌مندی کاربر را برای وب‌سایت نمایش می‌دهد.
        هر کالکشن شامل شناسه، نام، یک تصویر thumbnail از اولین آیتم کالکشن (در صورت وجود) و تعداد آیتم‌های داخل کالکشن است.
        مثال درخواست:
        ```
        GET /api/v1/favorite/website/collections/
        ```
        """,
        tags=["favorite-website"],
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Items(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "id": openapi.Schema(type=openapi.TYPE_INTEGER, description="شناسه کالکشن"),
                        "name": openapi.Schema(type=openapi.TYPE_STRING, description="نام کالکشن"),
                        "thumbnail": openapi.Schema(type=openapi.TYPE_STRING, description="URL تصویر thumbnail اولین آیتم یا null"),
                        "item_count": openapi.Schema(type=openapi.TYPE_INTEGER, description="تعداد آیتم‌های داخل کالکشن"),
                    }
                )
            )
        }
    )
    def get(self, request):
        collections = FavoriteCollection.objects.filter(user=request.user)
        result = []

        for collection in collections:
            item_count = Favorite.objects.filter(list=collection).count()
            
            # گرفتن اولین آیتم برای thumbnail
            first_item = Favorite.objects.filter(list=collection).first()
            thumbnail = None
            if first_item:
                try:
                    item_object = first_item.item
                    if item_object:
                        logger.info(f"Item found for collection {collection.id}: {item_object}, content_type: {first_item.item_content_type}")
                        # چک کردن نوع آیتم (hotel یا article)
                        if first_item.item_content_type.model == 'hotel':
                            thumbnail = getattr(item_object, 'main_image', None)
                        else:  # فرض بر article
                            thumbnail = getattr(item_object, 'thumbnail', None)
                        
                        if thumbnail and hasattr(thumbnail, 'url'):
                            thumbnail = request.build_absolute_uri(thumbnail.url)
                        else:
                            logger.warning(f"No valid image field for item {item_object} in collection {collection.id}")
                    else:
                        logger.warning(f"No item_object for favorite {first_item.id} in collection {collection.id}")
                except (AttributeError, ValueError) as e:
                    logger.error(f"Error accessing item or image for collection {collection.id}: {str(e)}")
                    pass

            data = {
                "id": collection.id,
                "name": collection.title,
                "thumbnail": thumbnail,
                "item_count": item_count
            }
            result.append(data)

        return Response(result)
    
    
    
    
# ------------------ بررسی وضعیت علاقه‌مندی آیتم ------------------
class FavoriteItemStatusAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="بررسی وضعیت علاقه‌مندی آیتم",
        operation_description="این API بررسی می‌کند که یک آیتم (هتل یا مقاله) در لیست علاقه‌مندی‌های کاربر موجود است یا خیر.",
        tags=["favorite-website"],
        manual_parameters=[
            openapi.Parameter(
                "type", openapi.IN_QUERY, description="نوع آیتم: hotel یا article", type=openapi.TYPE_STRING, required=True
            )
        ],
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "is_favorited": openapi.Schema(type=openapi.TYPE_BOOLEAN, description="وضعیت علاقه‌مندی آیتم"),
                    "type": openapi.Schema(type=openapi.TYPE_STRING, description="نوع آیتم: hotel یا article")
                }
            )
        }
    )
    def get(self, request, item_id):
        item_type = request.query_params.get("type")
        if item_type not in ["hotel", "article"]:
            return Response({"error": "نوع آیتم معتبر نیست"}, status=status.HTTP_400_BAD_REQUEST)

        model = Hotel if item_type == "hotel" else Article
        content_type = ContentType.objects.get_for_model(model)

        is_favorited = Favorite.objects.filter(
            list__user=request.user,
            item_content_type=content_type,
            item_object_id=item_id,
            is_active=True,
        ).exists()

        return Response({
            "is_favorited": is_favorited,
            "type": item_type
        }, status=status.HTTP_200_OK)