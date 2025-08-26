from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import ListCreateAPIView, RetrieveDestroyAPIView, CreateAPIView, DestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType
from django.db.models import Avg, Min, Q
from rest_framework.settings import api_settings
from django.db.models import Prefetch
from django.db.models.functions import Round
from .models import FavoriteCollection, Favorite
from .serializers import (
    FavoriteCollectionListSerializer,
    FavoriteCollectionRetrieveSerializer,
    FavoriteCreateSerializer,
    FavoriteSerializer,
)
from blog.models import Article
from reservation.models import Hotel


class FavoriteCollectionListCreateView(ListCreateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = FavoriteCollectionListSerializer

    def get_queryset(self):
        """
        بازگرداندن لیست مجموعه‌های علاقه‌مندی کاربر.
        """
        queryset = FavoriteCollection.objects.filter(user=self.request.user).prefetch_related('favorites')
        return queryset

    @swagger_auto_schema(
        operation_summary="لیست مجموعه‌های علاقه‌مندی",
        operation_description="""
        این API به کاربر اجازه می‌دهد تا:
        - لیست مجموعه‌های علاقه‌مندی خود را مشاهده کند
        - اطلاعات مجموعه‌ها شامل عنوان و تصاویر مرتبط با سه آیتم اخیر را دریافت کند
        """,
        responses={
            200: FavoriteCollectionListSerializer(many=True),
        },
        tags=['Favorite']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="ایجاد مجموعه علاقه‌مندی جدید",
        operation_description="""
        با استفاده از این API می‌توانید یک مجموعه علاقه‌مندی جدید با عنوان مشخص ایجاد کنید.
        """,
        request_body=FavoriteCollectionListSerializer,
        responses={201: FavoriteCollectionListSerializer()},
        tags=['Favorite']
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def perform_create(self, serializer):
        """
        ذخیره مجموعه علاقه‌مندی جدید با اختصاص کاربر فعلی.
        """
        serializer.save(user=self.request.user)


class FavoriteCollectionRetrieveDestroyView(RetrieveDestroyAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = FavoriteCollectionRetrieveSerializer

    def get_queryset(self):
        """
        بازگرداندن مجموعه‌های علاقه‌مندی کاربر.
        """
        queryset = FavoriteCollection.objects.filter(user=self.request.user)
        return queryset

    @swagger_auto_schema(
        operation_summary="مشاهده جزئیات مجموعه علاقه‌مندی",
        operation_description="""
        این API به کاربر اجازه می‌دهد تا:
        - جزئیات یک مجموعه علاقه‌مندی خاص را مشاهده کند
        - لیست آیتم‌های موجود در مجموعه را به صورت صفحه‌بندی شده دریافت کند
        """,
        responses={
            200: FavoriteCollectionRetrieveSerializer(),
        },
        tags=['Favorite']
    )
    def get(self, request, *args, **kwargs):
        collection = self.get_object()
        collection_data = self.get_serializer(collection).data

        favorites = Favorite.objects.filter(list=collection).order_by('-created')

        paginator = api_settings.DEFAULT_PAGINATION_CLASS()
        paginated_favorites = paginator.paginate_queryset(favorites, request)

        hotel_type = ContentType.objects.get_for_model(Hotel)
        article_type = ContentType.objects.get_for_model(Article)

        hotel_ids = [fav.item_object_id for fav in paginated_favorites if fav.item_content_type == hotel_type]
        article_ids = [fav.item_object_id for fav in paginated_favorites if fav.item_content_type == article_type]

        hotels = Hotel.objects.filter(id__in=hotel_ids)\
            .select_related('city')\
            .select_related('city__province')\
            .prefetch_related('comments__points')\
            .prefetch_related('rooms__dates')\
            .annotate(
                min_price=Min('rooms__dates__price'),
                rating=Round(
                    Avg('comments__points__point', filter=Q(comments__is_approved=True)),
                    precision=1
                ),
            )
        articles = Article.objects.filter(id__in=article_ids)

        hotel_map = {hotel.id: hotel for hotel in hotels}
        article_map = {article.id: article for article in articles}

        for fav in paginated_favorites:
            if fav.item_content_type == hotel_type:
                fav.item = hotel_map.get(fav.item_object_id)
            elif fav.item_content_type == article_type:
                fav.item = article_map.get(fav.item_object_id)

        favorites_data = FavoriteSerializer(paginated_favorites, many=True, context=self.get_serializer_context()).data

        collection_data['favorites'] = favorites_data
        return paginator.get_paginated_response(collection_data)

    @swagger_auto_schema(
        operation_summary="حذف مجموعه علاقه‌مندی",
        operation_description="""
        با استفاده از این API می‌توانید یک مجموعه علاقه‌مندی را حذف کنید.
        """,
        responses={204: 'No Content'},
        tags=['Favorite']
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


class FavoriteCreateView(CreateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = FavoriteCreateSerializer

    def get_queryset(self):
        """
        بازگرداندن لیست علاقه‌مندی‌های کاربر.
        """
        queryset = Favorite.objects.select_related('list').filter(list__user=self.request.user)
        return queryset

    @swagger_auto_schema(
        operation_summary="افزودن آیتم به لیست علاقه‌مندی",
        operation_description="""
        با استفاده از این API می‌توانید یک آیتم (هتل یا مقاله) را به یک لیست علاقه‌مندی اضافه کنید.
        در صورت وجود آیتم در یکی از لیست‌های علاقه‌مندی کاربر یا عدم وجود آیتم، خطا دریافت خواهید کرد.
        """,
        request_body=FavoriteCreateSerializer,
        responses={201: FavoriteSerializer()},
        tags=['Favorite']
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def perform_create(self, serializer):
        """
        ایجاد آیتم علاقه‌مندی جدید با اعتبارسنجی وجود آیتم و عدم تکرار.
        """
        item_type = serializer.validated_data.pop('item_type')
        item_object_id = serializer.validated_data.get('item_object_id')
        content_type = ContentType.objects.get(model=item_type)

        existing = Favorite.objects.filter(
            list__user=self.request.user,
            item_content_type=content_type,
            item_object_id=item_object_id,
        ).exists()

        if existing:
            raise ValidationError('این آیتم قبلاً در یکی از لیست‌های علاقه‌مندی شما ثبت شده است.')

        serializer.validated_data['item_content_type'] = content_type
        serializer.save()


class FavoriteDestroyView(DestroyAPIView):
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        """
        بازگرداندن لیست علاقه‌مندی‌های کاربر.
        """
        queryset = Favorite.objects.select_related('list').filter(list__user=self.request.user)
        return queryset

    @swagger_auto_schema(
        operation_summary="حذف آیتم از لیست علاقه‌مندی",
        operation_description="""
        با استفاده از این API می‌توانید یک آیتم را از لیست علاقه‌مندی حذف کنید.
        """,
        responses={204: 'No Content'},
        tags=['Favorite']
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)