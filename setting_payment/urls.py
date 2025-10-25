from django.urls import path
from .views import ReservationPaymentCheckAPIView

app_name = 'payment'

urlpatterns = [
    path('reservation-check/<str:tracking_code>', ReservationPaymentCheckAPIView.as_view(), name='reservation-payment-check'),
]