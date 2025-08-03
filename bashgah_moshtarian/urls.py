from django.urls import path
from .views import (
    MyRoomDiscountCodeListView,
    MyShoppingCenterDiscountCodeListView,
    MyCustomerClubPointView,
    SendRoomDiscountCodeSMSView,
    SendShoppingCenterDiscountCodeSMSView,
)

app_name = "bashgah"

urlpatterns = [
    path('room-discount-codes/', MyRoomDiscountCodeListView.as_view(), name='room-discount-code-list'),
    path('shopping-discount-codes/', MyShoppingCenterDiscountCodeListView.as_view(), name='shopping-discount-code-list'),
    path('customer-club/points/', MyCustomerClubPointView.as_view(), name='customer-club-points'),
    path('send-room-discount-sms/', SendRoomDiscountCodeSMSView.as_view(), name='send-room-discount-sms'),
    path('send-shopping-discount-sms/', SendShoppingCenterDiscountCodeSMSView.as_view(), name='send-shopping-discount-sms'),
]