from django.urls import path
from .views import (
    MyRoomDiscountCodeListView,
    MyShoppingCenterDiscountCodeListView,
)

app_name = "bashgah"

urlpatterns = [
    path('room-discount-codes/', MyRoomDiscountCodeListView.as_view(), name='room-discount-code-list'),
    path('shopping-discount-codes/', MyShoppingCenterDiscountCodeListView.as_view(), name='shopping-discount-code-list'),
]
