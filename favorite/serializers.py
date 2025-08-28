from rest_framework import serializers
from .models import FavoriteCollection, Favorite
from blog.models import Article
from reservation.models import Hotel, City, Province


# --- Province Serializer ---
class ProvinceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Province
        fields = ("id", "name")


# --- City Serializer ---
class CitySerializer(serializers.ModelSerializer):
    province = serializers.CharField(source="province.name", read_only=True)
    hotels_number = serializers.SerializerMethodField()

    class Meta:
        model = City
        fields = ("id", "name", "slug", "image", "hotels_number", "show_in_homepage", "province")

    def get_hotels_number(self, obj):
        return obj.hotels.count()


# --- Hotel Summary Serializer ---
class HotelSummarySerializer(serializers.ModelSerializer):
    city = CitySerializer(read_only=True)
    type = serializers.CharField(source="type.title", read_only=True)

    original_total_price = serializers.IntegerField(source="get_original_total_price", read_only=True)
    total_price = serializers.IntegerField(source="get_total_price", read_only=True)
    discount_percentage = serializers.IntegerField(source="get_discount_percentage", read_only=True)
    discount_expiry = serializers.DateTimeField(source="get_discount_expiry", read_only=True)
    average_score = serializers.FloatField(source="get_average_score", read_only=True)

    class Meta:
        model = Hotel
        fields = (
            "id",
            "name",
            "slug",
            "city",
            "address",
            "main_image",
            "stars",
            "type",
            "is_special_offer",
            "is_flash_sale",
            "is_best_seller",
            "original_total_price",
            "total_price",
            "discount_percentage",
            "discount_expiry",
            "rating",
            "reservation_count",
            "average_score",
        )


# --- Article Summary Serializer ---
class ArticleSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = ("id", "title", "slug", "summary", "thumbnail", "published_date")


# --- Favorite Item Serializer ---
class FavoriteItemSerializer(serializers.ModelSerializer):
    item_detail = serializers.SerializerMethodField()

    class Meta:
        model = Favorite
        fields = ("id", "item_detail")

    def get_item_detail(self, obj):
        if isinstance(obj.item, Hotel):
            return {
                "type": "hotel",
                **HotelSummarySerializer(obj.item, context=self.context).data
            }
        elif isinstance(obj.item, Article):
            return {
                "type": "article",
                **ArticleSummarySerializer(obj.item, context=self.context).data
            }
        return None


# --- Favorite Collection Serializer ---
class FavoriteCollectionSerializer(serializers.ModelSerializer):
    favorites = FavoriteItemSerializer(many=True, read_only=True)

    class Meta:
        model = FavoriteCollection
        fields = ("id", "title", "favorites")


# --- Favorite Collection Create Serializer ---
class FavoriteCollectionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FavoriteCollection
        fields = ("id", "title")
