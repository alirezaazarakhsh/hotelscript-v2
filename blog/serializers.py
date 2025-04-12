from rest_framework import serializers
from .models import (
    StoryCategory,
    Story,
)

class NestedStorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Story
        fields = (
            'image',
            'created',
        )

class StoryCategorySerializer(serializers.ModelSerializer):
    stories = NestedStorySerializer(many=True)

    class Meta:
        model = StoryCategory
        exclude = (
            'created',
        )
