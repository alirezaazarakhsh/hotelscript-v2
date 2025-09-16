from django.urls import path
from .views import (
    FavoriteCollectionListCreateAPI,
    FavoriteCollectionDetailAPI,
    FavoriteItemDeleteAPI,
    FavoriteItemListCreateAPI,
    FavoriteItemDetailAPI,
    FavoriteItemStatusAPI,
    FavoriteCollectionUpdateTitleAPI,
    
)

app_name = "favorites"

urlpatterns = [
    # کالکشن‌ها
    path("collections/", FavoriteCollectionListCreateAPI.as_view(), name="favorite-collections"),
    path("collections/<int:pk>/", FavoriteCollectionDetailAPI.as_view(), name="favorite-collection-detail"),
    path("collections/<int:pk>/update/", FavoriteCollectionUpdateTitleAPI.as_view(), name="favorite-collection-update"),

    # آیتم‌های داخل کالکشن
    path("collections/<int:pk>/items/", FavoriteItemListCreateAPI.as_view(), name="favorite-items"),
    path("collections/<int:pk>/items/<int:item_id>/", FavoriteItemDetailAPI.as_view(), name="favorite-item-detail"),
    
    # وضعیت هتل در علاقه‌مندی‌ها
path("favorites/<int:item_id>/status/", FavoriteItemStatusAPI.as_view(), name="favorite-item-status"),
path("favorites/<int:item_id>/delete/", FavoriteItemDeleteAPI.as_view(), name="favorite-item-delete"),
]
