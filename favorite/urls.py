from django.urls import path
from .views import FavoriteCollectionListView, FavoriteCollectionDetailView, FavoriteCollectionDeleteView

app_name = 'favorites'

urlpatterns = [
    path('collections/', FavoriteCollectionListView.as_view(), name='favorite-collections'),
    path('collections-<str:content_type>/<int:collection_id>/', FavoriteCollectionDetailView.as_view(), name='favorite-collection-detail'),
    path('collections/<int:collection_id>/delete/', FavoriteCollectionDeleteView.as_view(), name='favorite-collection-delete'),
]