from django.db.models.functions import Round
from django.db.models import (
    Q,
    Min,
    Avg,
    Prefetch,
)
from django.db import (
    transaction,
    IntegrityError,
)
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.exceptions import (
    ValidationError,
)
from rest_framework.permissions import (
    IsAuthenticated,
)
from rest_framework.settings import api_settings
from rest_framework.generics import (
    ListCreateAPIView,
    DestroyAPIView,
    CreateAPIView,
    ListAPIView,
    RetrieveDestroyAPIView,
)
from .models import (
    FavoriteCollection,
    Favorite,
    CustomerClubPrize,
    CustomerClub,
    CustomerReceivedPrize,
)
from .serializers import (
    FavoriteCollectionListSerializer,
    FavoriteCollectionRetrieveSerializer,
    FavoriteCreateSerializer,
    FavoriteSerializer,
    CustomerClubPrizeListSerializer,
)
from blog.models import Article
from reservation.models import Hotel
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


class FavoriteCollectionListCreateView(ListCreateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = FavoriteCollectionListSerializer

    def get_queryset(self):
        queryset = FavoriteCollection.objects.filter(user=self.request.user)

        hotel_type = ContentType.objects.get_for_model(Hotel)
        article_type = ContentType.objects.get_for_model(Article)

        queryset = queryset.prefetch_related(
            Prefetch('favorites', queryset=Favorite.objects.order_by('-created'), to_attr='cached_favorites')
        )

        hotel_ids, article_ids = set(), set()
        for collection in queryset:
            for fav in collection.cached_favorites[:3]:
                if fav.item_content_type_id == hotel_type.id:
                    hotel_ids.add(fav.item_object_id)
                elif fav.item_content_type_id == article_type.id:
                    article_ids.add(fav.item_object_id)

        hotel_map = {h.id: h for h in Hotel.objects.filter(id__in=hotel_ids)}
        article_map = {a.id: a for a in Article.objects.filter(id__in=article_ids)}

        for collection in queryset:
            images = []
            for fav in collection.cached_favorites[:3]:
                if fav.item_content_type_id == hotel_type.id:
                    hotel = hotel_map.get(fav.item_object_id)
                    images.append(hotel.main_image.url if hotel and hotel.main_image else None)
                elif fav.item_content_type_id == article_type.id:
                    article = article_map.get(fav.item_object_id)
                    images.append(article.thumbnail.url if article and article.thumbnail else None)
            collection.images = images

        return queryset

    @swagger_auto_schema(
        operation_summary="لیست و ایجاد مجموعه‌های علاقه‌مندی",
        operation_description="این API برای دریافت لیست مجموعه‌های علاقه‌مندی کاربر و ایجاد مجموعه جدید استفاده می‌شود.",
        tags=['profile']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="ایجاد مجموعه علاقه‌مندی جدید",
        operation_description="با استفاده از این API می‌توانید یک مجموعه علاقه‌مندی جدید برای کاربر جاری ایجاد کنید.",
        request_body=FavoriteCollectionListSerializer,
        responses={201: FavoriteCollectionListSerializer()},
        tags=['profile']
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class FavoriteCollectionRetrieveDestroyView(RetrieveDestroyAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = FavoriteCollectionRetrieveSerializer

    def get_queryset(self):
        return FavoriteCollection.objects.filter(user=self.request.user)

    @swagger_auto_schema(
        operation_summary="دریافت جزئیات مجموعه علاقه‌مندی",
        operation_description="این API اطلاعات مجموعه علاقه‌مندی را به همراه آیتم‌های داخل آن باز می‌گرداند.",
        tags=['profile']
    )
    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="حذف مجموعه علاقه‌مندی",
        operation_description="این API برای حذف یک مجموعه علاقه‌مندی مشخص استفاده می‌شود.",
        tags=['profile']
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        collection = self.get_object()
        collection_data = self.get_serializer(collection).data
        favorites = Favorite.objects.filter(list=collection).order_by('-created')

        paginator = api_settings.DEFAULT_PAGINATION_CLASS()
        paginated_favorites = paginator.paginate_queryset(favorites, request)

        hotel_type = ContentType.objects.get_for_model(Hotel)
        article_type = ContentType.objects.get_for_model(Article)

        hotel_ids = [fav.item_object_id for fav in paginated_favorites if fav.item_content_type == hotel_type]
        article_ids = [fav.item_object_id for fav in paginated_favorites if fav.item_content_type == article_type]

        hotels = Hotel.objects.filter(id__in=hotel_ids).select_related('city__province')\
            .prefetch_related('comments__points', 'rooms__dates')\
            .annotate(
                min_price=Min('rooms__dates__price'),
                rating=Round(Avg('comments__points__point', filter=Q(comments__is_approved=True)), precision=1),
            )
        articles = Article.objects.filter(id__in=article_ids)

        hotel_map = {hotel.id: hotel for hotel in hotels}
        article_map = {article.id: article for article in articles}

        for fav in paginated_favorites:
            if fav.item_content_type == hotel_type:
                fav.item = hotel_map.get(fav.item_object_id)
            elif fav.item_content_type == article_type:
                fav.item = article_map.get(fav.item_object_id)

        collection_data['favorites'] = FavoriteSerializer(paginated_favorites, many=True, context=self.get_serializer_context()).data
        return paginator.get_paginated_response(collection_data)


class FavoriteCreateView(CreateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = FavoriteCreateSerializer

    def get_queryset(self):
        return Favorite.objects.select_related('list').filter(list__user=self.request.user)

    @swagger_auto_schema(
        operation_summary="افزودن آیتم به علاقه‌مندی‌ها",
        operation_description="با استفاده از این API می‌توانید یک آیتم (هتل یا مقاله) را به علاقه‌مندی‌ها اضافه کنید.",
        request_body=FavoriteCreateSerializer,
        responses={201: FavoriteSerializer()},
        tags=['profile']
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def perform_create(self, serializer):
        item_type = serializer.validated_data.pop('item_type')
        item_object_id = serializer.validated_data.get('item_object_id')
        content_type = ContentType.objects.get(model=item_type)

        if Favorite.objects.filter(list__user=self.request.user, item_content_type=content_type, item_object_id=item_object_id).exists():
            raise ValidationError('این آیتم قبلاً در یکی از لیست‌های علاقه‌مندی شما ثبت شده است.')

        try:
            content_type.model_class().objects.get(pk=item_object_id)
        except ObjectDoesNotExist:
            raise ValidationError("آیتم مورد نظر وجود ندارد.")

        serializer.validated_data['item_content_type'] = content_type
        return super().perform_create(serializer)


class FavoriteDestroyView(DestroyAPIView):
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Favorite.objects.select_related('list').filter(list__user=self.request.user)

    @swagger_auto_schema(
        operation_summary="حذف آیتم علاقه‌مندی",
        operation_description="با استفاده از این API می‌توانید یک آیتم را از علاقه‌مندی‌ها حذف کنید.",
        tags=['profile']
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


class CustomerClubPrizeListView(ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = CustomerClubPrizeListSerializer

    def get_queryset(self):
        return CustomerClubPrize.objects.filter(type=self.request.query_params.get('type'))

    @swagger_auto_schema(
        operation_summary="لیست جوایز باشگاه مشتریان",
        operation_description="دریافت لیستی از جوایز با نوع مشخص‌شده.",
        manual_parameters=[
            openapi.Parameter(
                'type', openapi.IN_QUERY, description="نوع جایزه (hotel یا shopping-center)", type=openapi.TYPE_STRING, required=True
            )
        ],
        tags=['profile']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class CustomerReceivedPrizeListCreateView(ListCreateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = CustomerClubPrizeListSerializer

    def get_queryset(self):
        return CustomerReceivedPrize.objects.filter(customer_id=self.request.user).select_related('customer')

    @swagger_auto_schema(
        operation_summary="لیست جوایز دریافتی",
        operation_description="لیست جوایز دریافتی کاربر را باز می‌گرداند یا جایزه‌ای جدید برای وی ثبت می‌کند.",
        tags=['profile']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="دریافت جایزه جدید",
        operation_description="اگر امتیاز کافی داشته باشید، می‌توانید جایزه‌ای جدید دریافت کنید.",
        request_body=openapi.Schema(type=openapi.TYPE_OBJECT, properties={
            'prize': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID جایزه')
        }),
        responses={201: 'جایزه با موفقیت دریافت شد.'},
        tags=['profile']
    )
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        user = self.request.user
        customer_club = CustomerClub.objects.get(user=user)
        prize = CustomerClubPrize.objects.get(id=request.data.get('prize'))

        if customer_club.points < prize.required_points:
            raise ValidationError('شما امتیاز کافی برای دریافت جایزه را ندارید!')

        try:
            CustomerReceivedPrize.objects.create(customer=user, prize=prize)
            customer_club.points -= prize.required_points
            customer_club.save()
        except IntegrityError:
            raise ValidationError('شما قبلا این جایزه را دریافت کردید!')

        return super().post(request, *args, **kwargs)
