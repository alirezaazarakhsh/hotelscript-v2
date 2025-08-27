from rest_framework import generics, permissions, status
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers
from .models import Notification
from .serializers import NotificationSerializer
from django.db import models

# سریالایزر برای بدنه درخواست PUT و PATCH
class NotificationUpdateStatusSerializer(serializers.Serializer):
    is_read = serializers.BooleanField()

class NotificationListView(generics.ListAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = NotificationSerializer
    pagination_class = None  

    def get_queryset(self):
        user = self.request.user
        return Notification.objects.filter(
            models.Q(users=user) | 
            models.Q(send_to_all=True, created_at__gte=user.date_joined)
        ).distinct().order_by('-created_at')

    @swagger_auto_schema(
        operation_summary="دریافت لیست اعلان‌ها",
        operation_description="""
        این API تمام اعلان‌های مربوط به کاربر فعلی را برمی‌گرداند.
        اعلان‌هایی که به‌صورت جداگانه برای کاربر ارسال شده‌اند یا برای همه کاربران ارسال شده‌اند
        و بعد از ثبت‌نام کاربر ایجاد شده‌اند، نمایش داده می‌شوند.
        """,
        responses={200: NotificationSerializer(many=True)}
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
        operation_summary="حذف یک اعلان",
        operation_description="""
        این API به کاربر اجازه می‌دهد اعلانی که به او تعلق دارد را حذف کند.
        فقط اعلان‌هایی که کاربر در لیست گیرندگان آن باشد قابل حذف هستند.
        """,
        responses={
            204: "اعلان با موفقیت حذف شد",
            404: "اعلان یافت نشد یا متعلق به کاربر نیست",
        }
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)





class NotificationUpdateStatusView(generics.UpdateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = NotificationSerializer
    lookup_url_kwarg = 'notification_id'

    def get_queryset(self):
        user = self.request.user
        return Notification.objects.filter(
            models.Q(users=user) | 
            models.Q(send_to_all=True, created_at__gte=user.date_joined)
        )

    @swagger_auto_schema(
        operation_summary="به‌روزرسانی وضعیت اعلان با PUT",
        operation_description="""
        این API به کاربر اجازه می‌دهد با استفاده از متد PUT وضعیت خوانده شدن یک اعلان را تغییر دهد.
        در بدنه درخواست، فیلد is_read باید مقدار بولین (true یا false) داشته باشد.
        اگر true باشد، اعلان به‌عنوان خوانده شده علامت‌گذاری می‌شود.
        اگر false باشد، وضعیت خوانده شده حذف می‌شود.
        """,
        request_body=NotificationUpdateStatusSerializer,
        responses={
            200: NotificationSerializer(),
            400: "مقدار is_read باید بولین باشد",
            404: "اعلان یافت نشد یا متعلق به کاربر نیست",
        },
        operation_id="update_notification_status_put"
    )
    def put(self, request, *args, **kwargs):
        notification = self.get_object()
        user = self.request.user
        is_read = request.data.get('is_read')
        
        if not isinstance(is_read, bool):
            return Response(
                {"detail": "مقدار is_read باید بولین باشد"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if is_read:
            notification.read_by.add(user)
        else:
            notification.read_by.remove(user)

        serializer = self.get_serializer(notification)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="به‌روزرسانی وضعیت اعلان با PATCH",
        operation_description="""
        این API به کاربر اجازه می‌دهد با استفاده از متد PATCH وضعیت خوانده شدن یک اعلان را تغییر دهد.
        در بدنه درخواست، فیلد is_read باید مقدار بولین (true یا false) داشته باشد.
        اگر true باشد، اعلان به‌عنوان خوانده شده علامت‌گذاری می‌شود.
        اگر false باشد، وضعیت خوانده شده حذف می‌شود.
        """,
        request_body=NotificationUpdateStatusSerializer,
        responses={
            200: NotificationSerializer(),
            400: "مقدار is_read باید بولین باشد",
            404: "اعلان یافت نشد یا متعلق به کاربر نیست",
        },
        operation_id="update_notification_status_patch"
    )
    def patch(self, request, *args, **kwargs):
        notification = self.get_object()
        user = self.request.user
        is_read = request.data.get('is_read')
        
        if not isinstance(is_read, bool):
            return Response(
                {"detail": "مقدار is_read باید بولین باشد"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if is_read:
            notification.read_by.add(user)
        else:
            notification.read_by.remove(user)

        serializer = self.get_serializer(notification)
        return Response(serializer.data)