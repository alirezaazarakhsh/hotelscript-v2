from django.urls import path, include
from . import views

app_name = 'authentication'

urlpatterns = [
    path('profile/',  include([
        path('real/', views.UserProfileRetrieveUpdateView.as_view(), name='user-profile-retrieve-update'),
        path('juridical/', views.JuridicalProfileRetrieveUpdateView.as_view(), name='juridical-profile-retrieve-update'),
        path('juridical/documents/', views.JuridicalProfileDocumentListCreateDestroyView.as_view(), name='juridical-profile-document-list-create-destroy'),
        path('juridical/documents/<int:pk>/', views.JuridicalProfileDocumentListCreateDestroyView.as_view(), name='juridical-profile-document-list-create-destroy'),
    ])),         
    path('auth/', include([
        path('', views.AuthView.as_view(), name='auth'),
        path('logout/', views.APILogoutView.as_view(), name='logout'),
    ])),
    path('token/', include([
        path('', views.TokenObtainPairView.as_view(), name='token_obtain_pair'),
        path('refresh/', views.TokenRefreshView.as_view(), name='token_refresh'),
    ])),
]