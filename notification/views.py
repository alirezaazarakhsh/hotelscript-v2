from rest_framework import generics, permissions, status
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from .models import Notification
from .serializers import NotificationSerializer
from django.db import models


class NotificationListView(generics.ListAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = NotificationSerializer
    pagination_class = None  


    def get_queryset(self):
        user = self.request.user
        return Notification.objects.filter(
            models.Q(users=user) | models.Q(send_to_all=True)
        ).distinct().order_by('-created_at')

    @swagger_auto_schema(
        operation_summary="لیست اعلان‌ها",
        operation_description="""
        این API لیست اعلان‌های مربوط به کاربر را نمایش می‌دهد.
        شامل اعلان‌هایی که به صورت فردی برای کاربر ارسال شده‌اند یا برای همه ارسال شده‌اند.
        """,
        responses={200: NotificationSerializer(many=True)},
        tags=["notification-user"]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class NotificationDeleteView(generics.DestroyAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = NotificationSerializer
    lookup_url_kwarg = 'notification_id'

    def get_queryset(self):
        user = self.request.user
        return Notification.objects.filter(users=user)

    @swagger_auto_schema(
        operation_summary="حذف اعلان",
        operation_description="""
        این API به کاربر اجازه می‌دهد تا اعلان‌های خود را حذف کند.
        فقط اعلان‌هایی که به کاربر تعلق دارند قابل حذف هستند.
        """,
        responses={
            204: "حذف نوتیفیکیشن موفقیت‌آمیز بود",
            404: "اعلان یافت نشد یا متعلق به کاربر نیست",
        },
        tags=["notification-user"]
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)
