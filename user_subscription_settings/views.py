from rest_framework.generics import RetrieveAPIView, ListAPIView, CreateAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from .models import SubscriptionDescription, SubscriptionPackage, SubscriptionPaymentRequest
from .serializers import SubscriptionDescriptionSerializer, SubscriptionPackageSerializer, SubscriptionPaymentRequestSerializer, RenewalRequestSerializer
from authentication.models import NaturalProfile
from config.models import UserLevel
from django.db.models import Q


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


class RenewalRequestCreateView(CreateAPIView):
    queryset = SubscriptionPaymentRequest.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = RenewalRequestSerializer

    def perform_create(self, serializer):
        profile = self.request.user.natural_profile
        if not profile or not profile.subscription_package:
            raise serializers.ValidationError("شما پکیج اشتراکی فعالی ندارید.")
        serializer.save(user=self.request.user, package=profile.subscription_package, is_renewal=True)

    @swagger_auto_schema(
        operation_summary="ارسال درخواست تمدید اشتراک",
        operation_description="این API درخواست تمدید اشتراک فعلی را با فیش واریزی ارسال می‌کند.",
        tags=['sub_panel']
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class SubscriptionInfoView(RetrieveAPIView):
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(
        operation_summary="دریافت اطلاعات اشتراک کاربر",
        operation_description="این API تاریخ انقضا، نوع اشتراک و مبلغ تمدید را برمی‌گرداند.",
        tags=['sub_panel']
    )
    def get(self, request):
        from django.utils import timezone
        profile = request.user.natural_profile
        if not profile:
            return Response({"error": "پروفایل یافت نشد"}, status=404)
        
        # بررسی ارتقای خودکار
        if (profile.progress_target and 
            profile.total_purchase >= profile.progress_target and 
            timezone.now().date() <= profile.progress_deadline):
            try:
                gold_level = UserLevel.objects.get(title='طلایی')
                gold_package = SubscriptionPackage.objects.filter(upgrade_to_level=gold_level).first()
                profile.level = gold_level
                profile.subscription_package = gold_package
                profile.progress_target = None
                profile.progress_deadline = None
                profile.save()
            except UserLevel.DoesNotExist:
                pass  # اگر سطح طلایی وجود ندارد، ارتقا نکن
        
        # تعیین نوع
        if profile.subscription_package:
            subscription_type = "auto" if profile.auto_renewal_enabled else "manual"
            expiration_date = profile.expiration_date
            renewal_cost = profile.subscription_package.monthly_cost
            purchased_amount = None
            progress = {
                "current": int(profile.total_purchase),
                "target": int(profile.progress_target) if profile.progress_target else None,
                "deadline": profile.progress_deadline
            } if profile.progress_target else None
        else:
            subscription_type = "ارتقا"
            expiration_date = None  # بدون تاریخ
            renewal_cost = None
            purchased_amount = int(profile.total_purchase)
            # پیشرفت برای ارتقا
            if profile.total_purchase >= 500000000:
                progress = None  # طلایی، پیشرفت تمام
            elif profile.total_purchase >= 300000000:
                progress = {
                    "current": int(profile.total_purchase),
                    "target": 500000000,
                    "next_level": "طلایی"
                }
            else:
                progress = {
                    "current": int(profile.total_purchase),
                    "target": 300000000,
                    "next_level": "نقره‌ای"
                }
        
        data = {
            "expiration_date": expiration_date,
            "subscription_type": subscription_type,
            "renewal_cost": renewal_cost,
            "purchased_amount": purchased_amount,
            "progress": progress
        }
        return Response(data)


from django.db.models import Sum
from django.db.models.functions import TruncDate
from reservation.models import Reservationhotel

class UserDailyPurchasesView(ListAPIView):
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Reservationhotel.objects.filter(
            buyer=self.request.user,
            payment_status='paid'
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            total=Sum('final_price')
        ).order_by('date')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        data = list(queryset)
        return Response(data)

    @swagger_auto_schema(
        operation_summary="دریافت خریدهای روزانه کاربر",
        operation_description="این API مجموع خریدهای روزانه کاربر را برای چارت برمی‌گرداند.",
        tags=['sub_panel']
    )
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)
