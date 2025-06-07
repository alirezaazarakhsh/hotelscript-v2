from django.urls import path, include
from . import views

app_name = 'blog'

urlpatterns = [
    path(
        'stories/',
        views.StoryCategoryListView.as_view(),
        name='story-category-list'
    ),
    path(
        'stories/<int:pk>/',
        views.StoryCategoryRetrieveView.as_view(),
        name='story-category-retrieve'
    ),
    path(
        'categories/',
        views.ArticleCategoryListView.as_view(),
        name='article-category-lsit'
    ),
    path(
        'categories/<int:pk>/',
        views.ArticleCategoryRetrieveView.as_view(),
        name='article-category-retrieve'
    ),
    path(
        'articles/',
        views.ArticleListView.as_view(),
        name='article-list'
    ),
    path(
        'articles/<str:slug>/',
        views.ArticleRetrieveView.as_view(),
        name='article-retrieve'
    ),
    path(
        'articles/<str:slug>/comments/',
        views.CommentListCreateView.as_view(),
        name='article-comment-list-create'
    ),

    # این خط رو اضافه کن:
    path(
        'articles/engaging-no-pagination/',
        views.EngagingArticleListView.as_view(),
        name='engaging-article-list-no-pagination'
    ),
]
