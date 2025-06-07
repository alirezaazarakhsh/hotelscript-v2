from rest_framework.permissions import IsAuthenticated, AllowAny
from drf_yasg import openapi
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import (
    TokenObtainPairView as JwtTokenObtainPairView,
    TokenRefreshView as JwtTokenRefreshView,
)
from rest_framework_simplejwt.exceptions import TokenError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from drf_yasg.utils import swagger_auto_schema

from .serializers import (
    AuthSerializer,
    JuridicalProfileSerializer,
    NaturalProfileSerializer,
)
from .models import (
    BaseUser,
    OTP,
    JuridicalProfile,
    NaturalProfile,
)
from .utils import generate_otp_code
from .sms.sms import send_logout_sms, send_otp_sms, send_welcome_sms


# خروج از حساب
class APILogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(
        operation_summary="خروج از حساب کاربری",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'refresh_token': openapi.Schema(type=openapi.TYPE_STRING)
            },
            required=['refresh_token']
        ),
        responses={200: 'OK', 400: 'Bad Request'}
    )
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            if not refresh_token:
                return Response({"detail": "refresh_token is required"}, status=400)

            token = RefreshToken(refresh_token)
            token.blacklist()

            user = request.user
            phone = user.phone_number
            full_name = f"{user.first_name} {user.last_name}".strip()
            send_logout_sms(phone, full_name)

            return Response({"detail": _("با موفقیت خارج شدید.")})
        except Exception as e:
            return Response({"detail": str(e)}, status=400)


# دریافت OTP
class AuthView(APIView):
    permission_classes = (AllowAny,)

    @swagger_auto_schema(
        operation_summary="درخواست کد تایید OTP",
        request_body=AuthSerializer,
        responses={200: 'کد تایید ارسال شد', 429: 'بیش از حد درخواست داده‌اید'}
    )
    def post(self, request):
        if request.user.is_authenticated:
            return Response({"detail": _("شما قبلاً وارد شده‌اید.")}, status=403)

        serializer = AuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data['phone']

        user = BaseUser.objects.get_by_phone_or_create(phone)

        try:
            last_otp = user.otps.latest('created')
            remaining = (last_otp.expired - timezone.now()).total_seconds()
            if remaining > 0:
                return Response(
                    {"detail": _("لطفاً %(minute)d دقیقه صبر کنید.") % {"minute": int(remaining // 60) + 1}},
                    status=429
                )
        except OTP.DoesNotExist:
            pass

        code = generate_otp_code()
        OTP.objects.create(user=user, code=code)

        if not send_otp_sms(phone, code):
            return Response({"detail": _("ارسال کد با خطا مواجه شد.")}, status=500)

        return Response({"detail": _("کد تایید ارسال شد.")})


# ورود با کد OTP
class TokenObtainPairView(JwtTokenObtainPairView):
    @swagger_auto_schema(
        operation_summary="ورود با کد تایید",
        responses={200: 'ورود موفق', 403: 'قبلاً وارد شده‌اید', 401: 'نامعتبر'}
    )
    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return Response({"detail": _("شما قبلاً وارد شده‌اید.")}, status=403)

        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            return Response({"detail": str(e)}, status=401)

        user = serializer.user
        send_welcome_sms(user.phone_number, f"{user.first_name} {user.last_name}".strip())
        return Response(serializer.validated_data)


# تازه‌سازی توکن
class TokenRefreshView(JwtTokenRefreshView):
    @swagger_auto_schema(
        operation_summary="تازه‌سازی توکن",
        responses={200: 'توکن جدید صادر شد'}
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            return Response({"detail": str(e)}, status=401)
        return Response(serializer.validated_data)


# لیست و ایجاد پروفایل حقوقی
class JuridicalProfileListCreateAPIView(APIView):

    @swagger_auto_schema(
        operation_summary="لیست پروفایل‌های حقوقی",
        responses={200: JuridicalProfileSerializer(many=True)}
    )
    def get(self, request):
        queryset = JuridicalProfile.objects.all()
        serializer = JuridicalProfileSerializer(queryset, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="ایجاد پروفایل حقوقی",
        request_body=JuridicalProfileSerializer,
        responses={201: JuridicalProfileSerializer()}
    )
    def post(self, request):
        serializer = JuridicalProfileSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

# ویرایش و حذف پروفایل حقوقی بر اساس شناسه
class JuridicalProfileDetailAPIView(APIView):

    @swagger_auto_schema(
        operation_summary="ویرایش پروفایل حقوقی بر اساس شناسه (ID)",
        request_body=JuridicalProfileSerializer,
        responses={200: JuridicalProfileSerializer()}
    )
    def put(self, request, pk):
        try:
            profile = JuridicalProfile.objects.get(pk=pk)
        except JuridicalProfile.DoesNotExist:
            return Response({"detail": "پروفایل یافت نشد"}, status=404)

        serializer = JuridicalProfileSerializer(profile, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    @swagger_auto_schema(
        operation_summary="حذف پروفایل حقوقی بر اساس شناسه (ID)",
        responses={204: "پروفایل حذف شد"}
    )
    def delete(self, request, pk):
        try:
            profile = JuridicalProfile.objects.get(pk=pk)
            profile.delete()
            return Response(status=204)
        except JuridicalProfile.DoesNotExist:
            return Response({"detail": "پروفایل یافت نشد"}, status=404)


# لیست و ایجاد پروفایل حقیقی
class NaturalProfileListCreateAPIView(APIView):

    @swagger_auto_schema(
        operation_summary="لیست پروفایل‌های حقیقی",
        responses={200: NaturalProfileSerializer(many=True)}
    )
    def get(self, request):
        queryset = NaturalProfile.objects.all()
        serializer = NaturalProfileSerializer(queryset, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="ایجاد پروفایل حقیقی",
        request_body=NaturalProfileSerializer,
        responses={201: NaturalProfileSerializer()}
    )
    def post(self, request):
        serializer = NaturalProfileSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

# ویرایش و حذف پروفایل حقیقی بر اساس شناسه
class NaturalProfileDetailAPIView(APIView):

    @swagger_auto_schema(
        operation_summary="ویرایش پروفایل حقیقی بر اساس شناسه (ID)",
        request_body=NaturalProfileSerializer,
        responses={200: NaturalProfileSerializer()}
    )
    def put(self, request, pk):
        try:
            profile = NaturalProfile.objects.get(pk=pk)
        except NaturalProfile.DoesNotExist:
            return Response({"detail": "پروفایل یافت نشد"}, status=404)

        serializer = NaturalProfileSerializer(profile, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    @swagger_auto_schema(
        operation_summary="حذف پروفایل حقیقی بر اساس شناسه (ID)",
        responses={204: "پروفایل حذف شد"}
    )
    def delete(self, request, pk):
        try:
            profile = NaturalProfile.objects.get(pk=pk)
            profile.delete()
            return Response(status=204)
        except NaturalProfile.DoesNotExist:
            return Response({"detail": "پروفایل یافت نشد"}, status=404)