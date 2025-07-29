from rest_framework import serializers
from .models import (
    FavoriteCollection,
    Favorite,
    CustomerClubPrize,
    CustomerReceivedPrize,
)
from blog.serializers import (
    FavoriteArticleSerializer,
)


class FavoriteCollectionListSerializer(serializers.ModelSerializer):
    images = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = FavoriteCollection
        fields = (
            'id',
            'title',
            'images',
        )
        extra_kwargs = {
            'id' : {
                'read_only': True,
            },
        }
    
    def get_images(self, obj):
        return getattr(obj, 'images', [])

class FavoriteCollectionRetrieveSerializer(serializers.ModelSerializer):
    class Meta:
        model = FavoriteCollection
        fields = (
            'id',
            'title',
        )
        extra_kwargs = {
            'id' : {
                'read_only': True,
            },
        }

class FavoriteCreateSerializer(serializers.ModelSerializer):
    item_type = serializers.ChoiceField(
        choices=[
            'hotel',
            'article',
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
        return obj.item_content_type.model

    def get_item_data(self, obj):
        model_name = obj.item_content_type.model
        serializer_class = self.ITEM_SERIALIZER_MAP.get(model_name)
        if serializer_class:
            return serializer_class(obj.item, context=self.context).data
        return None

class CustomerClubPrizeListSerializer(serializers.ModelSerializer):

    class Meta:
        model = CustomerClubPrize
        fields = (
            'id',
            'title',
            'required_points',
            'expired_date',
            'discount_price',
            'rules',
        )


class CustomerClubPrizeRetrieveSerializer(serializers.ModelSerializer):

    class Meta:
        model = CustomerClubPrize
        fields = (
            'title',
            'expired_date',
            'discount_price',
            'discount_code',
        )

class CustomerClubPrizeListSerializer(serializers.ModelSerializer):
    prize = CustomerClubPrizeRetrieveSerializer()

    class Meta:
        model = CustomerReceivedPrize
        fields = (
            'prize',
            'created',
        )
