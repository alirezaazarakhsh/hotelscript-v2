from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType
from .models import FavoriteCollection, Favorite
from blog.models import Article
from reservation.models import Hotel, City, Province, HotelTag  # Updated to import HotelTag


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
        model = HotelTag  # Updated to use HotelTag
        fields = ("id", "title")


# ------------------ Hotel Summary ------------------
class HotelSummarySerializer(serializers.ModelSerializer):
    city = CitySerializer(read_only=True)
    residence_type = serializers.CharField(source="type.title", read_only=True)
    price = serializers.IntegerField(source="get_original_total_price", read_only=True, default=0)
    price_after_discount = serializers.IntegerField(source="get_total_price", read_only=True, default=0)
    discount_percentage = serializers.IntegerField(source="get_discount_percentage", read_only=True, default=0)
    discount_date = serializers.DateTimeField(source="get_discount_expiry", read_only=True, allow_null=True)
    average_score = serializers.FloatField(source="get_average_score", read_only=True, default=0.0)
    comment_count = serializers.IntegerField(source="get_comment_count", read_only=True, default=0)
    public_tags = PublicTagSerializer(many=True, read_only=True)
    night_count = serializers.SerializerMethodField()
    rating = serializers.FloatField(read_only=True, default=0.0)  # Ensure rating is a float

    class Meta:
        model = Hotel
        fields = (
            "id", "name", "slug", "city", "address", "main_image", "stars", "residence_type",
            "price", "price_after_discount", "discount_percentage", "discount_date",
            "rating", "average_score", "comment_count", "reservation_count",
            "public_tags", "night_count"
        )

    def get_night_count(self, obj):
        # Example: Get night_count from query params or default to 0
        request = self.context.get("request")
        return int(request.query_params.get("night_count", 0)) if request else 0


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
            return {"type": "hotel", **HotelSummarySerializer(obj.item, context=self.context).data}
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
                url = request.build_absolute_uri(fav.item.main_image.url) if request else fav.item.main_image.url
                thumbs.append(url)
            elif isinstance(fav.item, Article) and fav.item.thumbnail:
                url = request.build_absolute_uri(fav.item.thumbnail.url) if request else fav.item.thumbnail.url
                thumbs.append(url)
        return thumbs


# ------------------ Collection With Items ------------------
class FavoriteCollectionDetailSerializer(BaseFavoriteCollectionSerializer):
    favorites = FavoriteItemSerializer(many=True, read_only=True)

    class Meta(BaseFavoriteCollectionSerializer.Meta):
        fields = BaseFavoriteCollectionSerializer.Meta.fields + ("favorites",)