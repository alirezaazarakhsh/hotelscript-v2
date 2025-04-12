from django.urls import path, include
from . import views

app_name = 'blog'

urlpatterns = [
    path('stories/', views.StoryCategoryListView.as_view(), name='story-category-list'),
    path('stories/<int:pk>/', views.StoryCategoryRetrieveView.as_view(), name='story-category-retrieve'),
]