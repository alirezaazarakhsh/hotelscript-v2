from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from django.db.models import Q
from .models import CustomerClubPoint, RoomDiscountCode, ShoppingCenterDiscountCode
from .serializers import CustomerClubPointSerializer, RoomDiscountCodeSerializer, ShoppingCenterDiscountCodeSerializer




# ✅ ای‌پی‌آی دریافت کد تخفیف برای اتاق‌ها برای کاربر
class MyRoomDiscountCodeListView(ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = RoomDiscountCodeSerializer
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        return RoomDiscountCode.objects.filter(
            models.Q(users=user) |          # کدهایی که برای این کاربر تعریف شده‌اند
            models.Q(activated_users=user)  # کدهایی که کاربر فعال کرده است
        ).distinct()

    @swagger_auto_schema(
        operation_summary="دریافت کدهای تخفیف اتاق برای کاربر",
        operation_description="""
این API کدهای تخفیف مرتبط با کاربر را بازمی‌گرداند:
- کدهایی که برای این کاربر تعریف شده‌اند.
- کدهایی که کاربر قبلاً آن‌ها را فعال کرده است.
""",
        tags=['discount-crm']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)




# ✅ ای‌پی‌آی دریافت تخفیفات مراکز خرید کاربر
class MyShoppingCenterDiscountCodeListView(ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = ShoppingCenterDiscountCodeSerializer
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        return (
            ShoppingCenterDiscountCode.objects.filter(is_public=False, user=user)
            | ShoppingCenterDiscountCode.objects.filter(is_public=True)
            | ShoppingCenterDiscountCode.objects.filter(activated_users=user)
        ).distinct()

    @swagger_auto_schema(
        operation_summary="دریافت کدهای تخفیف مراکز خرید برای کاربر",
        operation_description="""
این API کدهای تخفیف مربوط به مراکز خرید را بازمی‌گرداند که با کاربر مرتبط هستند:
- کدهای عمومی (is_public=True)
- کدهای اختصاصی مربوط به کاربر
- کدهایی که کاربر آن‌ها را فعال کرده است.
""",
        tags=['discount-crm']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)




# ✅ ای‌پی‌آی نمایش امتیاز باشگاه مشتریان کاربر
class MyCustomerClubPointView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="دریافت امتیاز باشگاه مشتریان",
        operation_description="""
این API امتیاز فعلی کاربر در باشگاه مشتریان را بازمی‌گرداند.
""",
        tags=["discount-crm"]
    )
    def get(self, request, *args, **kwargs):
        try:
            instance = CustomerClubPoint.objects.get(user=request.user)
            serializer = CustomerClubPointSerializer(instance)
            return Response(serializer.data)
        except CustomerClubPoint.DoesNotExist:
            return Response({'points': 0}, status=status.HTTP_200_OK)
