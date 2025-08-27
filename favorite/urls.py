from django.urls import path
from .views import (
    FavoriteCollectionListCreateView,
    FavoriteCollectionDetailView,
    FavoriteListCreateView,
    FavoriteDetailView
)

app_name = "favorite"  

urlpatterns = [
    path('collections/', FavoriteCollectionListCreateView.as_view(), name='collection-list-create'),
    path('collections/<int:pk>/', FavoriteCollectionDetailView.as_view(), name='collection-detail'),
    path('collections/<int:list_id>/favorites/', FavoriteListCreateView.as_view(), name='favorite-list-create'),
    path('favorites/<int:pk>/', FavoriteDetailView.as_view(), name='favorite-detail'),
]
