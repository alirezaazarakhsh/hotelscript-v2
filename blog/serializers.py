from rest_framework import serializers
from .models import (
    StoryCategory,
    Story,
    ArticleCategory,
    ArticleSubCategory,
    Article,
    ArticleTag,
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

class ArticleCategoryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArticleCategory
        exclude = (
            'description',
        )

class NestedArticleSubCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ArticleSubCategory
        fields = (
            'title',
            'slug',
            'description',
        )

class ArticleCategoryRetrieveSerializer(serializers.ModelSerializer):
    subcategories = NestedArticleSubCategorySerializer(many=True)

    class Meta:
        model = ArticleCategory
        fields = '__all__'

class ArticleListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = (
            'title',
            'slug',
            'author',
            'thumbnail',
            'published_date',
        )

class ArticleTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArticleTag
        fields = (
            'title',
            'slug',
        )

class ArticleRetrieveSerializer(serializers.ModelSerializer):
    tags = ArticleTagSerializer(many=True)
    class Meta:
        model = Article
        fields = (
            'title',
            'slug',
            'body',
            'author',
            'tags',
            'thumbnail',
            'view_count',
            'published_date',
        )
