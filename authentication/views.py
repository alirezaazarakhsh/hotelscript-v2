from django.shortcuts import get_object_or_404
from django.conf import settings
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.views import (
    TokenObtainPairView as JwtTokenObtainPairView,
    TokenRefreshView as JwtTokenRefreshView,
)
from rest_framework_simplejwt.exceptions import TokenError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .serializers import (
    AuthSerializer,
    JuridicalProfileDocumentSerializer,
    JuridicalProfileSerializer,
    NaturalProfileSerializer,
    AdminPanelTokenObtainSerializer,
    CardNumberSerializer,
    JuridicalCardNumberSerializer,
)
from .models import (
    BaseUser,
    OTP,
    JuridicalProfile,
    JuridicalProfileDocument,
    NaturalProfile,
    CardNumber,
    JuridicalCardNumber,
)
from .utils import generate_otp_code
from .sms.sms import send_logout_sms, send_otp_sms, send_welcome_sms


# ای پی ای خروج از اکانت کاربران 
class APILogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(
        operation_summary="خروج از حساب کاربری",
        operation_description="این API برای خروج کاربر از سیستم با باطل کردن توکن refresh استفاده می‌شود. توکن از کوکی خوانده می‌شود.",
        responses={200: 'OK', 400: 'Bad Request'}
    )
    def post(self, request, *args, **kwargs):
        try:
            refresh_token = request.COOKIES.get('refresh_token')
            if not refresh_token:
                return Response(
                    {"detail": "refresh_token not found in cookies"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            token = RefreshToken(token=refresh_token)
            token.blacklist()

            # ارسال پیامک خروج
            user = request.user
            phone = user.phone_number
            full_name = f"{user.first_name}{user.last_name}".strip()
            send_logout_sms(phone, full_name)

            # حذف کوکی‌ها (expire)
            response = Response({"detail": _("با موفقیت خارج شدید.")})
            response.delete_cookie(
                key='access_token',
                domain='.safarnameh24.com',
                samesite='None'
            )
            response.delete_cookie(
                key='refresh_token',
                domain='.safarnameh24.com',
                samesite='None'
            )
            return response

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
        responses={
            200: 'کد تایید با موفقیت ارسال شد',
            400: 'فرمت شماره صحیح نیست',
            403: 'شما قبلاً با موفقیت وارد شده‌اید',
            429: 'جهت دریافت کد جدید لطفا یک دقیقه صبر کنید',
            500: 'ارسال کد ناموفق بود'
        }
    )
    def post(self, request):
        if request.user.is_authenticated:
            return Response(
                {"detail": "شما قبلاً با موفقیت وارد شده‌اید."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = AuthSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"detail": "فرمت شماره صحیح نیست. شماره را با فرمت درست وارد کنید."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        phone = serializer.validated_data.get('phone')
        user = BaseUser.objects.get_by_phone_or_create(phone)

        # جلوگیری از ارسال بیش از حد OTP
        try:
            last_otp = user.otps.latest('created')
            remaining_time = (last_otp.expired - timezone.now()).total_seconds()
            if remaining_time > 0:
                return Response(
                    {"detail": "جهت دریافت کد جدید لطفا یک دقیقه صبر کنید"},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )
        except OTP.DoesNotExist:
            pass

        code = generate_otp_code()
        otp = OTP(user=user)
        otp.set_code(code)  # فرض می‌شود این متد زمان انقضا را به 60 ثانیه تنظیم می‌کند
        otp.save()

        # ارسال کد OTP به شماره موبایل
        sent = send_otp_sms(phone, code)
        if not sent:
            return Response(
                {"detail": "ارسال کد ناموفق بود. دوباره تلاش کنید."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({"detail": "کد تایید ارسال شد."}, status=status.HTTP_200_OK)





class TokenObtainPairView(JwtTokenObtainPairView):
    @swagger_auto_schema(
        operation_summary="ورود با کد تایید OTP",
        operation_description="گرفتن توکن JWT با استفاده از کد تأیید ارسال شده",
        responses={
            200: 'دریافت موفق توکن',
            403: 'قبلاً وارد شده‌اید',
            401: 'کد نامعتبر است'
        }
    )
    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return Response(
                {"detail": _("شما قبلاً وارد شده‌اید.")},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # گرفتن شماره تلفن و نام کامل کاربر (فرض بر این است که در serializer این داده‌ها هست)
        user = serializer.user  # فرض می‌کنیم serializer بعد از اعتبارسنجی، user رو داره
        phone_number = user.phone_number
        full_name = f"{user.first_name}{user.last_name}".strip()

        # ارسال پیام خوش آمدگویی
        send_welcome_sms(phone_number, full_name)

        # Set JWT tokens in HTTP-only cookies
        response = Response(status=status.HTTP_200_OK)
        access_token = serializer.validated_data.get('access')
        refresh_token = serializer.validated_data.get('refresh')
        if access_token:
            response.set_cookie(
                key='access_token',
                value=access_token,
                httponly=True,
                secure=True,
                samesite='None',
                domain='.safarnameh24.com',
                max_age=60*60*24,  # 1 day
            )
        if refresh_token:
            response.set_cookie(
                key='refresh_token',
                value=refresh_token,
                httponly=True,
                secure=True,
                samesite='None',
                domain='.safarnameh24.com',
                max_age=60*60*7,  # 7 days
            )
        return response




# ای پی ای آپدیت توکن کاربر 
class TokenRefreshView(JwtTokenRefreshView):
    @swagger_auto_schema(
        operation_summary="تازه‌سازی توکن JWT",
        operation_description="دریافت توکن جدید با استفاده از refresh token از کوکی",
        responses={200: 'توکن جدید با موفقیت صادر شد'}
    )
    def post(self, request, *args, **kwargs):
        # خواندن refresh_token از کوکی
        refresh_token = request.COOKIES.get('refresh_token')
        if not refresh_token:
            return Response(
                {"detail": "refresh_token not found in cookies"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        
        # استفاده از refresh_token برای تولید access جدید
        serializer = self.get_serializer(data={'refresh': refresh_token})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        
        # Set new access token and refresh token (if rotated) in HTTP-only cookies
        response = Response(status=status.HTTP_200_OK)
        access_token = serializer.validated_data.get('access')
        new_refresh_token = serializer.validated_data.get('refresh')
        
        if access_token:
            response.set_cookie(
                key='access_token',
                value=access_token,
                httponly=True,
                secure=True,
                samesite='None',
                domain='.safarnameh24.com',
                max_age=60*60*24,  # 1 day
            )
        
        # اگر refresh token جدید تولید شده (rotation enabled)، آن را هم ست کن
        if new_refresh_token:
            response.set_cookie(
                key='refresh_token',
                value=new_refresh_token,
                httponly=True,
                secure=True,
                samesite='None',
                domain='.safarnameh24.com',
                max_age=60*60*24*7,  # 7 days
            )
        
        return response



class AdminPanelLoginView(APIView):
    permission_classes = (AllowAny,)

    @swagger_auto_schema(
        operation_summary="ورود ادمین پنل گرافیکی با رمز پنل",
        operation_description="ادمین‌های سایت با شماره موبایل و رمز پنل گرافیکی وارد می‌شوند و JWT در کوکی ست می‌شود.",
        request_body=AdminPanelTokenObtainSerializer,
        responses={200: 'OK', 401: 'Unauthorized'}
    )
    def post(self, request, *args, **kwargs):
        serializer = AdminPanelTokenObtainSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Set JWT tokens in HTTP-only cookies
        response = Response(status=status.HTTP_200_OK)
        access_token = serializer.validated_data.get('access')
        refresh_token = serializer.validated_data.get('refresh')

        if access_token:
            response.set_cookie(
                key='access_token',
                value=access_token,
                httponly=True,
                secure=settings.COOKIE_SECURE,
                samesite=settings.COOKIE_SAMESITE,
                domain=settings.COOKIE_DOMAIN,
                max_age=60*60*24,
            )
        if refresh_token:
            response.set_cookie(
                key='refresh_token',
                value=refresh_token,
                httponly=True,
                secure=settings.COOKIE_SECURE,
                samesite=settings.COOKIE_SAMESITE,
                domain=settings.COOKIE_DOMAIN,
                max_age=60*60*24*7,
            )
        return response



#ای پی ای لیست پروفایل های حقوقی 
class JuridicalProfileListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="دریافت پروفایل حقوقی کاربر جاری",
        responses={
            200: JuridicalProfileSerializer(),
            404: "پروفایل حقوقی یافت نشد"
        }
    )
    def get(self, request):
        # اگر پروفایل حقیقی وجود نداشته باشد، پاسخ خالی اما موفق برگردان
        natural_profile = NaturalProfile.objects.filter(base_user=request.user).first()
        if not natural_profile:
            empty = {
                'has_natural_profile': False,
                'has_juridical_profile': False,
                'organization_name': '',
                'national_id': '',
                'registeration_number': '',
                'economical_code': '',
                'phone_number': '',
                'postal_code': '',
                'address': None,
                'email': None,
                'image': None,
                'status': None,
                'reject_reason': '',
                'documents': [],
                'card_numbers': [],
            }
            return Response(empty, status=status.HTTP_200_OK)

        juridical_profile = JuridicalProfile.objects.filter(natural_profile=natural_profile).first()
        if juridical_profile:
            data = JuridicalProfileSerializer(juridical_profile, context={'request': request}).data
            data['has_natural_profile'] = True
            data['has_juridical_profile'] = True
            return Response(data, status=status.HTTP_200_OK)

        # پروفایل حقوقی موجود نیست؛ دادهٔ خالی استاندارد برگردان
        empty = {
            'has_natural_profile': True,
            'has_juridical_profile': False,
            'organization_name': '',
            'national_id': '',
            'registeration_number': '',
            'economical_code': '',
            'phone_number': '',
            'postal_code': '',
            'address': None,
            'email': None,
            'image': None,
            'status': None,
            'reject_reason': '',
            'documents': [],
            'card_numbers': [],
        }
        return Response(empty, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="ایجاد پروفایل حقوقی",
        operation_description="""
        این API امکان ایجاد یک پروفایل حقوقی جدید برای کاربر احراز هویت‌شده را فراهم می‌کند.
        اگر کاربر از قبل پروفایل حقوقی داشته باشد، خطای 400 بازگردانده می‌شود.
        درخواست باید به صورت JSON ارسال شود.

        **ورودی‌ها**:
        - هدر `Authorization`: توکن احراز هویت (Bearer Token) الزامی است.
        - بدنه درخواست (application/json):
            - `organization_name` (اجباری): نام شرکت (رشته).
            - `national_id` (اجباری): شناسه ملی (رشته، دقیقاً ۱۱ رقم).
            - `registeration_number` (اجباری): شماره ثبت (رشته).
            - `economical_code` (اجباری): کد اقتصادی (رشته).
            - `phone_number` (اجباری): شماره تماس (رشته).
            - `postal_code` (اجباری): کد پستی (رشته، دقیقاً ۱۰ رقم).
            - `address` (اختیاری): آدرس شرکت (رشته).
            - `email` (اختیاری): ایمیل شرکت (رشته).
            - `image` (اختیاری): آدرس تصویر شرکت (رشته، URL).
            - `status` (اختیاری): وضعیت پروفایل (checking, accepted, rejected).
            - `reject_reason` (اختیاری): دلیل رد (رشته، در صورت رد شده بودن اجباری).
            - `card_numbers` (اختیاری): لیست شماره‌های کارت (حداکثر ۲ مورد، شامل card_number و iban).

        **خروجی‌ها**:
        - **201 Created**: پروفایل با موفقیت ایجاد شد و اطلاعات آن بازگشت داده می‌شود.
        - **400 Bad Request**: در صورت نامعتبر بودن داده‌ها یا وجود پروفایل از قبل.
        - **401 Unauthorized**: در صورت عدم ارائه توکن معتبر.
        """,
        request_body=JuridicalProfileSerializer,
        consumes=['application/json'],  # مشخص کردن نوع ورودی
        responses={
            201: JuridicalProfileSerializer(),
            400: "Bad Request",
            401: "Unauthorized"
        }
    )
    def post(self, request):
        try:
            natural_profile = NaturalProfile.objects.get(base_user=request.user)
            if hasattr(natural_profile, 'juridical_profile'):
                return Response(
                    {"detail": "این کاربر از قبل پروفایل حقوقی دارد."},
                    status=400
                )
            
            # چک کردن اگر تمام داده‌ها null یا خالی باشند
            if not request.data or all(value is None for value in request.data.values()):
                return Response(
                    {"detail": "هیچ اطلاعاتی ارائه نشده است. عملیات بدون خطا پایان یافت."},
                    status=200
                )
            
            serializer = JuridicalProfileSerializer(
                data=request.data,
                context={'request': request}
            )
            if serializer.is_valid():
                serializer.save(natural_profile=natural_profile)
                return Response(serializer.data, status=201)
            return Response(serializer.errors, status=400)
        except NaturalProfile.DoesNotExist:
            return Response(
                {"detail": "برای ایجاد پروفایل حقوقی، ابتدا باید پروفایل حقیقی ایجاد کنید."},
                status=400
            )




class JuridicalProfileDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="دریافت اطلاعات پروفایل حقوقی کاربر جاری",
        operation_description="""
        این API اطلاعات پروفایل حقوقی کاربر احراز هویت‌شده را بازمی‌گرداند.
        اگر پروفایل وجود نداشته باشد، یک پروفایل خالی با اطلاعات پایه کاربر (بدون ذخیره در دیتابیس) بازگشت داده می‌شود.

        **ورودی‌ها**:
        - هدر `Authorization`: توکن احراز هویت (Bearer Token) الزامی است.

        **خروجی‌ها**:
        - **200 OK**: اطلاعات پروفایل شامل نام شرکت، شناسه ملی، شماره ثبت، کد اقتصادی، شماره تماس، کد پستی، آدرس، ایمیل، وضعیت، دلیل رد، مدارک و لیست شماره‌های کارت (حداکثر ۲ شماره).
        - **401 Unauthorized**: در صورت عدم ارائه توکن معتبر.
        """,
        responses={200: JuridicalProfileSerializer(), 401: "Unauthorized"}
    )
    def get(self, request):
        try:
            profile = request.user.natural_profile.juridical_profile
        except AttributeError:
            try:
                natural_profile = request.user.natural_profile
            except AttributeError:
                natural_profile = NaturalProfile(base_user=request.user)
            profile = JuridicalProfile(natural_profile=natural_profile)
        serializer = JuridicalProfileSerializer(profile, context={'request': request})
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="ویرایش پروفایل حقوقی کاربر جاری",
        operation_description="""
        این API امکان ویرایش پروفایل حقوقی کاربر جاری یا ایجاد پروفایل جدید (در صورت عدم وجود) را فراهم می‌کند.
        درخواست باید به صورت `multipart/form-data` ارسال شود تا امکان آپلود فایل تصویر وجود داشته باشد.
        تمام فیلدها اختیاری هستند و می‌توانند به صورت جزئی (partial) آپدیت شوند.
        شماره‌های کارت از طریق این API قابل ویرایش هستند.

        **ورودی‌ها**:
        - هدر `Authorization`: توکن احراز هویت (Bearer Token) الزامی است.
        - بدنه درخواست (`multipart/form-data`):
            - `organization_name` (اختیاری): نام شرکت (رشته).
            - `national_id` (اختیاری): شناسه ملی (رشته، دقیقاً ۱۱ رقم).
            - `registeration_number` (اختیاری): شماره ثبت (رشته).
            - `economical_code` (اختیاری): کد اقتصادی (رشته).
            - `phone_number` (اختیاری): شماره تماس (رشته).
            - `postal_code` (اختیاری): کد پستی (رشته، دقیقاً ۱۰ رقم).
            - `address` (اختیاری): آدرس شرکت (رشته).
            - `email` (اختیاری): ایمیل شرکت (رشته).
            - `image` (اختیاری): فایل تصویر شرکت (فرمت‌های مجاز: jpg, png).
            - `status` (اختیاری): وضعیت پروفایل (checking, accepted, rejected).
            - `reject_reason` (اختیاری): دلیل رد (رشته، در صورت رد شده بودن اجباری).
            - `card_numbers` (اختیاری): لیست شماره‌های کارت (حداکثر ۲ مورد، شامل id برای ویرایش).

        **خروجی‌ها**:
        - **200 OK**: در صورت آپدیت موفق پروفایل، اطلاعات به‌روز شده بازگشت داده می‌شود.
        - **201 Created**: در صورت ایجاد پروفایل جدید، اطلاعات پروفایل ایجادشده بازگشت داده می‌شود.
        - **400 Bad Request**: در صورت نامعتبر بودن داده‌های ورودی.
        - **401 Unauthorized**: در صورت عدم ارائه توکن معتبر.
        """,
        request_body=JuridicalProfileSerializer,
        consumes=['multipart/form-data'],
        responses={
            200: JuridicalProfileSerializer(),
            201: JuridicalProfileSerializer(),
            400: "Bad Request",
            401: "Unauthorized"
        }
    )
    def put(self, request):
        print("Request data:", request.data)
        try:
            profile = request.user.natural_profile.juridical_profile
        except AttributeError:
            try:
                natural_profile = request.user.natural_profile
            except AttributeError:
                return Response({"detail": "پروفایل حقیقی یافت نشد"}, status=404)
            profile = JuridicalProfile(natural_profile=natural_profile)

        serializer = JuridicalProfileSerializer(
            profile,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK if profile.id else status.HTTP_201_CREATED)
        print("Update errors:", serializer.errors)
        return Response(serializer.errors, status=400)

    @swagger_auto_schema(
        operation_summary="حذف پروفایل حقوقی کاربر جاری",
        operation_description="""
        این API پروفایل حقوقی کاربر جاری را حذف می‌کند.
        در صورت حذف پروفایل، تمام مدارک و شماره‌های کارت مرتبط نیز حذف می‌شوند.
        اگر پروفایل وجود نداشته باشد، خطای 404 بازگردانده می‌شود.

        **ورودی‌ها**:
        - هدر `Authorization`: توکن احراز هویت (Bearer Token) الزامی است.

        **خروجی‌ها**:
        - **204 No Content**: در صورت حذف موفق پروفایل.
        - **404 Not Found**: در صورت عدم وجود پروفایل.
        - **401 Unauthorized**: در صورت عدم ارائه توکن معتبر.
        """,
        responses={
            204: "پروفایل حذف شد",
            404: "پروفایل حقوقی یافت نشد",
            401: "Unauthorized"
        }
    )
    def delete(self, request):
        try:
            profile = request.user.natural_profile.juridical_profile
            profile.delete()
            return Response(status=204)
        except AttributeError:
            return Response({"detail": "پروفایل حقیقی یا حقوقی یافت نشد"}, status=404)
        


class NaturalProfileListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="دریافت پروفایل حقیقی کاربر جاری",
        operation_description="""
        این API اطلاعات پروفایل حقیقی کاربر احراز هویت‌شده را بازمی‌گرداند.
        اگر پروفایل وجود نداشته باشد، یک پروفایل خالی با اطلاعات پایه کاربر (بدون ذخیره در دیتابیس) بازگشت داده می‌شود.

        **ورودی‌ها**:
        - هدر `Authorization`: توکن احراز هویت (Bearer Token) الزامی است.

        **خروجی‌ها**:
        - **200 OK**: اطلاعات پروفایل شامل نام، نام خانوادگی، ایمیل، کد ملی، تصویر، کد پستی، آدرس، سطح کاربری، نام سطح و لیست شماره‌های کارت (حداکثر ۲ شماره).
        - **401 Unauthorized**: در صورت عدم ارائه توکن معتبر.
        """,
        responses={200: NaturalProfileSerializer(), 401: "Unauthorized"}
    )
    def get(self, request):
        user = request.user
        try:
            profile = user.natural_profile
        except NaturalProfile.DoesNotExist:
            profile = NaturalProfile(base_user=user)
        serializer = NaturalProfileSerializer(profile, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="ایجاد پروفایل حقیقی",
        operation_description="""
        این API امکان ایجاد یک پروفایل حقیقی جدید برای کاربر احراز هویت‌شده را فراهم می‌کند.
        اگر کاربر از قبل پروفایل داشته باشد، خطای 400 بازگردانده می‌شود.
        درخواست باید به صورت `multipart/form-data` ارسال شود تا امکان آپلود تصویر پروفایل وجود داشته باشد.

        **ورودی‌ها**:
        - هدر `Authorization`: توکن احراز هویت (Bearer Token) الزامی است.
        - بدنه درخواست (`multipart/form-data`):
            - `first_name` (اختیاری): نام کاربر (رشته).
            - `last_name` (اختیاری): نام خانوادگی کاربر (رشته).
            - `email` (اختیاری): ایمیل کاربر (رشته).
            - `national_code` (اختیاری): کد ملی (رشته، دقیقاً ۱۰ رقم).
            - `image` (اختیاری): فایل تصویر پروفایل (فرمت‌های مجاز: jpg, png).
            - `postal_code` (اختیاری): کد پستی (رشته، دقیقاً ۱۰ رقم).
            - `address` (اختیاری): آدرس کاربر (رشته).
            - `level` (اختیاری): شناسه سطح کاربری (عدد صحیح).
            - `card_numbers` (اختیاری): لیست شماره‌های کارت (حداکثر ۲ مورد).

        **خروجی‌ها**:
        - **201 Created**: پروفایل با موفقیت ایجاد شد و اطلاعات آن بازگشت داده می‌شود.
        - **400 Bad Request**: در صورت نامعتبر بودن داده‌ها یا وجود پروفایل از قبل.
        - **401 Unauthorized**: در صورت عدم ارائه توکن معتبر.
        """,
        request_body=NaturalProfileSerializer,
        responses={
            201: NaturalProfileSerializer(),
            400: "Bad Request",
            401: "Unauthorized"
        }
    )
    def post(self, request):
        user = request.user
        if NaturalProfile.objects.filter(base_user=user).exists():
            return Response(
                {"detail": "این کاربر از قبل پروفایل حقیقی دارد."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = NaturalProfileSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            profile = serializer.save()
            return Response(
                NaturalProfileSerializer(profile, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




class NaturalProfileDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="دریافت اطلاعات پروفایل حقیقی کاربر جاری",
        operation_description="""
        این API اطلاعات پروفایل حقیقی کاربر احراز هویت‌شده را بازمی‌گرداند.
        اگر پروفایل وجود نداشته باشد، یک پروفایل خالی با اطلاعات پایه کاربر (بدون ذخیره در دیتابیس) بازگشت داده می‌شود.

        **ورودی‌ها**:
        - هدر `Authorization`: توکن احراز هویت (Bearer Token) الزامی است.

        **خروجی‌ها**:
        - **200 OK**: اطلاعات پروفایل شامل نام، نام خانوادگی، ایمیل، کد ملی، تصویر، کد پستی، آدرس، سطح کاربری، نام سطح و لیست شماره‌های کارت (حداکثر ۲ شماره).
        - **401 Unauthorized**: در صورت عدم ارائه توکن معتبر.
        """,
        responses={200: NaturalProfileSerializer(), 401: "Unauthorized"}
    )
    def get(self, request):
        try:
            profile = request.user.natural_profile
        except AttributeError:
            profile = NaturalProfile(base_user=request.user)
        serializer = NaturalProfileSerializer(profile, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="ویرایش پروفایل حقیقی کاربر جاری",
        operation_description="""
        این API امکان ویرایش پروفایل حقیقی کاربر جاری یا ایجاد پروفایل جدید (در صورت عدم وجود) را فراهم می‌کند.
        درخواست باید به صورت `multipart/form-data` ارسال شود تا امکان آپلود تصویر پروفایل وجود داشته باشد.
        تمام فیلدها اختیاری هستند و می‌توانند به صورت جزئی (partial) آپدیت شوند.
        شماره‌های کارت از طریق این API قابل ویرایش هستند.

        **ورودی‌ها**:
        - هدر `Authorization`: توکن احراز هویت (Bearer Token) الزامی است.
        - بدنه درخواست (`multipart/form-data`):
            - `first_name` (اختیاری): نام کاربر (رشته).
            - `last_name` (اختیاری): نام خانوادگی کاربر (رشته).
            - `email` (اختیاری): ایمیل کاربر (رشته).
            - `national_code` (اختیاری): کد ملی (رشته، دقیقاً ۱۰ رقم).
            - `image` (اختیاری): فایل تصویر پروفایل (فرمت‌های مجاز: jpg, png).
            - `postal_code` (اختیاری): کد پستی (رشته، دقیقاً ۱۰ رقم).
            - `address` (اختیاری): آدرس کاربر (رشته).
            - `level` (اختیاری): شناسه سطح کاربری (عدد صحیح).
            - `card_numbers` (اختیاری): لیست شماره‌های کارت (حداکثر ۲ مورد، شامل id برای ویرایش).

        **خروجی‌ها**:
        - **200 OK**: در صورت آپدیت موفق پروفایل، اطلاعات به‌روز شده بازگشت داده می‌شود.
        - **201 Created**: در صورت ایجاد پروفایل جدید، اطلاعات پروفایل ایجادشده بازگشت داده می‌شود.
        - **400 Bad Request**: در صورت نامعتبر بودن داده‌های ورودی.
        - **401 Unauthorized**: در صورت عدم ارائه توکن معتبر.
        """,
        request_body=NaturalProfileSerializer,
        responses={
            200: NaturalProfileSerializer(),
            201: NaturalProfileSerializer(),
            400: "Bad Request",
            401: "Unauthorized"
        }
    )
    def put(self, request):
        try:
            profile = request.user.natural_profile
        except AttributeError:
            profile = NaturalProfile(base_user=request.user)
            serializer = NaturalProfileSerializer(profile, data=request.data, context={'request': request})
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer = NaturalProfileSerializer(profile, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_summary="حذف پروفایل حقیقی کاربر جاری",
        operation_description="""
        این API پروفایل حقیقی کاربر جاری را حذف می‌کند.
        در صورت حذف پروفایل، تمام شماره‌های کارت مرتبط نیز حذف می‌شوند.
        اگر پروفایل وجود نداشته باشد، خطای 404 بازگردانده می‌شود.

        **ورودی‌ها**:
        - هدر `Authorization`: توکن احراز هویت (Bearer Token) الزامی است.

        **خروجی‌ها**:
        - **204 No Content**: در صورت حذف موفق پروفایل.
        - **404 Not Found**: در صورت عدم وجود پروفایل.
        - **401 Unauthorized**: در صورت عدم ارائه توکن معتبر.
        """,
        responses={
            204: "پروفایل حذف شد",
            404: "پروفایل حقیقی یافت نشد",
            401: "Unauthorized"
        }
    )
    def delete(self, request):
        try:
            profile = request.user.natural_profile
            profile.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except AttributeError:
            return Response({"detail": "پروفایل حقیقی یافت نشد"}, status=status.HTTP_404_NOT_FOUND)
        
        



# 📄 لیست و ایجاد
class JuridicalProfileDocumentListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_summary="لیست مدارک پروفایل حقوقی",
        tags=["JuridicalProfile-Document"],
        responses={200: JuridicalProfileDocumentSerializer(many=True)}
    )
    def get(self, request):
        documents = JuridicalProfileDocument.objects.all()
        serializer = JuridicalProfileDocumentSerializer(documents, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="آپلود مدارک برای پروفایل حقوقی",
        tags=["JuridicalProfile-Document"],
        request_body=JuridicalProfileDocumentSerializer,
        responses={
            201: JuridicalProfileDocumentSerializer(many=True),
            400: "خطا در داده‌های ورودی یا عدم موفقیت در آپلود",
            404: "پروفایل حقوقی یافت نشد"
        }
    )
    def post(self, request):
        print("request.FILES:", request.FILES)
        print("request.data:", request.data)

        # بررسی وجود پروفایل حقوقی
        try:
            natural_profile = request.user.natural_profile
            profile = natural_profile.juridical_profile
        except (AttributeError, Exception) as e:
            print(f"Error fetching profile: {e}")
            return Response(
                {'detail': 'پروفایل حقوقی یافت نشد.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # بررسی وجود فایل‌ها
        uploaded_files = request.FILES.getlist('file')
        if not uploaded_files:
            return Response(
                {'detail': 'هیچ فایلی آپلود نشده است.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        response_data = []
        errors = []

        # پردازش هر فایل
        for uploaded_file in uploaded_files:
            print(f"Processing file: {uploaded_file.name}, type: {uploaded_file.content_type}")
            data = request.data.copy()
            data['file'] = uploaded_file
            serializer = JuridicalProfileDocumentSerializer(data=data, context={'request': request})
            if serializer.is_valid():
                try:
                    serializer.save(profile=profile)
                    # بعد از ذخیره، داده‌ها رو با تمام فیلدهای خواندنی سریالایزر بگیر
                    saved_instance = JuridicalProfileDocument.objects.get(id=serializer.data['id'])
                    response_data.append(JuridicalProfileDocumentSerializer(saved_instance, context={'request': request}).data)
                except Exception as e:
                    print(f"Error saving {uploaded_file.name}: {e}")
                    errors.append(f"خطا در ذخیره فایل {uploaded_file.name}: {str(e)}")
            else:
                print(f"Errors for {uploaded_file.name}: {serializer.errors}")
                errors.append(f"خطا در اعتبارسنجی فایل {uploaded_file.name}: {serializer.errors}")

        # مدیریت نتیجه
        if not response_data and errors:
            return Response(
                {'detail': 'هیچ فایلی با موفقیت آپلود نشد.', 'errors': errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        elif not response_data:
            return Response(
                {'detail': 'هیچ فایلی با موفقیت آپلود نشد.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(response_data, status=status.HTTP_201_CREATED)
    
    
    

class JuridicalProfileDocumentRetrieveUpdateDestroyAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="ویرایش مدرک پروفایل حقوقی",
        tags=["JuridicalProfile-Document"],
        request_body=JuridicalProfileDocumentSerializer,
        responses={
            200: JuridicalProfileDocumentSerializer(),
            400: "خطا در داده‌های ورودی",
            404: "مدرک یافت نشد"
        }
    )
    def put(self, request, pk):
        document = get_object_or_404(JuridicalProfileDocument, pk=pk)
        serializer = JuridicalProfileDocumentSerializer(document, data=request.data, context={'request': request}, partial=True)
        if serializer.is_valid():
            try:
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            except Exception as e:
                return Response(
                    {'detail': f'خطا در ذخیره مدرک: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_summary="حذف مدرک پروفایل حقوقی",
        tags=["JuridicalProfile-Document"],
        responses={
            204: 'مدرک حذف شد',
            404: 'مدرک یافت نشد'
        }
    )
    def delete(self, request, pk):
        document = get_object_or_404(JuridicalProfileDocument, pk=pk)
        try:
            document.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response(
                {'detail': f'خطا در حذف مدرک: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    


# ====================================================
# مدیریت شماره کارت‌های حقیقی و حقوقی
# ====================================================

class CardNumberManagementView(APIView):
    """
    API برای مدیریت شماره کارت‌های حقیقی و حقوقی
    
    این API امکان مدیریت کامل (مشاهده، افزودن، ویرایش، حذف) شماره کارت‌های بانکی را فراهم می‌کند.
    هر پروفایل (حقیقی یا حقوقی) می‌تواند حداکثر ۲ شماره کارت داشته باشد.
    
    نوع پروفایل (profile_type):
    - natural: پروفایل حقیقی
    - juridical: پروفایل حقوقی
    
    نوع عملیات (action):
    - list: مشاهده لیست شماره کارت‌ها
    - add: افزودن شماره کارت جدید
    - update: ویرایش شماره کارت موجود
    - delete: حذف شماره کارت
    """
    permission_classes = [IsAuthenticated]

    def get_profile(self, user, profile_type):
        """دریافت پروفایل بر اساس نوع"""
        if profile_type == 'natural':
            return get_object_or_404(NaturalProfile, base_user=user)
        elif profile_type == 'juridical':
            natural_profile = get_object_or_404(NaturalProfile, base_user=user)
            return get_object_or_404(JuridicalProfile, natural_profile=natural_profile)
        else:
            return None

    def get_serializer_class(self, profile_type):
        """دریافت سریالایزر بر اساس نوع پروفایل"""
        if profile_type == 'natural':
            return CardNumberSerializer
        elif profile_type == 'juridical':
            return JuridicalCardNumberSerializer
        return None

    @swagger_auto_schema(
        operation_summary="مدیریت یکپارچه شماره کارت‌ها",
        operation_description="""
        API یکپارچه برای مدیریت کامل شماره کارت‌های حقیقی و حقوقی
        
        **پارامترها:**
        - profile_type: نوع پروفایل (natural یا juridical) - الزامی
        - action: نوع عملیات (list, add, update, delete) - الزامی
        - card_id: شناسه شماره کارت (فقط برای update و delete) - اختیاری
        - card_number: شماره کارت ۱۶ رقمی (برای add و update) - اختیاری
        - iban: شماره شبا ۲۴ رقمی (برای add و update) - اختیاری
        - account_holder_name: نام صاحب حساب به فارسی (برای add و update) - اختیاری
        
        **نوع عملیات‌ها:**
        
        1. مشاهده لیست (list):
           - فقط profile_type و action=list لازم است
           - برمی‌گرداند: لیست تمام شماره کارت‌های پروفایل
        
        2. افزودن (add):
           - profile_type, action=add, card_number الزامی
           - iban و account_holder_name اختیاری
           - محدودیت: حداکثر ۲ شماره کارت برای هر پروفایل
        
        3. ویرایش (update):
           - profile_type, action=update, card_id الزامی
           - می‌توانید card_number, iban, account_holder_name را به صورت دلخواه ویرایش کنید
           - فقط فیلدهای ارسالی تغییر می‌کنند
        
        4. حذف (delete):
           - profile_type, action=delete, card_id الزامی
           - شماره کارت به طور کامل حذف می‌شود
        
        **محدودیت‌ها:**
        - هر پروفایل حداکثر ۲ شماره کارت
        - شماره کارت باید یکتا باشد
        - شماره شبا باید یکتا باشد
        - نام صاحب حساب فقط شامل حروف فارسی و فاصله
        
        **مثال‌های استفاده:**
        
        مشاهده لیست:
        {
            "profile_type": "natural",
            "action": "list"
        }
        
        افزودن:
        {
            "profile_type": "natural",
            "action": "add",
            "card_number": "6037991234567890",
            "iban": "123456789012345678901234",
            "account_holder_name": "علی احمدی"
        }
        
        ویرایش:
        {
            "profile_type": "natural",
            "action": "update",
            "card_id": 1,
            "iban": "987654321098765432109876"
        }
        
        حذف:
        {
            "profile_type": "juridical",
            "action": "delete",
            "card_id": 2
        }
        """,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['profile_type', 'action'],
            properties={
                'profile_type': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='نوع پروفایل',
                    enum=['natural', 'juridical']
                ),
                'action': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='نوع عملیات',
                    enum=['list', 'add', 'update', 'delete']
                ),
                'card_id': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='شناسه شماره کارت (فقط برای update و delete)',
                    example=1
                ),
                'card_number': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='شماره کارت ۱۶ رقمی (برای add و update)',
                    pattern='^\\d{16}$',
                    example='6037991234567890'
                ),
                'iban': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='شماره شبا ۲۴ رقمی (برای add و update)',
                    pattern='^\\d{24}$',
                    example='123456789012345678901234'
                ),
                'account_holder_name': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='نام صاحب حساب به فارسی (برای add و update)',
                    example='علی احمدی'
                ),
            }
        ),
        tags=['cardnumber-profile'],
        responses={
            200: openapi.Response(
                description="عملیات با موفقیت انجام شد",
                examples={
                    "application/json": {
                        "list": [
                            {
                                "id": 1,
                                "card_number": "6037991234567890",
                                "iban": "123456789012345678901234",
                                "account_holder_name": "علی احمدی"
                            }
                        ],
                        "add": {
                            "id": 1,
                            "card_number": "6037991234567890",
                            "iban": "123456789012345678901234",
                            "account_holder_name": "علی احمدی"
                        },
                        "update": {
                            "id": 1,
                            "card_number": "6037991234567890",
                            "iban": "987654321098765432109876",
                            "account_holder_name": "علی احمدی"
                        },
                        "delete": {
                            "detail": "شماره کارت با موفقیت حذف شد."
                        }
                    }
                }
            ),
            400: 'داده‌های نامعتبر یا عملیات نامعتبر',
            404: 'پروفایل یا شماره کارت یافت نشد'
        }
    )
    def post(self, request):
        """مدیریت یکپارچه شماره کارت‌ها"""
        profile_type = request.data.get('profile_type')
        action = request.data.get('action')
        
        # اعتبارسنجی پارامترهای اصلی
        if not profile_type or profile_type not in ['natural', 'juridical']:
            return Response(
                {'detail': 'نوع پروفایل (profile_type) باید natural یا juridical باشد.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not action or action not in ['list', 'add', 'update', 'delete']:
            return Response(
                {'detail': 'نوع عملیات (action) باید یکی از موارد list, add, update, delete باشد.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        profile = self.get_profile(request.user, profile_type)
        serializer_class = self.get_serializer_class(profile_type)
        model_class = CardNumber if profile_type == 'natural' else JuridicalCardNumber
        
        # مشاهده لیست
        if action == 'list':
            card_numbers = profile.card_numbers.all()
            serializer = serializer_class(card_numbers, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        # افزودن شماره کارت جدید
        elif action == 'add':
            serializer = serializer_class(
                data=request.data,
                context={'request': request, 'profile': profile}
            )
            
            if serializer.is_valid():
                serializer.save(profile=profile)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # ویرایش شماره کارت
        elif action == 'update':
            card_id = request.data.get('card_id')
            
            if not card_id:
                return Response(
                    {'detail': 'شناسه کارت (card_id) برای ویرایش الزامی است.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            card_number = get_object_or_404(model_class, id=card_id, profile=profile)
            
            serializer = serializer_class(
                card_number,
                data=request.data,
                partial=True,
                context={'request': request, 'profile': profile}
            )
            
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # حذف شماره کارت
        elif action == 'delete':
            card_id = request.data.get('card_id')
            
            if not card_id:
                return Response(
                    {'detail': 'شناسه کارت (card_id) برای حذف الزامی است.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            card_number = get_object_or_404(model_class, id=card_id, profile=profile)
            
            try:
                card_number.delete()
                return Response(
                    {'detail': 'شماره کارت با موفقیت حذف شد.'},
                    status=status.HTTP_200_OK
                )
            except Exception as e:
                return Response(
                    {'detail': f'خطا در حذف شماره کارت: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
