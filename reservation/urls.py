from django.urls import path
from . import views
from .views import CommentPointsAndSuggestionsView, HotelCommentPointSummaryView, HotelCommentsBySlugView, CreateCommentView




app_name = 'reservation'

urlpatterns = [
    # ==== Hotel Info ====
    path('hotels/<slug:slug>/faq/', views.HotelFAQListView.as_view(), name='hotel-faq-list'),
    path('hotels/<slug:slug>/facilities/', views.HotelFacilitiesListView.as_view(), name='hotel-facilities'),
    path('hotels/<slug:slug>/room-facilities/', views.HotelRoomFacilitiesListView.as_view(), name='hotel-room-facility-list'),
    path('hotels/<slug:slug>/all-facilities/', views.HotelFacilitiesView.as_view(), name='hotel-all-facilities'),
    path('hotels/<slug:slug>/nearby-places/', views.HotelNearbyPlaceListView.as_view(), name='nearby-place-list'),
    path('hotels/<slug:slug>/images/', views.HotelImagesView.as_view(), name='hotel-images'),
    path('hotels/<slug:slug>/description/', views.HotelDescriptionView.as_view(), name='hotel-description'),
    path('hotels/<slug:slug>/introduction/', views.HotelIntroductionView.as_view(), name='hotel-introduction'),
    path('hotels/<slug:slug>/further-description/', views.HotelFurtherDescriptionView.as_view(), name='hotel-further-description'),
    path('hotels/<slug:slug>/rules/', views.HotelRulesView.as_view(), name='hotel-rules'),
    path('hotels/<slug:slug>/tags/', views.HotelTagsView.as_view(), name='hotel-tags'),
    path('hotels/<slug:slug>/gallery/', views.HotelGalleryView.as_view(), name='hotel-gallery'),

    # ==== Hotel Listings ====
    path('hotels/search/hotel-city/', views.HotelSearchAPI.as_view(), name='hotel-search'),
    path('best-hotels/', views.BestHotelsListCreateView.as_view(), name='best-hotels-list-create'),
    path('hotels/home/', views.HomeHotelListView.as_view(), name='home-hotel-list'),


    # ==== Facilities and Services ====
    path('room-services/', views.RoomServiceListView.as_view(), name='room-service-list'),

    # ==== Cities ====
    path('cities/', views.CityListView.as_view(), name='city-list'),
    path('cities/homepage/', views.HomePageCityListView.as_view(), name='homepage-city-list'),

    # ==== Hotel Types ====
    path('types/', views.HotelTypeListView.as_view(), name='hotel-type-list'),

    # ==== Passenger ====
    path('passengers/', views.PassengerListCreateView.as_view(), name='passenger-list-create'),
    path('passengers/<int:pk>/', views.PassengerRetrieveUpdateDestroyView.as_view(), name='passenger-detail'),
    
     # ==== Comments ====
    path('hotels/<slug:slug>/comments/', HotelCommentsBySlugView.as_view(), name='hotel-comments-by-slug'),
    path('hotels/<slug:slug>/comments/create/', CreateCommentView.as_view(), name='hotel-comment-create'),
    path('hotels/<slug:slug>/comments/points-summary/', HotelCommentPointSummaryView.as_view(), name='hotel-comment-point-summary'),
    path('hotels/comments/points-and-suggestions/', CommentPointsAndSuggestionsView.as_view(), name='comment-points-and-suggestions'),


    # ==== Room Info ====
    path('hotels/<slug:slug>/rooms/', views.HotelRoomsView.as_view(), name='hotel-rooms'),


]
