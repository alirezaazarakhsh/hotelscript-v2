from django.urls import path
from . import views

app_name = 'config'

urlpatterns = [
    path('main/', views.SiteConfigRetrieveView.as_view(), name='site-config'),
    path('pages/', views.PageListView.as_view(), name='pages'),
]