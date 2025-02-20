from django.urls import path
from . import views

app_name = 'contact'

urlpatterns = [
    path('message/', views.ContactMessageCreateView.as_view(), name='contact-message'),
]