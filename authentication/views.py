from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import (
    TokenObtainPairView as JwtTokenObtainPairView,
    TokenRefreshView as JwtTokenRefreshView,
)
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .serializers import (
    AuthSerializer,
    UserProfileSerializer,
    JuridicalProfileSerializer,
    JuridicalProfileDocumentSerializer,
)
from .utils import generate_otp_code, send_otp_code
from .models import (
    BaseUser,
    OTP,
    NaturalProfile,
    JuridicalProfile,
    JuridicalProfileDocument,
)
from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import (
    RetrieveUpdateAPIView,
    GenericAPIView,
)
from rest_framework.mixins import (
    CreateModelMixin,
    ListModelMixin,
    DestroyModelMixin,
)
from .permissions import IsJuridicalProfileDocumentOwner


class APILogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(
        operation_summary="خروج از حساب کاربری",
        operation_description="این API برای خروج کاربر از سیستم با باطل کردن توکن refresh استفاده می‌شود.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'refresh_token': openapi.Schema(type=openapi.TYPE_STRING, description='توکن refresh کاربر')
            },
            required=['refresh_token']
        ),
        responses={200: 'OK', 400: 'Bad Request'}
    )
    def post(self, request, *args, **kwargs):
        try:
            if refresh_token := self.request.data.get('refresh_token'):
                outstanding_token = RefreshToken(token=refresh_token)
                outstanding_token.blacklist()
                return Response()
            else:
                return Response(
                    {"detail": "refresh_token is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class AuthView(APIView):
    permission_classes = (AllowAny,)

    @swagger_auto_schema(
        operation_summary="درخواست کد تایید OTP",
        operation_description="""
        این API برای ارسال کد تایید به شماره موبایل کاربر استفاده می‌شود. 
        اگر کدی از قبل ارسال شده و هنوز منقضی نشده باشد، از ارسال مجدد جلوگیری می‌شود.
        """,
        request_body=AuthSerializer,
        responses={200: 'کد ارسال شد', 429: 'باید صبر کنید'}
    )
    def post(self, request):
        if request.user.is_authenticated:
            return Response(
                {"detail": _("you are already logged in")},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = AuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = request.data.get('phone')
        user = BaseUser.objects.get_by_phone_or_create(phone)

        try:
            last_user_otp = user.otps.latest('created')
            wait_time_seconds = -(timezone.now() - last_user_otp.expired).total_seconds()
            if wait_time_seconds >= 0:
                return Response(
                    {
                        "detail": _("wait up to %(minute)d minute to receive the verfication code again") % {'minute': wait_time_seconds // 60 + 1}
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )
        except OTP.DoesNotExist:
            pass

        code = generate_otp_code()
        otp = OTP(user=user)
        otp.set_code(code)
        otp.save()
        send_otp_code(code, phone)

        return Response()


class TokenObtainPairView(JwtTokenObtainPairView):
    @swagger_auto_schema(
        operation_summary="ورود با کد تایید OTP",
        operation_description="گرفتن توکن JWT با استفاده از کد تأیید ارسال شده",
        responses={200: 'دریافت موفق توکن', 403: 'قبلاً وارد شده‌اید'}
    )
    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return Response(
                {"detail": _("you are already logged in")},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])

        return Response(serializer.validated_data)


class TokenRefreshView(JwtTokenRefreshView):
    @swagger_auto_schema(
        operation_summary="تازه‌سازی توکن JWT",
        operation_description="دریافت توکن جدید با استفاده از refresh token",
        responses={200: 'موفق'}
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class UserProfileRetrieveUpdateView(RetrieveUpdateAPIView, CreateModelMixin):
    permission_classes = (IsAuthenticated,)
    serializer_class = UserProfileSerializer

    @swagger_auto_schema(
        operation_summary="دریافت یا به‌روزرسانی پروفایل کاربر حقیقی",
        operation_description="اگر پروفایل وجود نداشته باشد، در هنگام به‌روزرسانی ساخته خواهد شد.",
        responses={200: UserProfileSerializer()}
    )
    def get_object(self):
        return self.request.user.natural_profile

    def get(self, request, *args, **kwargs):
        try:
            return self.retrieve(request, *args, **kwargs)
        except NaturalProfile.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def put(self, request, *args, **kwargs):
        request.data['base_user'] = request.user.pk
        try:
            return self.update(request, *args, **kwargs)
        except NaturalProfile.DoesNotExist:
            return super().create(request, *args, **kwargs)


class JuridicalProfileRetrieveUpdateView(RetrieveUpdateAPIView, CreateModelMixin):
    permission_classes = (IsAuthenticated,)
    serializer_class = JuridicalProfileSerializer

    @swagger_auto_schema(
        operation_summary="مشاهده یا به‌روزرسانی پروفایل حقوقی",
        operation_description="اگر وجود نداشته باشد، هنگام ویرایش ساخته خواهد شد.",
        responses={200: JuridicalProfileSerializer()}
    )
    def get_object(self):
        return self.request.user.natural_profile.juridical_profile

    def get(self, request, *args, **kwargs):
        try:
            return self.retrieve(request, *args, **kwargs)
        except JuridicalProfile.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def put(self, request, *args, **kwargs):
        request.data['natural_profile'] = request.user.natural_profile.pk
        request.data['status'] = 'checking'
        try:
            return self.update(request, *args, **kwargs)
        except NaturalProfile.DoesNotExist:
            return super().create(request, *args, **kwargs)




class JuridicalProfileDocumentListCreateDestroyView(ListModelMixin,
                                                    CreateModelMixin,
                                                    DestroyModelMixin,
                                                    GenericAPIView):
    permission_classes = (
        IsAuthenticated,
        IsJuridicalProfileDocumentOwner,
    )
    serializer_class = JuridicalProfileDocumentSerializer

    @swagger_auto_schema(
        operation_summary="لیست، ایجاد و حذف مدارک حقوقی",
        operation_description="""
        این API برای مدیریت مدارک آپلودی مربوط به پروفایل حقوقی است.
        هر بار ایجاد یا حذف باعث می‌شود وضعیت پروفایل به `checking` تغییر یابد.
        """,
        responses={200: JuridicalProfileDocumentSerializer(many=True)}
    )
    def get_juridical_profile_query_set(self):
        try:
            return JuridicalProfile.objects.select_related(
                'natural_profile',
                'natural_profile__base_user',
            ).filter(natural_profile__base_user=self.request.user)
        except:
            return JuridicalProfile.objects.none()

    def get_queryset(self):
        try:
            return JuridicalProfileDocument.objects.select_related(
                'profile',
                'profile__natural_profile',
                'profile__natural_profile__base_user',
            ).filter(profile__natural_profile__base_user=self.request.user)
        except:
            return JuridicalProfileDocument.objects.none()

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        request.data['profile'] = request.user.natural_profile.juridical_profile.pk
        self.get_juridical_profile_query_set().update(status='checking')
        return super().create(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        self.get_juridical_profile_query_set().update(status='checking')
        return self.destroy(request, *args, **kwargs)
