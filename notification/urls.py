from django.urls import path
from .views import NotificationListView, NotificationDeleteView

urlpatterns = [
    path('notifications/', NotificationListView.as_view(), name='notification-list'),
    path('notifications/<int:notification_id>/', NotificationDeleteView.as_view(), name='notification-delete'),
]
