from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    path(
        'bank-cards/',
        views.BankCardListCreateView.as_view(),
        name='bank-card-list-create'
    ),
    
    
    path(
            'wallet/',
            views.WalletRetrieveAPIView.as_view(),
            name='wallet-detail'
        ),
    
]