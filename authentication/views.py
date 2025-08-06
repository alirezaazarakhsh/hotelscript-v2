from django.shortcuts import get_object_or_404
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
)
from .models import (
    BaseUser,
    OTP,
    JuridicalProfile,
    JuridicalProfileDocument,
    NaturalProfile,
)
from .utils import generate_otp_code
from .sms.sms import send_logout_sms, send_otp_sms, send_welcome_sms


# ای پی ای خروج از اکانت کاربران 
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
            refresh_token = self.request.data.get('refresh_token')
            if not refresh_token:
                return Response(
                    {"detail": "refresh_token is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            token = RefreshToken(token=refresh_token)
            token.blacklist()

            # ارسال پیامک خروج
            user = request.user
            phone = user.phone_number  
            full_name = f"{user.first_name}{user.last_name}".strip()
            send_logout_sms(phone, full_name)

            return Response({"detail": _("با موفقیت خارج شدید.")})

        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )




#ای پی ای ارسال otp برای کاربران 
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
            403: 'شما قبلاً با موفقیت  وارد شده‌اید',
            429: 'جهت دریافت کد جدید لطفا یک دقیقه صبر کنید',
            500: 'ارسال کد ناموفق بود'
        }
    )
    def post(self, request):
        if request.user.is_authenticated:
            return Response(
                {"detail": "شما قبلاً  با موفقیت وارد شده‌اید."},
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
        otp.set_code(code)
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

        return Response(serializer.validated_data, status=status.HTTP_200_OK)




# ای پی ای آپدیت توکن کاربر 
class TokenRefreshView(JwtTokenRefreshView):
    @swagger_auto_schema(
        operation_summary="تازه‌سازی توکن JWT",
        operation_description="دریافت توکن جدید با استفاده از refresh token",
        responses={200: 'توکن جدید با موفقیت صادر شد'}
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        return Response(serializer.validated_data, status=status.HTTP_200_OK)



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
        try:
            # ابتدا پروفایل حقیقی کاربر را پیدا می‌کنیم
            natural_profile = NaturalProfile.objects.get(base_user=request.user)
            
            # سپس پروفایل حقوقی مرتبط با آن را پیدا می‌کنیم
            juridical_profile = JuridicalProfile.objects.get(natural_profile=natural_profile)
            
            serializer = JuridicalProfileSerializer(juridical_profile, context={'request': request})
            return Response(serializer.data)
            
        except NaturalProfile.DoesNotExist:
            return Response(
                {"detail": "پروفایل حقیقی برای این کاربر یافت نشد."},
                status=404
            )
        except JuridicalProfile.DoesNotExist:
            return Response(
                {"detail": "پروفایل حقوقی برای این کاربر یافت نشد."},
                status=404
            )

    @swagger_auto_schema(
        operation_summary="ایجاد پروفایل حقوقی",
        request_body=JuridicalProfileSerializer,
        responses={
            201: JuridicalProfileSerializer(),
            400: "داده‌های نامعتبر"
        }
    )
    def post(self, request):
        try:
            # بررسی می‌کنیم که کاربر پروفایل حقیقی دارد
            natural_profile = NaturalProfile.objects.get(base_user=request.user)
            
            # بررسی می‌کنیم که کاربر از قبل پروفایل حقوقی ندارد
            if hasattr(natural_profile, 'juridical_profile'):
                return Response(
                    {"detail": "این کاربر از قبل پروفایل حقوقی دارد."},
                    status=400
                )
            
            serializer = JuridicalProfileSerializer(
                data=request.data,
                context={'request': request}
            )
            
            if serializer.is_valid():
                # پروفایل حقیقی را به داده‌های سریالایزر اضافه می‌کنیم
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
        operation_summary="دریافت پروفایل حقوقی کاربر جاری",
        responses={200: JuridicalProfileSerializer()}
    )
    def get(self, request):
        from .models import NaturalProfile, JuridicalProfile
        try:
            profile = request.user.natural_profile.juridical_profile
        except AttributeError:
            try:
                natural_profile = request.user.natural_profile
            except AttributeError:
                natural_profile = NaturalProfile(base_user=request.user)
            profile = JuridicalProfile(natural_profile=natural_profile)  # شیء فیک
        serializer = JuridicalProfileSerializer(profile, context={'request': request})
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="ویرایش پروفایل حقوقی کاربر جاری",
        request_body=JuridicalProfileSerializer,
        responses={200: JuridicalProfileSerializer()}
    )
    def put(self, request):
        try:
            profile = request.user.natural_profile.juridical_profile
        except AttributeError:
            return Response({"detail": "پروفایل حقیقی یا حقوقی یافت نشد"}, status=404)

        serializer = JuridicalProfileSerializer(
            profile,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    @swagger_auto_schema(
        operation_summary="حذف پروفایل حقوقی کاربر جاری",
        responses={204: "پروفایل حذف شد"}
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
        responses={200: NaturalProfileSerializer()}
    )
    def get(self, request):
        user = request.user

        try:
            profile = user.natural_profile
        except NaturalProfile.DoesNotExist:
            # نمونه‌ی موقت بدون ذخیره‌سازی در دیتابیس
            profile = NaturalProfile(base_user=user)

        serializer = NaturalProfileSerializer(profile, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="ایجاد پروفایل حقیقی",
        request_body=NaturalProfileSerializer,
        responses={
            201: NaturalProfileSerializer(),
            400: "داده‌های نامعتبر یا پروفایل موجود"
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
            profile = serializer.save(base_user=user)
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
        - **200 OK**: اطلاعات پروفایل شامل نام، نام خانوادگی، ایمیل، کد ملی، تصویر، کد پستی، آدرس، سطح کاربری و نام سطح.
        - **401 Unauthorized**: در صورت عدم ارائه توکن معتبر.

        **مثال پاسخ**:
        ```json
        {
            "first_name": "علی",
            "last_name": "احمدی",
            "email": "ali@example.com",
            "national_code": "1234567890",
            "image": "https://cps.safarnameh24.com/media/profile_images/image.jpg",
            "postal_code": "1234567890",
            "address": "تهران، خیابان نمونه",
            "level": 1,
            "level_name": "کاربر عادی"
        }
        ```
        """,
        responses={200: NaturalProfileSerializer(), 401: "Unauthorized"}
    )
    def get(self, request):
        try:
            profile = request.user.natural_profile
        except AttributeError:
            profile = NaturalProfile(base_user=request.user)
        serializer = NaturalProfileSerializer(profile, context={'request': request})
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="ویرایش یا ایجاد پروفایل حقیقی کاربر جاری",
        operation_description="""
        این API امکان ویرایش پروفایل حقیقی کاربر جاری یا ایجاد پروفایل جدید (در صورت عدم وجود) را فراهم می‌کند.
        درخواست باید به صورت `multipart/form-data` ارسال شود تا امکان آپلود تصویر پروفایل وجود داشته باشد.
        تمام فیلدها اختیاری هستند و می‌توانند به صورت جزئی (partial) آپدیت شوند.

        **ورودی‌ها**:
        - هدر `Authorization`: توکن احراز هویت (Bearer Token) الزامی است.
        - بدنه درخواست (`multipart/form-data`):
            - `first_name` (اختیاری): نام کاربر (رشته).
            - `last_name` (اختیاری): نام خانوادگی کاربر (رشته).
            - `email` (اختیاری): ایمیل کاربر (رشته).
            - `national_code` (اختیاری): کد ملی (رشته، حداکثر 10 رقم).
            - `image` (اختیاری): فایل تصویر پروفایل (فرمت‌های مجاز: jpg, png).
            - `postal_code` (اختیاری): کد پستی (رشته، حداکثر 10 رقم).
            - `address` (اختیاری): آدرس کاربر (رشته).
            - `level` (اختیاری): شناسه سطح کاربری (عدد صحیح).

        **خروجی‌ها**:
        - **200 OK**: در صورت آپدیت موفق پروفایل، اطلاعات به‌روز شده بازگشت داده می‌شود.
        - **201 Created**: در صورت ایجاد پروفایل جدید، اطلاعات پروفایل ایجادشده بازگشت داده می‌شود.
        - **400 Bad Request**: در صورت نامعتبر بودن داده‌های ورودی.
        - **401 Unauthorized**: در صورت عدم ارائه توکن معتبر.

        **مثال درخواست**:
        ```
        Content-Type: multipart/form-data
        Authorization: Bearer <your_token>
        
        first_name=علی
        last_name=احمدی
        image=<file.jpg>
        ```

        **مثال پاسخ**:
        ```json
        {
            "first_name": "علی",
            "last_name": "احمدی",
            "email": "ali@example.com",
            "national_code": "1234567890",
            "image": "https://cps.safarnameh24.com/media/profile_images/image.jpg",
            "postal_code": "1234567890",
            "address": "تهران، خیابان نمونه",
            "level": 1,
            "level_name": "کاربر عادی"
        }
        ```
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
            # ایجاد پروفایل جدید اگر وجود نداشته باشد
            profile = NaturalProfile(base_user=request.user)
            serializer = NaturalProfileSerializer(profile, data=request.data, context={'request': request})
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=201)
            return Response(serializer.errors, status=400)

        # آپدیت پروفایل موجود
        serializer = NaturalProfileSerializer(profile, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    @swagger_auto_schema(
        operation_summary="حذف پروفایل حقیقی کاربر جاری",
        operation_description="""
        این API پروفایل حقیقی کاربر جاری را حذف می‌کند.
        در صورت عدم وجود پروفایل، خطای 404 بازگردانده می‌شود.

        **ورودی‌ها**:
        - هدر `Authorization`: توکن احراز هویت (Bearer Token) الزامی است.

        **خروجی‌ها**:
        - **204 No Content**: در صورت حذف موفق پروفایل.
        - **404 Not Found**: در صورت عدم وجود پروفایل.
        - **401 Unauthorized**: در صورت عدم ارائه توکن معتبر.

        **مثال پاسخ**:
        ```json
        {}
        ```
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
            return Response(status=204)
        except AttributeError:
            return Response({"detail": "پروفایل حقیقی یافت نشد"}, status=404)




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
        operation_summary="آپلود مدرک برای پروفایل حقوقی",
        tags=["JuridicalProfile-Document"],
        request_body=JuridicalProfileDocumentSerializer,
        responses={
            201: JuridicalProfileDocumentSerializer(),
            400: "خطا در داده‌های ورودی",
            404: "پروفایل حقوقی یافت نشد"
        }
    )
    def post(self, request):
        # چاپ برای دیباگ
        print("request.FILES:", request.FILES)
        print("request.data:", request.data)

        # بررسی وجود پروفایل حقوقی
        try:
            natural_profile = request.user.natural_profile
            profile = natural_profile.juridical_profile
        except AttributeError:
            return Response(
                {'detail': 'پروفایل حقوقی یافت نشد.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # بررسی وجود فایل
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response(
                {'detail': 'فایل آپلود نشده است.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # کپی داده‌ها و افزودن فایل
        data = request.data.copy()
        data['file'] = uploaded_file

        # سریالایزر با داده‌ها و context
        serializer = JuridicalProfileDocumentSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            # ذخیره با تخصیص پروفایل از کاربر احرازشده
            serializer.save(profile=profile)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# 🧾 جزئیات، ویرایش و حذف
class JuridicalProfileDocumentRetrieveUpdateDestroyAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="ویرایش مدرک پروفایل حقوقی",
        tags=["JuridicalProfile-Document"],
        request_body=JuridicalProfileDocumentSerializer,
        responses={200: JuridicalProfileDocumentSerializer()}
    )
    def put(self, request, pk):
        document = get_object_or_404(JuridicalProfileDocument, pk=pk)
        serializer = JuridicalProfileDocumentSerializer(document, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    @swagger_auto_schema(
        operation_summary="حذف مدرک پروفایل حقوقی",
        tags=["JuridicalProfile-Document"],
        responses={204: 'مدرک حذف شد'}
    )
    def delete(self, request, pk):
        document = get_object_or_404(JuridicalProfileDocument, pk=pk)
        document.delete()
        return Response(status=204)