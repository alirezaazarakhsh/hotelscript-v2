from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    users = serializers.SerializerMethodField()
    created_date_jalali = serializers.DateField(format="%Y/%m/%d")
    created_time = serializers.TimeField(format="%H:%M:%S")

    class Meta:
        model = Notification
        fields = [
            'id',
            'title',
            'message',
            'status',
            'users',
            'created_date_jalali',
            'created_time',
            'send_to_all',
        ]

    def get_users(self, obj):
        return obj.get_users_with_names()
