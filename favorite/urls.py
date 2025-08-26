from django.urls import path
from .views import (
    FavoriteCollectionListCreateView,
    FavoriteCollectionRetrieveDestroyView,
    FavoriteCreateView,
    FavoriteDestroyView,
)

app_name = 'favorite'

urlpatterns = [
    path(
        'collections/',
        FavoriteCollectionListCreateView.as_view(),
        name='favorite-collection-list-create',
    ),
    path(
        'collections/<int:pk>/',
        FavoriteCollectionRetrieveDestroyView.as_view(),
        name='favorite-collection-retrieve-destroy',
    ),
    path(
        'favorites/',
        FavoriteCreateView.as_view(),
        name='favorite-create',
    ),
    path(
        'favorites/<int:pk>/',
        FavoriteDestroyView.as_view(),
        name='favorite-destroy',
    ),
]