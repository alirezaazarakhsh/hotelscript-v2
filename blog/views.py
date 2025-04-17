from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.db.models import Q
from rest_framework.generics import (
    ListAPIView,
    RetrieveAPIView,
)
from rest_framework.permissions import AllowAny
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import (
    StoryCategory,
    ArticleCategory,
    ArticleSubCategory,
    Article,
)
from .serializers import (
    StoryCategorySerializer,
    ArticleCategoryListSerializer,
    ArticleCategoryRetrieveSerializer,
    ArticleListSerializer,
    ArticleRetrieveSerializer,
)

# Create your views here.
class StoryCategoryListView(ListAPIView):
    queryset = StoryCategory.has_story.prefetch_related('stories').all()
    permission_classes = (AllowAny,)
    serializer_class = StoryCategorySerializer

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

class StoryCategoryRetrieveView(RetrieveAPIView):
    queryset = StoryCategory.has_story.prefetch_related('stories').all()
    permission_classes = (AllowAny,)
    serializer_class = StoryCategorySerializer
    lookup_field = 'pk'

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

class ArticleCategoryListView(ListAPIView):
    queryset = ArticleCategory.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = ArticleCategoryListSerializer

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

class ArticleCategoryRetrieveView(RetrieveAPIView):
    queryset = ArticleCategory.objects.prefetch_related('subcategories').all()
    permission_classes = (AllowAny,)
    serializer_class = ArticleCategoryRetrieveSerializer
    lookup_field = 'pk'

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

class ArticleListView(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = ArticleListSerializer

    def get_queryset(self):
        if is_publishing := self.request.query_params.get('publishing'):
            queryset = Article.publishings.order_by('published_date')
        else:
            queryset = Article.published.order_by('-published_date', '-created')

        if search_query := self.request.query_params.get('q'):
            search_query = SearchQuery(search_query)
            search_vector = (
                SearchVector('title', weight='A') +
                SearchVector('slug', weight='A') +
                SearchVector('body', weight='B')
            )
            tags_vector = SearchVector('tags__title', weight='B')

            queryset = queryset.annotate(
                search=search_vector + tags_vector,
                rank=SearchRank(
                    search_vector + tags_vector,
                    search_query
                )
            ).filter(rank__gte=0.3)\
            .order_by('-rank')

            # queryset = queryset.filter(
            #     Q(title__icontains=search_query) | 
            #     Q(slug__icontains=search_query) | 
            #     Q(body__icontains=search_query)
            # )

        if category_slug := self.request.query_params.get('category'):
            category = get_object_or_404(
                ArticleCategory.objects.prefetch_related('subcategories'),
                slug=category_slug
            )

            queryset = queryset.filter(
                Q(category_content_type__model=category.__class__.__name__.lower(), category_object_id=category.id) |
                Q(category_content_type__model=ArticleSubCategory.__name__.lower(), category_object_id__in=category.subcategories.values('id'))
            )

        elif subcategory_slug := self.request.query_params.get('subcategory'):
            subcategory_content_type = ContentType.objects.get_for_model(ArticleSubCategory)
            category = get_object_or_404(
                ArticleSubCategory,
                slug=subcategory_slug
            )
            queryset = queryset.filter(
                category_content_type=subcategory_content_type,
                category_object_id=category.id
            )

        if is_popular := self.request.query_params.get('popular'):
            queryset = queryset.filter(is_popular=True)
        elif is_engaging := self.request.query_params.get('engaging'):
            queryset = queryset.filter(is_engaging=True)

        if sort_by := self.request.query_params.get('sort'):
            if sort_by == 'view':
                queryset = queryset.order_by('-view_count', '-published_date', '-created')
            elif sort_by == 'updated':
                queryset = queryset.order_by('-updated', '-published_date', '-created')

        return queryset

    @swagger_auto_schema(manual_parameters=[
        openapi.Parameter(
            'q',
            openapi.IN_QUERY,
            description="search term",
            type=openapi.TYPE_STRING,
            required=False,
        ),
        openapi.Parameter(
            'category',
            openapi.IN_QUERY,
            description="Filter by category",
            type=openapi.TYPE_STRING,
            required=False,
        ),
        openapi.Parameter(
            'subcategory',
            openapi.IN_QUERY,
            description="Filter by subcategory",
            type=openapi.TYPE_STRING,
            required=False,
        ),
        openapi.Parameter(
            'sort',
            openapi.IN_QUERY,
            description="Sort by",
            type=openapi.TYPE_STRING,
            enum=['view', 'updated'],
            required=False,
        ),
        openapi.Parameter(
            'popular',
            openapi.IN_QUERY,
            description="Filter popular blogs",
            type=openapi.TYPE_BOOLEAN,
            required=False,
        ),
        openapi.Parameter(
            'engaging',
            openapi.IN_QUERY,
            description="Filter engaging blogs",
            type=openapi.TYPE_BOOLEAN,
            required=False,
        ),
        openapi.Parameter(
            'publishing',
            openapi.IN_QUERY,
            description="Filter publishing blogs",
            type=openapi.TYPE_BOOLEAN,
            required=False,
        ),
    ])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

class ArticleRetrieveView(RetrieveAPIView):
    queryset = Article.published.all()
    permission_classes = (AllowAny,)
    serializer_class = ArticleRetrieveSerializer
    lookup_field = 'slug'
    lookup_url_kwarg = 'slug'

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
