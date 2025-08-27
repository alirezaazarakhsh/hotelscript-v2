from django.urls import path
from .views import (
    FavoriteCollectionListCreateView,
    FavoriteCollectionDetailView,
    FavoriteListCreateView,
    FavoriteDetailView
)

urlpatterns = [
    # لیست علاقمندی‌ها
    path('collections/', FavoriteCollectionListCreateView.as_view(), name='favorite-collection-list-create'),
    path('collections/<int:pk>/', FavoriteCollectionDetailView.as_view(), name='favorite-collection-detail'),

    # آیتم‌های داخل هر لیست
    path('collections/<int:list_id>/favorites/', FavoriteListCreateView.as_view(), name='favorite-list-create'),
    path('favorites/<int:pk>/', FavoriteDetailView.as_view(), name='favorite-detail'),
]
