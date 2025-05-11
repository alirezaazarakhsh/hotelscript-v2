from django.urls import path, include
from . import views

app_name = 'reservation'

urlpatterns = [
    path('<str:slug>/', include([
        path(
            'detail/',
            views.HotelRetrieveView.as_view(),
            name='hotel-detail'
        ),
    ])),
    path(
        'search/',
        views.HotelListView.as_view(),
        name='hotel-list'
    ),
    path(
        'cities/',
        views.CityListView.as_view(),
        name='city-list'
    ),
    path(
        'types/',
        views.HotelTypeListView.as_view(),
        name='hotel-type-list'
    ),
    path(
        'facilities/',
        views.FacilitiesListView.as_view(),
        name='facility-list'
    ),
    path(
        'room-facilities/',
        views.RoomFacilitiesListView.as_view(),
        name='room-facility-list'
    ),
    path(
        'room-services/',
        views.RoomServiceListView.as_view(),
        name='room-service-list'
    ),
]