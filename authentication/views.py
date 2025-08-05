import json
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.parsers import MultiPartParser, FormParser , JSONParser
from rest_framework_simplejwt.views import (
    TokenObtainPairView as JwtTokenObtainPairView,
    TokenRefreshView as JwtTokenRefreshView,
)
from rest_framework_simplejwt.exceptions import TokenError
from django.core.exceptions import ValidationError
from rest_framework import status
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .serializers import (
    AuthSerializer,
    CardNumberSerializer,
    JuridicalCardNumberSerializer,
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
        operation_description="این API پروفایل حقوقی مرتبط با کاربر جاری را بر اساس پروفایل حقیقی او دریافت می‌کند. اگر پروفایل حقیقی یا حقوقی وجود نداشته باشد، خطای 404 برگردانده می‌شود.",
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
                status=status.HTTP_404_NOT_FOUND
            )
        except JuridicalProfile.DoesNotExist:
            return Response(
                {"detail": "پروفایل حقوقی برای این کاربر یافت نشد."},
                status=status.HTTP_404_NOT_FOUND
            )

    @swagger_auto_schema(
        operation_summary="ایجاد پروفایل حقوقی",
        operation_description="این API یک پروفایل حقوقی جدید برای کاربر جاری ایجاد می‌کند، به شرطی که کاربر از قبل پروفایل حقوقی نداشته باشد و پروفایل حقیقی وجود داشته باشد. شماره‌های کارت بانکی تا حداکثر ۲ عدد قابل ثبت هستند.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'organization_name': openapi.Schema(type=openapi.TYPE_STRING, description='نام شرکت'),
                'national_id': openapi.Schema(type=openapi.TYPE_STRING, description='شناسه ملی'),
                'registeration_number': openapi.Schema(type=openapi.TYPE_STRING, description='شماره ثبت'),
                'economical_code': openapi.Schema(type=openapi.TYPE_STRING, description='کد اقتصادی'),
                'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description='شماره تماس'),
                'postal_code': openapi.Schema(type=openapi.TYPE_STRING, description='کد پستی'),
                'address': openapi.Schema(type=openapi.TYPE_STRING, description='آدرس', nullable=True),
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='ایمیل', nullable=True),
                'image': openapi.Schema(type=openapi.TYPE_FILE, description='فایل عکس شرکت', nullable=True),
                'status': openapi.Schema(type=openapi.TYPE_STRING, description='وضعیت پروفایل'),
                'reject_reason': openapi.Schema(type=openapi.TYPE_STRING, description='دلیل رد', nullable=True),
                'bank_cards': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    description='لیست کارت‌های بانکی',
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'card_number': openapi.Schema(type=openapi.TYPE_STRING, description='شماره کارت (۱۶ رقم)'),
                            'iban': openapi.Schema(type=openapi.TYPE_STRING, description='شماره شبا (۲۴ رقم)', nullable=True),
                        },
                        required=['card_number']
                    ),
                    nullable=True
                ),
            },
            required=['organization_name', 'national_id', 'registeration_number', 'economical_code', 'phone_number', 'postal_code']
        ),
        responses={
            201: JuridicalProfileSerializer(),
            400: "داده‌های نامعتبر یا پروفایل موجود"
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
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # جدا کردن داده‌های bank_cards از request.data
            data = request.data.copy()
            bank_cards_data = data.pop('bank_cards', None)

            serializer = JuridicalProfileSerializer(
                data=data,
                context={'request': request}
            )
            
            if serializer.is_valid():
                # پروفایل حقوقی را ذخیره می‌کنیم
                profile = serializer.save(natural_profile=natural_profile)

                # مدیریت شماره‌های کارت
                if bank_cards_data:
                    try:
                        bank_cards = bank_cards_data if isinstance(bank_cards_data, list) else json.loads(bank_cards_data)
                        if len(bank_cards) > 2:
                            profile.delete()  # حذف پروفایل در صورت خطا
                            return Response(
                                {"detail": "حداکثر ۲ شماره کارت مجاز است."},
                                status=status.HTTP_400_BAD_REQUEST
                            )

                        # ایجاد شماره‌های کارت
                        for card_data in bank_cards:
                            serializer = JuridicalCardNumberSerializer(data=card_data, context={'request': request})
                            if serializer.is_valid():
                                serializer.save(profile=profile)
                            else:
                                profile.delete()  # حذف پروفایل در صورت خطا
                                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                    except (json.JSONDecodeError, TypeError):
                        profile.delete()  # حذف پروفایل در صورت خطا
                        return Response(
                            {"detail": "فرمت JSON برای bank_cards نامعتبر است."},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    except ValidationError as e:
                        profile.delete()  # حذف پروفایل در صورت خطا
                        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

                return Response(
                    JuridicalProfileSerializer(profile, context={'request': request}).data,
                    status=status.HTTP_201_CREATED
                )
                
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except NaturalProfile.DoesNotExist:
            return Response(
                {"detail": "برای ایجاد پروفایل حقوقی، ابتدا باید پروفایل حقیقی ایجاد کنید."},
                status=status.HTTP_400_BAD_REQUEST
            )




class JuridicalProfileDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @swagger_auto_schema(
        operation_summary="دریافت پروفایل حقوقی کاربر جاری",
        operation_description=(
            "این API اطلاعات پروفایل حقوقی کاربر جاری را برمی‌گرداند. "
            "اگر پروفایل وجود نداشته باشد، خطای 404 بازگردانده می‌شود."
        ),
        responses={200: JuridicalProfileSerializer(), 404: 'پروفایل یافت نشد'}
    )
    def get(self, request):
        natural_profile = get_object_or_404(NaturalProfile, base_user=request.user)
        profile = get_object_or_404(JuridicalProfile, natural_profile=natural_profile)
        serializer = JuridicalProfileSerializer(profile, context={'request': request})
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="ویرایش پروفایل حقوقی کاربر جاری",
        operation_description=(
            "این API به کاربر اجازه می‌دهد اطلاعات پروفایل حقوقی خود را ویرایش کند. "
            "شماره‌های کارت بانکی می‌توانند حداکثر ۲ عدد باشند. کارت‌های حذف‌شده نیز پاک می‌شوند."
        ),
        manual_parameters=[
            openapi.Parameter('image', openapi.IN_FORM, description="فایل عکس شرکت", type=openapi.TYPE_FILE, required=False),
            openapi.Parameter('organization_name', openapi.IN_FORM, description="نام شرکت", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('national_id', openapi.IN_FORM, description="شناسه ملی", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('registeration_number', openapi.IN_FORM, description="شماره ثبت", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('economical_code', openapi.IN_FORM, description="کد اقتصادی", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('phone_number', openapi.IN_FORM, description="شماره تماس", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('postal_code', openapi.IN_FORM, description="کد پستی", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('address', openapi.IN_FORM, description="آدرس", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('email', openapi.IN_FORM, description="ایمیل", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('status', openapi.IN_FORM, description="وضعیت", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('reject_reason', openapi.IN_FORM, description="دلیل رد", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('bank_cards', openapi.IN_FORM, description="لیست کارت‌ها (JSON string یا آرایه)", type=openapi.TYPE_STRING, required=False),
        ],
        responses={
            200: JuridicalProfileSerializer(),
            400: "داده‌های نامعتبر",
            404: "پروفایل یافت نشد"
        },
        consumes=['multipart/form-data', 'application/json']
    )
    def put(self, request):
        natural_profile = get_object_or_404(NaturalProfile, base_user=request.user)
        profile = get_object_or_404(JuridicalProfile, natural_profile=natural_profile)

        data = request.data.copy()
        bank_cards_data = data.pop('bank_cards', None)

        serializer = JuridicalProfileSerializer(profile, data=data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()

            if bank_cards_data:
                try:
                    if isinstance(bank_cards_data, str):
                        bank_cards = json.loads(bank_cards_data)
                    else:
                        bank_cards = bank_cards_data

                    if not isinstance(bank_cards, list):
                        return Response({"detail": "bank_cards باید یک لیست باشد."}, status=status.HTTP_400_BAD_REQUEST)

                    if len(bank_cards) > 2:
                        return Response({"detail": "حداکثر ۲ کارت بانکی مجاز است."}, status=status.HTTP_400_BAD_REQUEST)

                    existing_cards = {card.card_number: card for card in profile.card_numbers.all()}
                    submitted_card_numbers = set()

                    for card_data in bank_cards:
                        card_number = card_data.get("card_number")
                        if not card_number:
                            return Response({"detail": "شماره کارت الزامی است."}, status=status.HTTP_400_BAD_REQUEST)
                        submitted_card_numbers.add(card_number)

                        if card_number in existing_cards:
                            card = existing_cards[card_number]
                            card_serializer = JuridicalCardNumberSerializer(card, data=card_data, partial=True, context={'request': request})
                            if card_serializer.is_valid():
                                card_serializer.save()
                            else:
                                return Response(card_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                        else:
                            card_serializer = JuridicalCardNumberSerializer(data=card_data, context={'request': request})
                            if card_serializer.is_valid():
                                card_serializer.save(profile=profile)
                            else:
                                return Response(card_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

                    for card_number, card_obj in existing_cards.items():
                        if card_number not in submitted_card_numbers:
                            card_obj.delete()

                except (json.JSONDecodeError, TypeError, ValueError) as e:
                    return Response({"detail": f"فرمت bank_cards نامعتبر است: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
                except ValidationError as e:
                    return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

            return Response(JuridicalProfileSerializer(profile, context={'request': request}).data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_summary="حذف پروفایل حقوقی کاربر جاری",
        operation_description="این API پروفایل حقوقی کاربر جاری را حذف می‌کند. اگر پروفایل وجود نداشته باشد، خطای 404 بازگردانده می‌شود.",
        responses={204: "پروفایل حذف شد", 404: "پروفایل یافت نشد"}
    )
    def delete(self, request):
        natural_profile = get_object_or_404(NaturalProfile, base_user=request.user)
        profile = get_object_or_404(JuridicalProfile, natural_profile=natural_profile)
        profile.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
        



class NaturalProfileListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="دریافت پروفایل حقیقی کاربر جاری",
        operation_description="این API اطلاعات پروفایل حقیقی کاربر جاری را برمی‌گرداند. اگر پروفایل وجود نداشته باشد، یک شیء فیک بدون ذخیره‌سازی در دیتابیس ایجاد می‌شود.",
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
        operation_description="این API یک پروفایل حقیقی جدید برای کاربر جاری ایجاد می‌کند، به شرطی که کاربر از قبل پروفایل حقیقی نداشته باشد. شماره‌های کارت بانکی تا حداکثر ۲ عدد قابل ثبت هستند.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'first_name': openapi.Schema(type=openapi.TYPE_STRING, description='نام', nullable=True),
                'last_name': openapi.Schema(type=openapi.TYPE_STRING, description='نام خانوادگی', nullable=True),
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='ایمیل', nullable=True),
                'national_code': openapi.Schema(type=openapi.TYPE_STRING, description='کدملی', nullable=True),
                'image': openapi.Schema(type=openapi.TYPE_FILE, description='فایل عکس پروفایل', nullable=True),
                'postal_code': openapi.Schema(type=openapi.TYPE_STRING, description='کدپستی', nullable=True),
                'address': openapi.Schema(type=openapi.TYPE_STRING, description='آدرس', nullable=True),
                'level': openapi.Schema(type=openapi.TYPE_INTEGER, description='شناسه سطح کاربری', nullable=True),
                'bank_cards': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    description='لیست کارت‌های بانکی',
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'card_number': openapi.Schema(type=openapi.TYPE_STRING, description='شماره کارت (۱۶ رقم)'),
                            'iban': openapi.Schema(type=openapi.TYPE_STRING, description='شماره شبا (۲۴ رقم)', nullable=True),
                        },
                        required=['card_number']
                    ),
                    nullable=True
                ),
            }
        ),
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

        # جدا کردن داده‌های bank_cards از request.data
        data = request.data.copy()
        bank_cards_data = data.pop('bank_cards', None)

        # اعتبارسنجی و ایجاد پروفایل
        serializer = NaturalProfileSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            profile = serializer.save(base_user=user)

            # مدیریت شماره‌های کارت
            if bank_cards_data:
                try:
                    bank_cards = bank_cards_data if isinstance(bank_cards_data, list) else json.loads(bank_cards_data)
                    if len(bank_cards) > 2:
                        profile.delete()  # حذف پروفایل در صورت خطا
                        return Response(
                            {"detail": "حداکثر ۲ شماره کارت مجاز است."},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                    # ایجاد شماره‌های کارت
                    for card_data in bank_cards:
                        serializer = CardNumberSerializer(data=card_data, context={'request': request})
                        if serializer.is_valid():
                            serializer.save(profile=profile)
                        else:
                            profile.delete()  # حذف پروفایل در صورت خطا
                            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                except (json.JSONDecodeError, TypeError):
                    profile.delete()  # حذف پروفایل در صورت خطا
                    return Response(
                        {"detail": "فرمت JSON برای bank_cards نامعتبر است."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                except ValidationError as e:
                    profile.delete()  # حذف پروفایل در صورت خطا
                    return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

            return Response(
                NaturalProfileSerializer(profile, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)






class NaturalProfileDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @swagger_auto_schema(
        operation_summary="دریافت پروفایل حقیقی کاربر جاری",
        operation_description=(
            "این API اطلاعات پروفایل حقیقی کاربر جاری را برمی‌گرداند. "
            "اگر پروفایل وجود نداشته باشد، خطای 404 بازگردانده می‌شود."
        ),
        responses={200: NaturalProfileSerializer(), 404: 'پروفایل یافت نشد'}
    )
    def get(self, request):
        profile = get_object_or_404(NaturalProfile, base_user=request.user)
        serializer = NaturalProfileSerializer(profile, context={'request': request})
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="ویرایش پروفایل حقیقی کاربر جاری",
        operation_description=(
            "این API به کاربر اجازه می‌دهد اطلاعات پروفایل حقیقی خود را به‌صورت جزئی یا کامل ویرایش کند. "
            "شماره‌های کارت بانکی می‌توانند به‌صورت انتخابی به‌روزرسانی شوند، با محدودیت حداکثر ۲ کارت. "
            "کارت‌هایی که حذف شوند، از پایگاه داده پاک می‌شوند."
        ),
        manual_parameters=[
            openapi.Parameter('image', openapi.IN_FORM, description="فایل عکس پروفایل", type=openapi.TYPE_FILE, required=False),
            openapi.Parameter('first_name', openapi.IN_FORM, description="نام", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('last_name', openapi.IN_FORM, description="نام خانوادگی", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('email', openapi.IN_FORM, description="ایمیل", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('national_code', openapi.IN_FORM, description="کدملی", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('postal_code', openapi.IN_FORM, description="کدپستی", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('address', openapi.IN_FORM, description="آدرس", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('level', openapi.IN_FORM, description="شناسه سطح کاربری", type=openapi.TYPE_INTEGER, required=False),
            openapi.Parameter('bank_cards', openapi.IN_FORM, description="لیست کارت‌ها (JSON string یا آرایه)", type=openapi.TYPE_STRING, required=False),
        ],
        responses={
            200: NaturalProfileSerializer(),
            400: 'خطا در داده‌های ارسالی',
            404: 'پروفایل یافت نشد'
        },
        consumes=['multipart/form-data', 'application/json']
    )
    def put(self, request):
        profile, created = NaturalProfile.objects.get_or_create(base_user=request.user)

        bank_cards_raw = request.data.get('bank_cards')
        if bank_cards_raw:
            try:
                if isinstance(bank_cards_raw, str):
                    bank_cards = json.loads(bank_cards_raw)
                else:
                    bank_cards = bank_cards_raw

                if not isinstance(bank_cards, list):
                    return Response({"detail": "bank_cards باید یک لیست باشد."}, status=status.HTTP_400_BAD_REQUEST)

                if len(bank_cards) > 2:
                    return Response({"detail": "حداکثر ۲ شماره کارت مجاز است."}, status=status.HTTP_400_BAD_REQUEST)

                existing_cards = {card.card_number: card for card in profile.card_numbers.all()}
                submitted_card_numbers = set()

                for card_data in bank_cards:
                    card_number = card_data.get('card_number')
                    if not card_number:
                        return Response({"detail": "شماره کارت الزامی است."}, status=status.HTTP_400_BAD_REQUEST)
                    submitted_card_numbers.add(card_number)

                    if card_number in existing_cards:
                        card = existing_cards[card_number]
                        card_serializer = CardNumberSerializer(card, data=card_data, partial=True, context={'request': request})
                        if card_serializer.is_valid():
                            card_serializer.save()
                        else:
                            return Response(card_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                    else:
                        card_serializer = CardNumberSerializer(data=card_data, context={'request': request})
                        if card_serializer.is_valid():
                            card_serializer.save(profile=profile)
                        else:
                            return Response(card_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

                # حذف کارت‌هایی که حذف شدند
                for card_number, card_obj in existing_cards.items():
                    if card_number not in submitted_card_numbers:
                        card_obj.delete()

            except (json.JSONDecodeError, TypeError, ValueError) as e:
                return Response({"detail": f"فرمت bank_cards نامعتبر است: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
            except ValidationError as e:
                return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = NaturalProfileSerializer(profile, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_summary="حذف پروفایل حقیقی کاربر جاری",
        operation_description="این API پروفایل حقیقی کاربر جاری را حذف می‌کند. اگر پروفایل وجود نداشته باشد، خطای 404 بازگردانده می‌شود.",
        responses={204: "پروفایل حذف شد", 404: "پروفایل یافت نشد"}
    )
    def delete(self, request):
        profile = get_object_or_404(NaturalProfile, base_user=request.user)
        profile.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    



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