from django.db.models.functions import Round
from django.db.models import (
    Q,
    Min,
    Avg,
    Prefetch,
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
)
from .serializers import (
    FavoriteCollectionListSerializer,
    FavoriteCollectionRetrieveSerializer,
    FavoriteCreateSerializer,
    FavoriteSerializer,
)
from blog.models import Article
from reservation.models import Hotel

# Create your views here.
class FavoriteCollectionListCreateView(ListCreateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = FavoriteCollectionListSerializer

    def get_queryset(self):
        queryset = FavoriteCollection.objects.filter(
            user=self.request.user
        )

        hotel_type = ContentType.objects.get_for_model(Hotel)
        article_type = ContentType.objects.get_for_model(Article)

        queryset = queryset.prefetch_related(
            Prefetch(
                'favorites',
                queryset=Favorite.objects.order_by('-created'),
                to_attr='cached_favorites'
            ),
        )

        hotel_ids = set()
        article_ids = set()
        for collection in queryset:
            recent_favs = collection.cached_favorites[:3]
            for fav in recent_favs:
                if fav.item_content_type_id == hotel_type.id:
                    hotel_ids.add(fav.item_object_id)
                elif fav.item_content_type_id == article_type.id:
                    article_ids.add(fav.item_object_id)

        hotels = Hotel.objects.filter(id__in=hotel_ids)
        articles = Article.objects.filter(id__in=article_ids)

        hotel_map = {hotel.id: hotel for hotel in hotels}
        article_map = {article.id: article for article in articles}

        for collection in queryset:
            images = []
            for fav in collection.cached_favorites[:3]:
                if fav.item_content_type_id == hotel_type.id:
                    hotel = hotel_map.get(fav.item_object_id)
                    if hotel:
                        images.append(hotel.main_image.url if hotel.main_image else None)
                elif fav.item_content_type_id == article_type.id:
                    article = article_map.get(fav.item_object_id)
                    if article:
                        images.append(article.thumbnail.url if article.thumbnail else None)
            collection.images = images

        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class FavoriteCollectionRetrieveDestroyView(RetrieveDestroyAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = FavoriteCollectionRetrieveSerializer

    def get_queryset(self):
        queryset = FavoriteCollection.objects.filter(
            user=self.request.user,
        )

        return queryset
    
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

class FavoriteCreateView(CreateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = FavoriteCreateSerializer

    def get_queryset(self):
        queryset = Favorite.objects.select_related('list')\
            .filter(list__user__id=self.request.user.pk)

        return queryset
    
    def perform_create(self, serializer):
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
        
        try:
            model_class = content_type.model_class()
            model_class.objects.get(pk=item_object_id)
        except ObjectDoesNotExist:
            raise ValidationError("آیتم مورد نظر وجود ندارد.")
        
        serializer.validated_data['item_content_type'] = content_type

        return super().perform_create(serializer)

class FavoriteDestroyView(DestroyAPIView):
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        queryset = Favorite.objects.select_related('list')\
            .filter(list__user__id=self.request.user.pk)

        return queryset
