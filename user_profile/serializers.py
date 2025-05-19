from rest_framework import serializers
from .models import (
    FavoriteCollection,
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
