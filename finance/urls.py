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
    # مسیر کال‌بک برای پرداخت - با همان View لینک پرداخت هندل می‌شود (GET)
    path(
        'wallet/payment-callback/',
        views.CreatePaymentLinkAPIView.as_view(),
        name='wallet-payment-callback'
    ),
    path(
        'admin-card-settings/',
        views.AdminCardSettingsAPIView.as_view(),
        name='admin-card-settings'
    ),
    path(
        'deposit-receipts/',
        views.DepositReceiptCreateAPIView.as_view(),
        name='deposit-receipt-create'
    ),
    path(
        'withdrawal-requests/',
        views.WithdrawalRequestCreateAPIView.as_view(),
        name='withdrawal-request-create'
    ),
    path(
        'wallet/operations/',
        views.FinancialOperationsListAPIView.as_view(),
        name='wallet-operations'
    ),
    path(
        'card-to-card/instruction/',
        views.CardToCardInstructionAPIView.as_view(),
        name='card-to-card-instruction'
    ),
]
