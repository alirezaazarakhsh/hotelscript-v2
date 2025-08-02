from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from .models import RoomDiscountCode, ShoppingCenterDiscountCode  # این خط مهم بود
from .serializers import RoomDiscountCodeSerializer, ShoppingCenterDiscountCodeSerializer


# ✅ ای‌پی‌آی دریافت کد تخفیف برای اتاق‌ها برای کاربر
class MyRoomDiscountCodeListView(ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = RoomDiscountCodeSerializer
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        return RoomDiscountCode.objects.filter(
            is_public=False,
            user=user
        ) | RoomDiscountCode.objects.filter(
            is_public=True
        ) | RoomDiscountCode.objects.filter(
            activated_users=user
        )

    @swagger_auto_schema(
        operation_summary="دریافت کدهای تخفیف اتاق برای کاربر",
        operation_description="""
این API کدهای تخفیف مرتبط با کاربر را بازمی‌گرداند:
- کدهای عمومی (is_public=True)
- کدهایی که فقط برای همین کاربر تعریف شده‌اند
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
        return ShoppingCenterDiscountCode.objects.filter(
            is_public=False,
            user=user
        ) | ShoppingCenterDiscountCode.objects.filter(
            is_public=True
        ) | ShoppingCenterDiscountCode.objects.filter(
            activated_users=user
        )

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
