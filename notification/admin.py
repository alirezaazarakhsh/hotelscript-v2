# notification/admin.py
from django.contrib import admin
from .models import Notification

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'created_date_jalali', 'created_time', 'send_to_all')
    filter_horizontal = ('users',)
