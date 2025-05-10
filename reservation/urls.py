from django.urls import path
from . import views

app_name = 'reservation'

urlpatterns = [
    path(
        'search/',
        views.HotelListView.as_view(),
        name='hotel-list'
    ),
]