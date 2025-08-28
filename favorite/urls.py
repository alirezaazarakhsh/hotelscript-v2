from django.urls import path
from .views import (
    FavoriteCollectionListCreateAPI,
    FavoriteCollectionDetailAPI,
    FavoriteItemListCreateAPI,
    FavoriteItemDetailAPI,
)

app_name = "favorites"

urlpatterns = [
    # کالکشن‌ها
    path("collections/", FavoriteCollectionListCreateAPI.as_view(), name="favorite-collections"),
    path("collections/<int:pk>/", FavoriteCollectionDetailAPI.as_view(), name="favorite-collection-detail"),

    # آیتم‌های داخل کالکشن
    path("collections/<int:pk>/items/", FavoriteItemListCreateAPI.as_view(), name="favorite-items"),
    path("collections/<int:pk>/items/<int:item_id>/", FavoriteItemDetailAPI.as_view(), name="favorite-item-detail"),
]
