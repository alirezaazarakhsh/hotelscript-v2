from urllib.parse import urljoin
from django.conf import settings
from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType

from blog.models import Article
from reservation.models import Hotel
from .models import FavoriteCollection, Favorite
from blog.serializers import FavoriteArticleSerializer
from reservation.serializers import FavoriteHotelSerializer


class FavoriteCollectionListSerializer(serializers.ModelSerializer):
    images = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = FavoriteCollection
        fields = ('id', 'title', 'images')

    def _abs(self, url: str) -> str:
        if not url:
            return url
        # اگر از قبل absolute است، دست نمی‌زنیم
        if urlparse(url).scheme:
            return url
        # دامنه‌ی هدف: safarnameh24.com
        base = getattr(settings, 'PUBLIC_BASE_URL', 'https://safarnameh24.com').rstrip('/')
        return urljoin(base + '/', url.lstrip('/'))

    def get_images(self, obj):
        images = []
        hotel_type = ContentType.objects.get_for_model(Hotel)
        article_type = ContentType.objects.get_for_model(Article)

        for fav in obj.favorites.all()[:3]:
            if fav.item_content_type_id == hotel_type.id:
                hotel = fav.item
                if hotel and getattr(hotel, 'main_image', None):
                    images.append(self._abs(hotel.main_image.url))
            elif fav.item_content_type_id == article_type.id:
                article = fav.item
                if article and getattr(article, 'thumbnail', None):
                    images.append(self._abs(article.thumbnail.url))
        return images
    
    


class FavoriteCollectionRetrieveSerializer(serializers.ModelSerializer):
    class Meta:
        model = FavoriteCollection
        fields = (
            'id',
            'title',
        )
        extra_kwargs = {
            'id': {
                'read_only': True,
            },
        }


class FavoriteCreateSerializer(serializers.ModelSerializer):
    item_type = serializers.ChoiceField(
        choices=[
            ('hotel', 'Hotel'),
            ('article', 'Article'),
        ],
        write_only=True,
    )

    class Meta:
        model = Favorite
        fields = (
            'list',
            'item_type',
            'item_object_id',
        )

    def validate(self, data):
        """
        اعتبارسنجی داده‌های ورودی برای اطمینان از وجود لیست و آیتم.
        """
        item_type = data.get('item_type')
        item_object_id = data.get('item_object_id')
        list_instance = data.get('list')

        if not list_instance.user == self.context['request'].user:
            raise serializers.ValidationError("شما اجازه دسترسی به این لیست را ندارید.")

        content_type = ContentType.objects.get(model=item_type)
        model_class = content_type.model_class()
        
        try:
            model_class.objects.get(pk=item_object_id)
        except model_class.DoesNotExist:
            raise serializers.ValidationError(f"آیتم {item_type} با شناسه {item_object_id} یافت نشد.")

        return data


class FavoriteSerializer(serializers.ModelSerializer):
    ITEM_SERIALIZER_MAP = {
        'article': FavoriteArticleSerializer,
        'hotel': FavoriteHotelSerializer,
    }
    type = serializers.SerializerMethodField()
    item_data = serializers.SerializerMethodField()

    class Meta:
        model = Favorite
        fields = (
            'id',
            'type',
            'item_data',
        )

    def get_type(self, obj):
        """
        دریافت نوع آیتم (هتل یا مقاله).
        """
        return obj.item_content_type.model

    def get_item_data(self, obj):
        """
        دریافت داده‌های سریالایز شده آیتم بر اساس نوع آن.
        """
        model_name = obj.item_content_type.model
        serializer_class = self.ITEM_SERIALIZER_MAP.get(model_name)
        if serializer_class and obj.item:
            return serializer_class(obj.item, context=self.context).data
        return None