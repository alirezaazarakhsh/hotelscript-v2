from django.urls import path
from . import views

app_name = 'user_subscription_settings'

urlpatterns = [
    path(
        'description/',
        views.SubscriptionDescriptionView.as_view(),
        name='subscription-description'
    ),
    path(
        'packages/',
        views.SubscriptionPackageListView.as_view(),
        name='subscription-packages'
    ),
    path(
        'payment-request/',
        views.SubscriptionPaymentRequestCreateView.as_view(),
        name='subscription-payment-request-create'
    ),
    path(
        'renewal-request/',
        views.RenewalRequestCreateView.as_view(),
        name='renewal-request-create'
    ),
    path(
        'subscription-info/',
        views.SubscriptionInfoView.as_view(),
        name='subscription-info'
    ),
    path(
        'daily-purchases/',
        views.UserDailyPurchasesView.as_view(),
        name='user-daily-purchases'
    ),
]
