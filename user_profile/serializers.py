from rest_framework import serializers
from .models import (
    FavoriteCollection,
    Favorite,
)

class FavoriteCollectionSerializer(serializers.ModelSerializer):

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
