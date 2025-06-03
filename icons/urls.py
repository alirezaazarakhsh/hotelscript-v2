from django.urls import path, include
from . import views

app_name = 'icons'

urlpatterns = [
    path(
    'shortcuts/',
    views.IconShortcutListCreateView.as_view(),
    name='icon-shortcut-list-create'
),  
      
]