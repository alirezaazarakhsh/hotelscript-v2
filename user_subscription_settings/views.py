from rest_framework.generics import RetrieveAPIView, ListAPIView, CreateAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from .models import SubscriptionDescription, SubscriptionPackage, SubscriptionPaymentRequest
from .serializers import SubscriptionDescriptionSerializer, SubscriptionPackageSerializer, SubscriptionPaymentRequestSerializer
from authentication.models import NaturalProfile
from django.db.models import Q


class UserSubscriptionSettingsView(RetrieveUpdateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = None  # خواهیم ساخت

    def get_object(self):
        return self.request.user.natural_profile

    @swagger_auto_schema(
        operation_summary="دریافت و ویرایش تنظیمات اشتراک کاربر",
        operation_description="این API تنظیمات تمدید خودکار اشتراک را دریافت و ویرایش می‌کند.",
        tags=['sub_panel']
    )
    def get(self, request, *args, **kwargs):
        profile = self.get_object()
        return Response({'auto_renewal_enabled': profile.auto_renewal_enabled})

    def patch(self, request, *args, **kwargs):
        profile = self.get_object()
        enabled = request.data.get('auto_renewal_enabled', profile.auto_renewal_enabled)
        profile.auto_renewal_enabled = enabled
        profile.save()
        return Response({'auto_renewal_enabled': profile.auto_renewal_enabled})


# لیست کاربران با برداشت خودکار فعال
class AutoRenewalUsersListView(ListAPIView):
    permission_classes = (IsAuthenticated,)  # یا AllowAny اگر عمومی
    serializer_class = None  # ساده Response

    def get_queryset(self):
        return NaturalProfile.objects.filter(auto_renewal_enabled=True)

    def list(self, request, *args, **kwargs):
        users = self.get_queryset()
        data = [{'user_id': p.base_user.id, 'username': p.base_user.phone_number, 'full_name': f"{p.first_name or ''} {p.last_name or ''}".strip()} for p in users]
        return Response(data)


# لیست کاربران با اشتراک فعال
class ActiveSubscriptionUsersListView(ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = None

    def get_queryset(self):
        from django.utils import timezone
        return NaturalProfile.objects.filter(expiration_date__gt=timezone.now())

    def list(self, request, *args, **kwargs):
        users = self.get_queryset()
        data = [{'user_id': p.base_user.id, 'username': p.base_user.phone_number, 'level': str(p.level), 'expiration_date': p.expiration_date} for p in users]
        return Response(data)


# API برای downgrade سطح توسط کاربر
class UserLevelDowngradeView(RetrieveUpdateAPIView):
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user.natural_profile

    def patch(self, request, *args, **kwargs):
        profile = self.get_object()
        new_level_title = request.data.get('level')  # مثل 'نقره‌ای'
        if new_level_title:
            from config.models import UserLevel
            try:
                new_level = UserLevel.objects.get(title=new_level_title)
                profile.level = new_level
                profile.save()
                return Response({'level': str(profile.level)})
            except UserLevel.DoesNotExist:
                return Response({'error': 'سطح نامعتبر'}, status=400)
        return Response({'error': 'سطح مشخص نشده'}, status=400)


class SubscriptionDescriptionView(RetrieveAPIView):
    queryset = SubscriptionDescription.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = SubscriptionDescriptionSerializer

    def get_object(self):
        # همیشه اولین رکورد رو برگردون، اگر نباشه، یکی بسازه
        obj, created = SubscriptionDescription.objects.get_or_create(id=1, defaults={'description': ''})
        return obj

    @swagger_auto_schema(
        operation_summary="دریافت توضیحات تکمیلی اشتراک",
        operation_description="این API توضیحات تکمیلی اشتراک را دریافت می‌کند.",
        tags=['sub_panel']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class SubscriptionPackageListView(ListAPIView):
    queryset = SubscriptionPackage.objects.prefetch_related('options').all()
    permission_classes = (AllowAny,)
    serializer_class = SubscriptionPackageSerializer
    pagination_class = None  # غیرفعال کردن pagination

    @swagger_auto_schema(
        operation_summary="دریافت لیست پکیج‌های اشتراک",
        operation_description="این API لیست تمامی پکیج‌های اشتراک را همراه با آپشن‌ها برمی‌گرداند.",
        tags=['sub_panel']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class SubscriptionPaymentRequestCreateView(CreateAPIView):
    queryset = SubscriptionPaymentRequest.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = SubscriptionPaymentRequestSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @swagger_auto_schema(
        operation_summary="ارسال درخواست پرداخت اشتراک",
        operation_description="این API درخواست پرداخت اشتراک را با فیش واریزی ارسال می‌کند.",
        tags=['sub_panel']
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
