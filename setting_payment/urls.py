from django.urls import path
from .views import CreateTransactionView, VerifyTransactionView, callback_view

app_name = 'payment'

urlpatterns = [
    path('create/', CreateTransactionView.as_view(), name='payment_create'),
    path('verify/', VerifyTransactionView.as_view(), name='payment_verify'),
    path('callback/', callback_view, name='payment_callback'),
]