from django.urls import path
from . import views

app_name = 'reservation'

urlpatterns = [

    # ==== Hotel Info ====
    path('hotels/<slug:slug>/faq/', views.HotelFAQListView.as_view(), name='hotel-faq-list'),
    path('hotels/<slug:slug>/facilities/', views.HotelFacilitiesListView.as_view(), name='hotel-facilities'),
    path('hotels/<slug:slug>/nearby-places/', views.HotelNearbyPlaceListView.as_view(), name='nearby-place-list'),
    path('hotels/<slug:slug>/comments/', views.HotelCommentListCreateView.as_view(), name='hotel-comments'),
    path('hotels/<slug:slug>/rating-summary/', views.HotelRatingSummaryListView.as_view(), name='rating-summary-list'),
    path('hotels/<slug:slug>/images/', views.HotelImagesView.as_view(), name='hotel-images'),
    path('hotels/<slug:slug>/description/', views.HotelDescriptionView.as_view(), name='hotel-description'),
    path('hotels/<slug:slug>/introduction/', views.HotelIntroductionView.as_view(), name='hotel-introduction'),
    path('hotels/<slug:slug>/further-description/', views.HotelFurtherDescriptionView.as_view(), name='hotel-further-description'),
    path('hotels/<slug:slug>/rules/', views.HotelRulesView.as_view(), name='hotel-rules'),
    path('hotels/<slug:slug>/tags/', views.HotelTagsView.as_view(), name='hotel-tags'),
    path('hotels/<slug:slug>/gallery/', views.HotelGalleryView.as_view(), name='hotel-gallery'),  # ✅ اضافه شده

    # ==== Hotel Listings ====
    path('hotels/search/', views.HotelListView.as_view(), name='hotel-list'),
    path('best-hotels/', views.BestHotelsListCreateView.as_view(), name='best-hotels-list-create'),
    path('special-offer-hotels/', views.SpecialOfferHotelListView.as_view(), name='special-offer-hotel-list'),
    path('flash-sale-hotels/', views.FlashSaleHotelListView.as_view(), name='flash-sale-hotel-list'),
    path('best-seller-hotels/', views.BestSellerHotelListView.as_view(), name='best-seller-hotel-list'),

    # ==== Room Info ====
    path('rooms/search/', views.RoomListView.as_view(), name='room-list'),
    path('room-dates/<int:room_id>/', views.RoomDateListView.as_view(), name='room-date-list'),

    # ==== Facilities and Services ====
    path('room-services/', views.RoomServiceListView.as_view(), name='room-service-list'),
    path('hotels/<slug:slug>/room-facilities/', views.HotelRoomFacilitiesListView.as_view(), name='hotel-room-facility-list'),

    # ==== Cities ====
    path('cities/', views.CityListView.as_view(), name='city-list'),
    path('cities/homepage/', views.HomePageCityListView.as_view(), name='homepage-city-list'),

    # ==== Hotel Types ====
    path('types/', views.HotelTypeListView.as_view(), name='hotel-type-list'),

    # ==== Availability and Scheduling ====
    path('closed-dates/', views.ClosedDateListCreateView.as_view(), name='closed-date-list-create'),
]
