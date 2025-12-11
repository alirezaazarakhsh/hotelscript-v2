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
        'settings/',
        views.UserSubscriptionSettingsView.as_view(),
        name='user-subscription-settings'
    ),
    path(
        'auto-renewal-users/',
        views.AutoRenewalUsersListView.as_view(),
        name='auto-renewal-users'
    ),
    path(
        'active-subscription-users/',
        views.ActiveSubscriptionUsersListView.as_view(),
        name='active-subscription-users'
    ),
    path(
        'downgrade-level/',
        views.UserLevelDowngradeView.as_view(),
        name='user-level-downgrade'
    ),
]
