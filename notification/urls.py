from django.urls import path
from .views import NotificationListView, NotificationDeleteView, NotificationUpdateStatusView

app_name = 'notification'

urlpatterns = [
    path('notifications/', NotificationListView.as_view(), name='notification-list'),
    path('notifications/<int:notification_id>/', NotificationDeleteView.as_view(), name='notification-delete'),
    path('notifications/<int:notification_id>/update-status/', NotificationUpdateStatusView.as_view(), name='notification-update-status'),
]