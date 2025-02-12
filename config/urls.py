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
    path('faqs/', views.FAQListView.as_view(), name='faqs'),
    path('services/', views.ServiceListView.as_view(), name='services'),
    path('contact-info/', views.ContactInfoListView.as_view(), name='contact-info'),
    path('social-media/', views.SocialMediaListView.as_view(), name='social-media'),
    path('banners/', views.BannerListView.as_view(), name='banners'),
    path('enamad/', views.EnamadLicenseRetrieveView.as_view(), name='enamad'),
]