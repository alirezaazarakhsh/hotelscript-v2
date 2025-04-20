from rest_framework import serializers
from .models import (
    StoryCategory,
    Story,
    ArticleCategory,
    ArticleSubCategory,
    Article,
    ArticleTag,
    Comment,
)
from authentication.models import (
    Admin,
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

class ArticleAuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Admin
        fields = (
            'first_name',
            'last_name',
        )

class ArticleTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArticleTag
        fields = (
            'title',
            'slug',
        )

class ArticleRetrieveSerializer(serializers.ModelSerializer):
    author = ArticleAuthorSerializer()
    tags = ArticleTagSerializer(many=True)
    similar_articles = serializers.SerializerMethodField()

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
            'similar_articles'
        )


    def get_similar_articles(self, obj):
        def serialize_article(article):
            author = ArticleAuthorSerializer(article.author).data

            return {
                'title': article.title,
                'slug': article.slug,
                'author': author,
                'thumbnail': article.thumbnail.url,
                'published_date': article.published_date,
            }
        
        return map(serialize_article, obj.get_similar_articles())

class CommentSerializer(serializers.ModelSerializer):
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = (
            'author_name',
            'author_email',
            'text',
            'created',
            'replies',
            'reply_to',
        )
        extra_kwargs = {
            'author_name': {
                'required': True,
            },
            'author_email': {
                'required': True,
            },
            'text': {
                'required': True,
            },
            'created': {
                'read_only': True,
            },
            'replies': {
                'read_only': True,
            },
            'reply_to': {
                'write_only': True,
            },
        }

    def get_replies(self, obj):
        return self.__class__(obj.get_replies(), many=True, context=self.context).data

    def create(self, validated_data):
        article = self.context['article']
        validated_data['article'] = article
        return super().create(validated_data)

    def validate_reply_to(self, value):
        article = self.context.get('article')
        if value and value.article.slug != article:
            raise serializers.ValidationError({
                'reply_to': "کامنتی که به آن ریپلای میکنید، متعلق به مقاله دیگری است."
            })
        return value
