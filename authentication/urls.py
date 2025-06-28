from django.urls import path
from . import views

app_name = 'authentication'

urlpatterns = [
    # احراز هویت و خروج
    path('auth/', views.AuthView.as_view(), name='auth'),
    path('auth/logout/', views.APILogoutView.as_view(), name='logout'),

    # توکن JWT
    path('token/', views.TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', views.TokenRefreshView.as_view(), name='token_refresh'),

    # پروفایل‌های حقیقی
    path('natural-profiles/', views.NaturalProfileListCreateAPIView.as_view(), name='natural_profile_list_create'),
    path('natural-profiles/<int:pk>/', views.NaturalProfileDetailAPIView.as_view(), name='natural_profile_update_delete'),

    # پروفایل‌های حقوقی
    path('juridical-profiles/', views.JuridicalProfileListCreateAPIView.as_view(), name='juridical_profile_list_create'),
    path('juridical-profiles/<int:pk>/', views.JuridicalProfileDetailAPIView.as_view(), name='juridical_profile_update_delete'),
    path('juridical-profile-documents/', views.JuridicalProfileDocumentAPIView.as_view(), name='juridical_profile_document'),

]