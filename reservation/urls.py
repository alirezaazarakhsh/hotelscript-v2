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
        path(
            'faq/',
            views.HotelFAQListView.as_view(),
            name='hotel-faq-list'
        ),
        path(
            'facilities/',
            views.HotelFacilitiesListView.as_view(),
            name='hotel-facility-list'
        ),
        path(
            'room-facilities/',
            views.HotelRoomFacilitiesListView.as_view(),
            name='hotel-room-facility-list'
        ),
        path(
            'nearby-places/',
            views.HotelNearbyPlaceListView.as_view(),
            name='nearby-place-list'
        ),
        path(
            'comments/',
            views.HotelCommentListCreateView.as_view(),
            name='comment-list'
        ),
        path(
            'rating-summary/',
            views.HotelRatingSummaryListView.as_view(),
            name='rating-summary-list'
        ),
        path(
            'search/',
            views.RoomListView.as_view(),
            name='room-list'
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
    'cities/homepage/',
    views.HomePageCityListView.as_view(),
    name='homepage-city-list'
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
    path(
        'room-dates/<int:room_id>/',
        views.RoomDateListView.as_view(),
        name='room-date-list'
    ),
    path(
        'best-hotels/',
        views.BestHotelsListCreateView.as_view(),
        name='best-hotels-list-create'
    ),
    path(
        'closed-dates/',
        views.ClosedDateListCreateView.as_view(),
        name='closed-date-list-create'
    ),
    
    
    path(
        'special-offer-hotels/',
        views.SpecialOfferHotelListView.as_view(),
        name='special-offer-hotel-list'
    ),
    path(
        'flash-sale-hotels/',
        views.FlashSaleHotelListView.as_view(),
        name='flash-sale-hotel-list'
    ),
    path(
        'best-seller-hotels/',
        views.BestSellerHotelListView.as_view(),
        name='best-seller-hotel-list'
    ),
]
