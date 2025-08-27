from django.urls import path
from .views import (
    HotelFavoriteCollectionListCreateAPI,
    HotelFavoriteCollectionDetailAPI,
    ArticleFavoriteCollectionListCreateAPI,
    ArticleFavoriteCollectionDetailAPI,
)

app_name = "favorites"  

urlpatterns = [
    path("hotels/", HotelFavoriteCollectionListCreateAPI.as_view(), name="hotel-favorite-collections"),
    path("hotels/<int:pk>/", HotelFavoriteCollectionDetailAPI.as_view(), name="hotel-favorite-collection-detail"),
    path("articles/", ArticleFavoriteCollectionListCreateAPI.as_view(), name="article-favorite-collections"),
    path("articles/<int:pk>/", ArticleFavoriteCollectionDetailAPI.as_view(), name="article-favorite-collection-detail"),
]
