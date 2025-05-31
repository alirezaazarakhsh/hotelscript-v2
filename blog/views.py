from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.db.models import Q
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.generics import ListAPIView, RetrieveAPIView, ListCreateAPIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import StoryCategory, ArticleCategory, ArticleSubCategory, Article, Comment
from .serializers import (
    StoryCategorySerializer,
    ArticleCategoryListSerializer,
    ArticleCategoryRetrieveSerializer,
    ArticleListSerializer,
    ArticleRetrieveSerializer,
    CommentSerializer,
)


class StoryCategoryListView(ListAPIView):
    queryset = StoryCategory.has_story.prefetch_related('stories').all()
    permission_classes = (AllowAny,)
    serializer_class = StoryCategorySerializer

    @swagger_auto_schema(
        operation_summary="دریافت لیست دسته‌بندی‌های داستان‌ها",
        operation_description="این API تمامی دسته‌بندی‌های داستان‌هایی که داستان دارند را همراه با لیست داستان‌هایشان برمی‌گرداند.",
        tags=['story-blog']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class StoryCategoryRetrieveView(RetrieveAPIView):
    queryset = StoryCategory.has_story.prefetch_related('stories').all()
    permission_classes = (AllowAny,)
    serializer_class = StoryCategorySerializer
    lookup_field = 'pk'

    @swagger_auto_schema(
        operation_summary="دریافت جزئیات یک دسته‌بندی داستان",
        operation_description="این API جزئیات یک دسته‌بندی داستان مشخص به همراه داستان‌های مرتبط را برمی‌گرداند.",
        tags=['story-blog']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ArticleCategoryListView(ListAPIView):
    queryset = ArticleCategory.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = ArticleCategoryListSerializer

    @swagger_auto_schema(
        operation_summary="دریافت لیست دسته‌بندی‌های مقالات",
        operation_description="این API تمامی دسته‌بندی‌های مقالات را برمی‌گرداند.",
        tags=['article']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ArticleCategoryRetrieveView(RetrieveAPIView):
    queryset = ArticleCategory.objects.prefetch_related('subcategories').all()
    permission_classes = (AllowAny,)
    serializer_class = ArticleCategoryRetrieveSerializer
    lookup_field = 'pk'

    @swagger_auto_schema(
        operation_summary="دریافت جزئیات یک دسته‌بندی مقاله",
        operation_description="این API جزئیات یک دسته‌بندی مقاله به همراه زیرشاخه‌های آن را برمی‌گرداند.",
        tags=['article']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ArticleListView(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = ArticleListSerializer

    @swagger_auto_schema(manual_parameters=[
        openapi.Parameter('q', openapi.IN_QUERY, description="عبارت جستجو", type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('category', openapi.IN_QUERY, description="فیلتر بر اساس دسته‌بندی مقاله", type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('subcategory', openapi.IN_QUERY, description="فیلتر بر اساس زیرشاخه مقاله", type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('sort', openapi.IN_QUERY, description="مرتب‌سازی بر اساس", type=openapi.TYPE_STRING, enum=['view', 'updated'], required=False),
        openapi.Parameter('popular', openapi.IN_QUERY, description="فیلتر مقالات محبوب", type=openapi.TYPE_BOOLEAN, required=False),
        openapi.Parameter('engaging', openapi.IN_QUERY, description="فیلتر مقالات جذاب", type=openapi.TYPE_BOOLEAN, required=False),
        openapi.Parameter('publishing', openapi.IN_QUERY, description="فیلتر مقالات در حال انتشار", type=openapi.TYPE_BOOLEAN, required=False),
    ])
    @swagger_auto_schema(
        operation_summary="دریافت لیست مقالات",
        operation_description="این API لیستی از مقالات را با امکان فیلتر، جستجو، مرتب‌سازی و انتخاب بر اساس دسته‌بندی و زیرشاخه برمی‌گرداند.",
        tags=['article']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        publishing_param = self.request.query_params.get('publishing')
        if publishing_param and publishing_param.lower() == 'true':
            queryset = Article.publishings.order_by('published_date')
        else:
            queryset = Article.published.order_by('-published_date', '-created')

        search_query = self.request.query_params.get('q')
        if search_query:
            search_query_obj = SearchQuery(search_query)
            search_vector = (
                SearchVector('title', weight='A') +
                SearchVector('slug', weight='A') +
                SearchVector('body', weight='B')
            )
            tags_vector = SearchVector('tags__title', weight='B')

            queryset = queryset.annotate(
                search=search_vector + tags_vector,
                rank=SearchRank(search_vector + tags_vector, search_query_obj)
            ).filter(rank__gte=0.3).order_by('-rank')

        category_slug = self.request.query_params.get('category')
        subcategory_slug = self.request.query_params.get('subcategory')

        if category_slug:
            category = get_object_or_404(
                ArticleCategory.objects.prefetch_related('subcategories'),
                slug=category_slug
            )
            content_type_category = ContentType.objects.get_for_model(ArticleCategory)
            content_type_subcategory = ContentType.objects.get_for_model(ArticleSubCategory)

            queryset = queryset.filter(
                Q(category_content_type=content_type_category, category_object_id=category.id) |
                Q(category_content_type=content_type_subcategory, category_object_id__in=category.subcategories.values_list('id', flat=True))
            )
        elif subcategory_slug:
            subcategory = get_object_or_404(ArticleSubCategory, slug=subcategory_slug)
            content_type_subcategory = ContentType.objects.get_for_model(ArticleSubCategory)

            queryset = queryset.filter(
                category_content_type=content_type_subcategory,
                category_object_id=subcategory.id
            )

        popular_param = self.request.query_params.get('popular')
        if popular_param and popular_param.lower() == 'true':
            queryset = queryset.filter(is_popular=True)

        engaging_param = self.request.query_params.get('engaging')
        if engaging_param and engaging_param.lower() == 'true':
            queryset = queryset.filter(is_engaging=True)

        sort_by = self.request.query_params.get('sort')
        if sort_by == 'view':
            queryset = queryset.order_by('-view_count', '-published_date', '-created')
        elif sort_by == 'updated':
            queryset = queryset.order_by('-updated', '-published_date', '-created')

        return queryset


class ArticleRetrieveView(RetrieveAPIView):
    queryset = Article.published.prefetch_related('tags').select_related('author').all()
    permission_classes = (AllowAny,)
    serializer_class = ArticleRetrieveSerializer
    lookup_field = 'slug'
    lookup_url_kwarg = 'slug'

    @swagger_auto_schema(
        operation_summary="دریافت جزئیات یک مقاله",
        operation_description="این API جزئیات کامل یک مقاله منتشر شده بر اساس slug را برمی‌گرداند.",
        tags=['article']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class CommentListCreateView(ListCreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = CommentSerializer

    @swagger_auto_schema(
        operation_summary="دریافت و ثبت کامنت‌ها",
        operation_description="این API کامنت‌های تایید شده مربوط به یک مقاله را برمی‌گرداند و امکان ثبت کامنت جدید را نیز فراهم می‌کند.",
        tags=['comment-blog']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        slug = self.kwargs.get('slug')
        return Comment.approved.select_related('article').prefetch_related('replies').filter(article__slug=slug, reply_to__isnull=True)

    def post(self, request, *args, **kwargs):
        slug = self.kwargs.get('slug')
        article = get_object_or_404(Article, slug=slug)

        serializer = self.get_serializer(data=request.data, context={'article': article})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
