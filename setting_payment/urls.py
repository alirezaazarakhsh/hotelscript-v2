from django.urls import path
from .views import (
    ReservationPaymentCheckAPIView,
    PaymentCallbackAPIView,
    PaymentVerifyAPIView,
)

app_name = "payment"

urlpatterns = [
    path(
        'reservation-check/<str:tracking_code>/',
        ReservationPaymentCheckAPIView.as_view(),
        name='reservation-payment-check'
    ),
    path(
        'callback/',
        PaymentCallbackAPIView.as_view(),
        name='payment-callback'
    ),
    path(
        'verify/',
        PaymentVerifyAPIView.as_view(),
        name='payment-verify'
    ),
  
]
