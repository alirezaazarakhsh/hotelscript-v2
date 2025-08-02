from django.urls import path
from .views import (
    MyRoomDiscountCodeListView,
    MyShoppingCenterDiscountCodeListView,
    MyCustomerClubPointView,  # 🔹 اضافه شده
)

app_name = "bashgah"

urlpatterns = [
    path('room-discount-codes/', MyRoomDiscountCodeListView.as_view(), name='room-discount-code-list'),
    path('shopping-discount-codes/', MyShoppingCenterDiscountCodeListView.as_view(), name='shopping-discount-code-list'),
    path('customer-club/points/', MyCustomerClubPointView.as_view(), name='customer-club-points'),  # 🔹 مسیر جدید
]
