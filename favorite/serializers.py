from rest_framework import serializers
from .models import FavoriteCollection, Favorite
from blog.models import Article
from reservation.models import Hotel


# --- Hotel Summary ---
class HotelSummarySerializer(serializers.ModelSerializer):
    city = serializers.SerializerMethodField()
    type = serializers.CharField(source='type.title', read_only=True)

    class Meta:
        model = Hotel
        fields = (
            "name", "slug", "city", "address", "main_image",
            "stars", "type", "is_special_offer", "is_flash_sale",
            "is_best_seller", "rating", "reservation_count",
        )

    def get_city(self, obj):
        return {
            "id": obj.city.id,
            "image": obj.city.image.url if obj.city.image else None,
            "name": obj.city.name,
            "province": obj.city.province,
            "slug": obj.city.slug,
            "hotels_number": obj.city.hotels.count(),
            "show_in_homepage": obj.city.show_in_homepage,
        }


# --- Article Summary ---
class ArticleSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = ("title", "slug", "summary", "thumbnail", "published_date")


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


# --- Collection Serializer ---
class FavoriteCollectionSerializer(serializers.ModelSerializer):
    favorites = FavoriteItemSerializer(many=True, read_only=True)

    class Meta:
        model = FavoriteCollection
        fields = ("id", "title", "favorites")


# --- Create Serializer ---
class FavoriteCollectionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FavoriteCollection
        fields = ("id", "title")
