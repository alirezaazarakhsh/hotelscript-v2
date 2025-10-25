from django.urls import path
from .views import ReservationPaymentCheckAPIView, PaymentCallbackAPIView

urlpatterns = [
    path('reservation-check/<str:tracking_code>/', ReservationPaymentCheckAPIView.as_view(), name='reservation-payment-check'),
    path('payment/callback/', PaymentCallbackAPIView.as_view(), name='payment-callback'),
]
