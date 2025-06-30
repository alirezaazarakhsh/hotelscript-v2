from django.contrib import admin
from .models import Notification

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'status',
        'created_date_jalali',
        'created_time',
        'send_to_all',
    )
    filter_horizontal = ('users',)

    def get_users_display(self, obj):
        return ", ".join(obj.get_users_with_names())
    get_users_display.short_description = "کاربران (شماره و نام)"
