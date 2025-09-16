from django.urls import path
from .views import (
    FavoriteCollectionListCreateAPI,
    FavoriteCollectionDetailAPI,
    FavoriteCollectionWebsiteDetailAPI,
    FavoriteItemDeleteAPI,
    FavoriteItemListCreateAPI,
    FavoriteItemDetailAPI,
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
    
    # ایتم های حذف 
    path("items/<int:item_id>/", FavoriteItemDeleteAPI.as_view(), name="favorite-item-delete"),

    # کالکشن وب سایت 
    path("website/collections/<int:pk>/", FavoriteCollectionWebsiteDetailAPI.as_view(), name="favorite-collection-website-detail"),
    
]
