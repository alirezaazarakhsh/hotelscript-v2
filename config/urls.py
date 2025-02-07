from django.urls import path, include
from . import views

app_name = 'config'

urlpatterns = [
    path('main/', views.SiteConfigRetrieveView.as_view(), name='site-config'),
]