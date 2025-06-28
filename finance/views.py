from django.contrib.contenttypes.models import ContentType
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListCreateAPIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import BankCard, Wallet
from .serializers import BankCardSerializer, WalletSerializer





class BankCardListCreateView(ListCreateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = BankCardSerializer

    def get_queryset(self):
        """
        بازگرداندن لیست کارت‌های بانکی مربوط به نوع پروفایل کاربر (طبیعی یا حقوقی)
        """
        user = self.request.user
        profile_type = self.request.query_params.get('profile_type')

        if profile_type == 'natural':
            profile = user.natural_profile
        elif profile_type == 'juridical':
            profile = user.natural_profile.juridical_profile
        else:
            raise ValidationError({
                'profile_type': 'مقدار نوع پروفایل صحیح نیست!',
            })

        return BankCard.objects.filter(
            profile_object_id=profile.pk,
            profile_content_type=ContentType.objects.get_for_model(profile.__class__)
        )

    def perform_create(self, serializer):
        """
        ثبت کارت بانکی جدید برای پروفایل طبیعی یا حقوقی کاربر
        """
        profile_type = self.request.data.get('profile_type')
        if profile_type == 'natural':
            profile = self.request.user.natural_profile
        elif profile_type == 'juridical':
            profile = self.request.user.natural_profile.juridical_profile
        else:
            raise ValidationError({
                'profile_type': 'مقدار نوع پروفایل صحیح نیست!',
            })

        BankCard.objects.create(
            card_number=self.request.data.get('card_number'),
            sheba_number=self.request.data.get('sheba_number'),
            profile_object_id=profile.pk,
            profile_content_type=ContentType.objects.get_for_model(profile.__class__),
        )

    @swagger_auto_schema(
        operation_summary="لیست کارت‌های بانکی",
        operation_description="""
        این API به کاربر احراز هویت شده اجازه می‌دهد تا لیست کارت‌های بانکی متصل به نوع پروفایل انتخاب‌شده خود را مشاهده کند.

        ⚠️ پارامتر `profile_type` اجباری است و مقادیر مجاز آن عبارتند از:
        - `natural` برای پروفایل‌های شخص حقیقی
        - `juridical` برای پروفایل‌های حقوقی
        """,
        manual_parameters=[
            openapi.Parameter(
                'profile_type',
                openapi.IN_QUERY,
                description="نوع پروفایل (natural یا juridical)",
                type=openapi.TYPE_STRING,
                required=True,
                enum=["natural", "juridical"]
            ),
        ],
        responses={200: BankCardSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="ثبت کارت بانکی جدید",
        operation_description="""
        این API به کاربر اجازه می‌دهد تا یک کارت بانکی جدید برای پروفایل خود ثبت کند.

        ⚠️ فیلدهای مورد نیاز:
        - `card_number`: شماره کارت (مثال: `6037991234567890`)
        - `sheba_number`: شماره شبا (مثال: `IR820540102680020817909002`)
        - `profile_type`: نوع پروفایل (`natural` یا `juridical`)
        """,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['card_number', 'sheba_number', 'profile_type'],
            properties={
                'card_number': openapi.Schema(type=openapi.TYPE_STRING, description='شماره کارت'),
                'sheba_number': openapi.Schema(type=openapi.TYPE_STRING, description='شماره شبا'),
                'profile_type': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='نوع پروفایل (natural یا juridical)',
                    enum=['natural', 'juridical']
                ),
            },
            example={
                "card_number": "6037991234567890",
                "sheba_number": "IR820540102680020817909002",
                "profile_type": "natural"
            }
        ),
        responses={201: BankCardSerializer()}
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)






class WalletRetrieveAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="دریافت موجودی کیف پول",
        operation_description="""
        این API به کاربر احراز هویت شده اجازه می‌دهد تا موجودی کیف پول خود را مشاهده کند.
        
        این موجودی فقط برای کاربر جاری بازگردانده می‌شود.
        """,
        responses={200: WalletSerializer()}
    )
    def get(self, request):
        try:
            wallet = Wallet.objects.get(user=request.user)
        except Wallet.DoesNotExist:
            return Response({"detail": "کیف پول یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

        serializer = WalletSerializer(wallet)
        return Response(serializer.data, status=status.HTTP_200_OK)
