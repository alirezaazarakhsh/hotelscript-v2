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
    province = ProvinceSerializer(read_only=True)  # فقط داده‌های ساده JSON برمی‌گرده

    class Meta:
        model = City
        fields = ("id", "name", "slug", "image", "hotels_number", "show_in_homepage", "province")

    hotels_number = serializers.SerializerMethodField()

    def get_hotels_number(self, obj):
        return obj.hotels.count()


# --- Hotel Summary Serializer ---
class HotelSummarySerializer(serializers.ModelSerializer):
    city = CitySerializer(read_only=True)
    type = serializers.CharField(source="type.title", read_only=True)

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
            "rating",
            "reservation_count",
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
