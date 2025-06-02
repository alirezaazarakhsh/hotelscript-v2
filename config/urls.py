from django.urls import path
from . import views

app_name = 'config'

urlpatterns = [
    path('main/', views.SiteConfigRetrieveView.as_view(), name='site-config'),
    path('pages/', views.PageListView.as_view(), name='pages'),
    path('header-menus/', views.HeaderMenuListView.as_view(), name='header-menus'),
    path('quick-access/', views.QuickAccessListView.as_view(), name='quick-access'),
    path('slides/', views.SlideListView.as_view(), name='slides'),
    path('statistics/', views.StatisticListView.as_view(), name='statistics'),
    path('choose-reasons/', views.ChooseReasonListView.as_view(), name='choose-reasons'),
    path('faqs/', views.FAQListView.as_view(), name='faqs'),
    path('services/', views.ServiceListView.as_view(), name='services'),
    path('contact-info/', views.ContactInfoListView.as_view(), name='contact-info'),
    path('social-media/', views.SocialMediaListView.as_view(), name='social-media'),
    path('banners/', views.BannerListView.as_view(), name='banners'),
    path('enamad/', views.EnamadLicenseRetrieveView.as_view(), name='enamad'),
    path('licenses/', views.LicenseListView.as_view(), name='licenses'),
    path('advantages/', views.AdvantageListView.as_view(), name='advantages'),
    path('comments/', views.FakeCommentListView.as_view(), name='fake-comments'),
    path('rules/', views.RuleListView.as_view(), name='rules'),
    path('user-levels/', views.UserLevelListView.as_view(), name='user-levels'),
    path('coming-soon/', views.ComingSoonView.as_view(), name='coming-soon'),
    path('location/', views.LocationView.as_view(), name='location'),


]