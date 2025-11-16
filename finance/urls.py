from django.urls import path
from . import views
from rest_framework.permissions import IsAuthenticated

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

    # ساخت لینک پرداخت برای افزایش کیف پول ـ فقط کاربران لاگین‌کرده
    path(
        'wallet/create-payment-link/',
        views.CreatePaymentLinkAPIView.as_view(),
        name='wallet-create-payment-link'
    ),
]
