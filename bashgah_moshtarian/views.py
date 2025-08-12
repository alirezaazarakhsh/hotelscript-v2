import traceback
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from django.db.models import Q


from authentication import models
from .models import CustomerClubPoint, DiscountActivationRecord, RoomDiscountCode, ShoppingCenterDiscountCode
from .serializers import CustomerClubPointSerializer, DiscountActivationRecordSerializer, RoomDiscountCodeSerializer, ShoppingCenterDiscountCodeSerializer




# ✅ ای‌پی‌آی دریافت کد تخفیف برای اتاق‌ها برای کاربر
class MyRoomDiscountCodeListView(ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = RoomDiscountCodeSerializer
    

    def get_queryset(self):
        user = self.request.user
        return RoomDiscountCode.objects.filter(
            Q(users=user) |          
            Q(activated_users=user)
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
        try:
            return super().get(request, *args, **kwargs)
        except Exception as exc:
            return Response({
                "error": str(exc),
                "exception_type": exc.__class__.__name__,
                "trace": traceback.format_exc(limit=2)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




# ✅ ای‌پی‌آی دریافت تخفیفات مراکز خرید کاربر
class MyShoppingCenterDiscountCodeListView(ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = ShoppingCenterDiscountCodeSerializer
    

    def get_queryset(self):
        user = self.request.user
        # فقط کدهایی که یا به کاربر اختصاص داره یا کاربر فعال‌شون کرده
        return (
            ShoppingCenterDiscountCode.objects.filter(users=user) |
            ShoppingCenterDiscountCode.objects.filter(activated_users=user)
        ).distinct()

    @swagger_auto_schema(
        operation_summary="دریافت کدهای تخفیف مراکز خرید برای کاربر",
        operation_description="""
این API کدهای تخفیف مربوط به مراکز خرید را بازمی‌گرداند که با کاربر مرتبط هستند:
- کدهای اختصاصی مربوط به کاربر
- کدهایی که کاربر آن‌ها را فعال کرده است.
""",
        tags=['discount-crm']
    )
    def get(self, request, *args, **kwargs):
        try:
            return super().get(request, *args, **kwargs)
        except Exception as exc:
            return Response({
                "error": str(exc),
                "exception_type": exc.__class__.__name__,
                "trace": traceback.format_exc(limit=2)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            



#ای پی ای جوایز دریافتی کاربران 
class DiscountActivationRecordListView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = DiscountActivationRecordSerializer

    def get_queryset(self):
        user = self.request.user
        return DiscountActivationRecord.objects.filter(user=user).order_by('-activated_at')

    @swagger_auto_schema(
        operation_summary="دریافت لیست جوایز فعال شده کاربر",
        operation_description="""
این API لیست جوایز فعال شده توسط کاربر را بازمی‌گرداند که شامل:
- کدهای تخفیف اتاق
- کدهای تخفیف مرکز خرید
می‌باشد. نتایج بر اساس تاریخ فعال‌سازی به ترتیب نزولی مرتب شده‌اند.
""",
        tags=['discount-crm'],
        responses={
            200: DiscountActivationRecordSerializer(many=True),
            500: 'خطای سرور داخلی'
        }
    )
    def get(self, request, *args, **kwargs):
        try:
            return super().get(request, *args, **kwargs)
        except Exception as exc:
            return Response({
                "error": str(exc),
                "exception_type": exc.__class__.__name__,
                "trace": traceback.format_exc(limit=2)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)





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



