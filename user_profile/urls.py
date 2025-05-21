from django.urls import path
from . import views

app_name = 'profile'

urlpatterns = [
    path(
        'favorite-collections/',
        views.FavoriteCollectionListCreateView.as_view(),
        name='favorite-collection-list-create'
    ),
    path(
        'favorite-collections/<int:pk>/',
        views.FavoriteCollectionRetrieveDestroyView.as_view(),
        name='favorite-collection-retrieve-destroy'
    ),
    path(
        'favorites/',
        views.FavoriteCreateView.as_view(),
        name='favorite-create'
    ),
    path(
        'favorites/<int:pk>/',
        views.FavoriteDestroyView.as_view(),
        name='favorite-destroy'
    ),
    path(
        'customer-club/prizes/',
        views.CustomerClubPrizeListView.as_view(),
        name='customer-club-prize-list'
    ),
]