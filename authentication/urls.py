from django.urls import path
from . import views
from .admin import tinymce_upload

app_name = 'authentication'

urlpatterns = [
    # احراز هویت و خروج
    path('auth/', views.AuthView.as_view(), name='auth'),
    path('auth/logout/', views.APILogoutView.as_view(), name='logout'),
    # ورود پنل گرافیکی ادمین
    path('panel/login/', views.AdminPanelLoginView.as_view(), name='panel_login'),

    # توکن JWT
    path('token/', views.TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', views.TokenRefreshView.as_view(), name='token_refresh'),

    # پروفایل‌ها
    path('natural-profiles/', views.NaturalProfileListCreateAPIView.as_view(), name='natural_profile_list_create'),
    path('natural-profiles/me/', views.NaturalProfileDetailAPIView.as_view(), name='natural_profile_me'),

    path('juridical-profiles/', views.JuridicalProfileListCreateAPIView.as_view(), name='juridical_profile_list_create'),
    path('juridical-profiles/me/', views.JuridicalProfileDetailAPIView.as_view(), name='juridical_profile_me'),

    # مدارک پروفایل حقوقی
    path('juridical-profile-documents/', views.JuridicalProfileDocumentListCreateAPIView.as_view(), name='juridical_profile_document_list_create'),
    path('juridical-profile-documents/<int:pk>/', views.JuridicalProfileDocumentRetrieveUpdateDestroyAPIView.as_view(), name='juridical_profile_document_detail'),

    # مدیریت شماره کارت‌های حقیقی و حقوقی
    path('card-numbers/', views.CardNumberManagementView.as_view(), name='card_number_management'),

    # آپلود TinyMCE
    path('tinymce/upload/', tinymce_upload, name='tinymce-upload'),
]
