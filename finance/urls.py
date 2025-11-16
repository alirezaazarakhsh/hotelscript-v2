from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    path(
        'wallet/',
        views.WalletRetrieveAPIView.as_view(),
        name='wallet-detail'
    ),
    path(
        'wallet/packs/',
        views.WalletPackListAPIView.as_view(),
        name='wallet-pack-list'
    ),
    path(
        'wallet/create-payment-link/',
        views.CreatePaymentLinkAPIView.as_view(),
        name='wallet-create-payment-link'
    ),
    # مسیر کال‌بک زرین‌پال:
    path(
        'payment/callback/',
        views.PaymentCallbackAPIView.as_view(),
        name='payment-callback'
    ),
]
