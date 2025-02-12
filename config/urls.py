from django.urls import path
from . import views

app_name = 'config'

urlpatterns = [
    path('main/', views.SiteConfigRetrieveView.as_view(), name='site-config'),
    path('pages/', views.PageListView.as_view(), name='pages'),
    path('header-menus/', views.HeaderMenuListView.as_view(), name='header-menus'),
    path('quick-access/', views.QuickAccessListView.as_view(), name='quick-access'),
    path('sections/', views.SectionListView.as_view(), name='sections'),
    path('slides/', views.SlideListView.as_view(), name='slides'),
    path('statistics/', views.StatisticListView.as_view(), name='statistics'),
    path('choose-reasons/', views.ChooseReasonListView.as_view(), name='choose-reasons'),
]