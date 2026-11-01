from django.urls import path
from . import views
from .views import (
    AmazingHotelsListView,
    CancellationReasonListAPIView,
    CommentPointsAndSuggestionsView,
    GetPriceRangeAPI,
    HomeHotelByHotelSlugView,
    HotelChatBotListView,
    HotelCommentPointSummaryView,
    HotelCommentsBySlugView,
    CreateCommentView,
    BestSellersListView,
    HotelImageAPIView,
    HotelSEOView,
    PassengerListForReservationView,
    ReservationCreateAPIView,
    ReservationDescriptionAPIView,
    ReservationDetailAPIView,
    ReservationInvoiceAPIView,
    ReservationInvoiceDetailAPIView,
    ReservationInvoiceSettingsAPIView,
    SuggesteHotelListView,
    ReservationRoomDetailAPIView,
    UserCancellationCreateAPIView,
    WalletWithdrawAPIView
)

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

    # ==== Hotel Listings (آدرس‌های منطبق با فرانت‌اند) ====
    path('suggested-hotels/', SuggesteHotelListView.as_view(), name='suggested-hotels'),
    path('amazing-hotels/', AmazingHotelsListView.as_view(), name='amazing-hotels'),
    path('best-sellers/', BestSellersListView.as_view(), name='best-sellers'),
    path('by-hotel-slug/<str:hotel_slug>/', HomeHotelByHotelSlugView.as_view(), name='by-hotel-slug'),

    # ==== Hotel Listings (آدرس‌های قدیمی برای پشتیبانی کامل) ====
    path('hotels/suggested-hotels/', SuggesteHotelListView.as_view(), name='suggested-hotels-legacy'),
    path('hotels/amazing-hotels/', AmazingHotelsListView.as_view(), name='amazing-hotels-legacy'),
    path('hotels/best-sellers/', BestSellersListView.as_view(), name='best-sellers-legacy'),
    path('hotels/by-hotel-slug/<str:hotel_slug>/', HomeHotelByHotelSlugView.as_view(), name='hotels-by-hotel-slug-legacy'),

    path('hotels/search/hotel-city/', views.HotelSearchAPI.as_view(), name='hotel-search'),
    path('best-hotels/', views.BestHotelsListCreateView.as_view(), name='best-hotels-list-create'),
    path('best-hotels/best-filter/', views.BestHotelspageAPI.as_view(), name='best-hotels'),
    path('best-hotels/price-range/', GetPriceRangeAPI.as_view(), name='price-range'),  

    # ==== Facilities and Services ====
    path('room-services/', views.RoomServiceListView.as_view(), name='room-service-list'),
    path('hotel-facilities/', views.AllFacilitiesView.as_view(), name='hotel-facilities-short'),
    path('room-facilities/', views.AllRoomFacilitiesView.as_view(), name='room-facilities-short'),
    path('hotels/hotel-facilities/', views.AllFacilitiesView.as_view(), name='all-facilities'),
    path('hotels/room-facilities/', views.AllRoomFacilitiesView.as_view(), name='all-room-facilities'),

    # ==== Cities ====
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
    path('reservation/create/', ReservationCreateAPIView.as_view(), name='reservation-create'),    
    path('reservation/reservation-detail/<str:tracking_code>/', ReservationDetailAPIView.as_view(), name='reservation-detail'),
    path('reservation/hotel-slug/<str:tracking_code>/', HotelImageAPIView.as_view(), name='hotel-image'),
    path("reservation/invoice/<str:tracking_code>/", ReservationInvoiceAPIView.as_view(), name="reservation-invoice"),
    path('reservation/description/<str:tracking_code>/', ReservationDescriptionAPIView.as_view(), name='reservation-description'),
    path('reservation/form/<str:tracking_code>/', ReservationRoomDetailAPIView.as_view(), name='reservation-room-detail'),
    path('reservation/passengers/', PassengerListForReservationView.as_view(), name='reservation-passenger-list'),
    path('reservation/wallet/withdraw/<str:tracking_code>/', WalletWithdrawAPIView.as_view(), name='wallet-withdraw'),
    
    # ==== list reserve user ===
    path('reservation/user-reservations/', views.UserReservationListAPIView.as_view(), name='user-reservations'),
    path('cancellation-reasons/', CancellationReasonListAPIView.as_view(), name='cancellation-reasons-list'),
    
    # ==== User Cancellations ====
    path('reservation/cancellations/create/', UserCancellationCreateAPIView.as_view(), name='user-cancellation-create'),
    
    # ==== Invoice Settings ====
    path('reservation/factor/signator/', ReservationInvoiceSettingsAPIView.as_view(), name='reservation-invoice-settings'),
    
    # ==== Invoice Detail ====
    path('reservation/invoices/<str:tracking_code>/', ReservationInvoiceDetailAPIView.as_view(), name='reservation-invoice-detail'),

    # ==== hotel seo ===
    path('hotels/<slug:hotel_slug>/seo/', HotelSEOView.as_view(), name='hotel-seo'),

    # ==== discount code reservation ===
    path('reservation/discount-code/<str:tracking_code>/', views.ApplyDiscountCodeAPIView.as_view(), name='apply-discount'),
    
    # === Chat-bot API ===
    path('hotels/chatbot/', HotelChatBotListView.as_view(), name='hotel-chatbot-list'),
]