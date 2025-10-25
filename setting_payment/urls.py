from django.urls import path
from .views import (
    ReservationPaymentCheckAPIView,
    PaymentCallbackAPIView,
    IranianGatewayRedirectView,
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
    path(
        'iranian-redirect/<str:authority>/',
        IranianGatewayRedirectView.as_view(),
        name='iranian-redirect'
    ),
]
