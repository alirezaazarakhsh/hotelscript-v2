from django.urls import path
from .views import (
    HotelFavoriteCollectionListCreateAPI,
    HotelFavoriteCollectionDetailAPI,
    HotelFavoriteItemRemoveAPI,
    ArticleFavoriteCollectionListCreateAPI,
    ArticleFavoriteCollectionDetailAPI,
    ArticleFavoriteItemRemoveAPI,
)
app_name = "favorites"
urlpatterns = [
    # هتل‌ها
    path("hotels/", HotelFavoriteCollectionListCreateAPI.as_view(), name="hotel-favorite-collections"),
    path("hotels/<int:pk>/", HotelFavoriteCollectionDetailAPI.as_view(), name="hotel-favorite-collection-detail"),
    path("hotels/<int:collection_id>/items/<int:item_id>/remove/", HotelFavoriteItemRemoveAPI.as_view(), name="hotel-favorite-item-remove"),

    # مقالات
    path("articles/", ArticleFavoriteCollectionListCreateAPI.as_view(), name="article-favorite-collections"),
    path("articles/<int:pk>/", ArticleFavoriteCollectionDetailAPI.as_view(), name="article-favorite-collection-detail"),
    path("articles/<int:collection_id>/items/<int:item_id>/remove/", ArticleFavoriteItemRemoveAPI.as_view(), name="article-favorite-item-remove"),
]

 
 
 
 
