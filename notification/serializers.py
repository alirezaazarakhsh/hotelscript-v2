from rest_framework import serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    users = serializers.SerializerMethodField()
    read_by = serializers.SerializerMethodField()
    created_date_jalali = serializers.DateField(format="%Y/%m/%d")
    created_time = serializers.TimeField(format="%H:%M:%S")
    is_read = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id',
            'title',
            'message',
            'status',
            'users',
            'read_by',
            'created_date_jalali',
            'created_time',
            'send_to_all',
            'is_read',
        ]

    def get_users(self, obj):
        return obj.get_users_with_names()

    def get_read_by(self, obj):
        return obj.get_read_by_with_names()

    def get_is_read(self, obj):
        user = self.context['request'].user
        if not user.is_authenticated:
            return False
        return user in obj.read_by.all()