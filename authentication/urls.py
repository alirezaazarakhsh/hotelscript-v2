from django.urls import path, include
from . import views

app_name = 'authentication'

urlpatterns = [
    path('auth/', include([
        path('', views.AuthView.as_view(), name='auth'),
        path('logout/', views.APILogoutView.as_view(), name='logout'),
    ])),
    path('token/', include([
        path('', views.TokenObtainPairView.as_view(), name='token_obtain_pair'),
        path('refresh/', views.TokenRefreshView.as_view(), name='token_refresh'),
    ])),
]