from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    
     path(
            'wallet/',
            views.WalletRetrieveAPIView.as_view(),
            name='wallet-detail'
        ),
    
]