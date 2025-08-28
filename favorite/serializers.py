from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType
from .models import FavoriteCollection, Favorite
from blog.models import Article
from reservation.models import Hotel, City, Province, HotelTag
from datetime import datetime


# ------------------ Province ------------------
class ProvinceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Province
        fields = ("id", "name")


# ------------------ City ------------------
class CitySerializer(serializers.ModelSerializer):
    province = serializers.CharField(source="province.name", read_only=True)
    hotels_number = serializers.SerializerMethodField()

    class Meta:
        model = City
        fields = ("id", "name", "slug", "image", "hotels_number", "show_in_homepage", "province")

    def get_hotels_number(self, obj):
        return obj.hotels.count()


# ------------------ Public Tags ------------------
class PublicTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = HotelTag
        fields = ("id", "title")


# ------------------ Hotel Summary ------------------
class HotelSummarySerializer(serializers.ModelSerializer):
    city = CitySerializer(read_only=True)
    residence_type = serializers.CharField(source="type.title", read_only=True)
    price = serializers.SerializerMethodField()
    price_after_discount = serializers.SerializerMethodField()
    discount_percentage = serializers.SerializerMethodField()
    discount_date = serializers.SerializerMethodField()
    average_score = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()
    public_tags = PublicTagSerializer(many=True, read_only=True)
    night_count = serializers.SerializerMethodField()
    rating = serializers.FloatField(read_only=True, default=0.0)
    main_image = serializers.SerializerMethodField()  # Added to handle URLs consistently

    class Meta:
        model = Hotel
        fields = (
            "id", "name", "slug", "city", "address", "main_image", "stars", "residence_type",
            "price", "price_after_discount", "discount_percentage", "discount_date",
            "rating", "average_score", "comment_count", "reservation_count",
            "public_tags", "night_count"
        )

    def get_main_image(self, obj):
        request = self.context.get('request')
        image_url = obj.main_image.url if obj.main_image else ''
        return request.build_absolute_uri(image_url) if request and image_url else f"https://safarnameh24.com{image_url}"

    def get_price(self, obj):
        price_data = self.context.get('hotel_min_price_map', {}).get(obj.id, {})
        return price_data.get('original_total_price', 0)

    def get_price_after_discount(self, obj):
        price_data = self.context.get('hotel_min_price_map', {}).get(obj.id, {})
        return price_data.get('total_price', 0)

    def get_discount_percentage(self, obj):
        price_data = self.context.get('hotel_min_price_map', {}).get(obj.id, {})
        discount_type = price_data.get('discount_type', 'none')
        discount_value = price_data.get('discount_value', 0)
        if discount_type == 'percentage':
            return discount_value
        elif discount_type == 'fixed':
            original_price = price_data.get('original_total_price', 0)
            if original_price > 0:
                return round((discount_value / original_price) * 100, 1)
        return 0

    def get_discount_date(self, obj):
        price_data = self.context.get('hotel_min_price_map', {}).get(obj.id, {})
        discount_date = price_data.get('discount_date', None)
        return discount_date.strftime('%Y-%m-%d') if discount_date else None

    def get_average_score(self, obj):
        view = self.context.get('view')
        if view and hasattr(view, 'get_average_score'):
            return view.get_average_score(obj)
        return getattr(obj, 'average_score', 0.0)

    def get_comment_count(self, obj):
        return getattr(obj, 'get_comment_count', lambda: 0)()

    def get_night_count(self, obj):
        request = self.context.get('request')
        if request:
            check_in = request.query_params.get('check_in')
            check_out = request.query_params.get('check_out')
            if check_in and check_out:
                try:
                    check_in_date = datetime.strptime(check_in, '%Y-%m-%d')
                    check_out_date = datetime.strptime(check_out, '%Y-%m-%d')
                    return (check_out_date - check_in_date).days
                except ValueError:
                    pass
        return 1


# ------------------ Article Summary ------------------
class ArticleSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = ("id", "title", "slug", "summary", "thumbnail", "published_date")


# ------------------ Favorite Item ------------------
class FavoriteItemSerializer(serializers.ModelSerializer):
    item_detail = serializers.SerializerMethodField()

    class Meta:
        model = Favorite
        fields = ("id", "item_detail")

    def get_item_detail(self, obj):
        if isinstance(obj.item, Hotel):
            context = self.context
            return {"type": "hotel", **HotelSummarySerializer(obj.item, context=context).data}
        elif isinstance(obj.item, Article):
            return {"type": "article", **ArticleSummarySerializer(obj.item, context=self.context).data}
        return None


# ------------------ Collection Create ------------------
class FavoriteCollectionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FavoriteCollection
        fields = ("id", "title")


# ------------------ Collection Base ------------------
class BaseFavoriteCollectionSerializer(serializers.ModelSerializer):
    thumbnails = serializers.SerializerMethodField()

    class Meta:
        model = FavoriteCollection
        fields = ("id", "title", "thumbnails")

    def get_thumbnails(self, obj):
        thumbs = []
        request = self.context.get("request")
        for fav in obj.favorites.all()[:3]:
            if isinstance(fav.item, Hotel) and fav.item.main_image:
                url = request.build_absolute_uri(fav.item.main_image.url) if request and fav.item.main_image.url else f"https://safarnameh24.com{fav.item.main_image.url if fav.item.main_image else ''}"
                thumbs.append(url)
            elif isinstance(fav.item, Article) and fav.item.thumbnail:
                url = request.build_absolute_uri(fav.item.thumbnail.url) if request and fav.item.thumbnail.url else f"https://safarnameh24.com{fav.item.thumbnail.url if fav.item.thumbnail else ''}"
                thumbs.append(url)
        return thumbs


# ------------------ Collection With Items ------------------
class FavoriteCollectionDetailSerializer(BaseFavoriteCollectionSerializer):
    favorites = FavoriteItemSerializer(many=True, read_only=True)

    class Meta(BaseFavoriteCollectionSerializer.Meta):
        fields = BaseFavoriteCollectionSerializer.Meta.fields + ("favorites",)