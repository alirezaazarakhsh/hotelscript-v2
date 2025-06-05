from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, PasswordField
from django.contrib.auth import authenticate
from rest_framework import exceptions, serializers
from rest_framework_simplejwt.settings import api_settings
from django.contrib.auth.models import update_last_login
from django.utils.translation import gettext_lazy as _

from safarname24.serializers import ErrorMessageSerializerMixin

from .validators import validate_phone_number
from .models import BaseUser, NaturalProfile, JuridicalProfile, JuridicalProfileDocument


# -----------------------------
# Custom Token Serializer
# -----------------------------
class UserTokenObtainPairSerializer(TokenObtainPairSerializer, ErrorMessageSerializerMixin):
    username_field = "phone"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # تغییر رمز به OTP
        self.password_field = "otp"
        self.fields[self.password_field] = PasswordField()
        del self.fields["password"]

        self.fields[self.username_field].label = _('phone')
        self.fields[self.password_field].label = _('otp')

        ErrorMessageSerializerMixin.__init__(self, *args, **kwargs)

    def validate(self, attrs):
        authenticate_kwargs = {
            self.username_field: attrs[self.username_field],
            self.password_field: attrs[self.password_field],
        }

        if "request" in self.context:
            authenticate_kwargs["request"] = self.context["request"]

        # احراز هویت با OTP
        self.user = authenticate(**authenticate_kwargs)

        if not api_settings.USER_AUTHENTICATION_RULE(self.user):
            raise exceptions.AuthenticationFailed(
                _("validation code is not correct"),
                "no_active_account",
            )

        refresh = self.get_token(self.user)

        data = {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }

        # ثبت آخرین ورود
        if api_settings.UPDATE_LAST_LOGIN:
            update_last_login(None, self.user)

        # گرفتن پروفایل طبیعی کاربر برای نام و نام خانوادگی
        try:
            natural_profile = NaturalProfile.objects.get(base_user=self.user)
            first_name = natural_profile.first_name
            last_name = natural_profile.last_name
        except NaturalProfile.DoesNotExist:
            first_name = ""
            last_name = ""

        # افزودن اطلاعات کاربر به پاسخ
        data["user_id"] = self.user.id
        data["phone_number"] = self.user.phone_number
        data["first_name"] = first_name
        data["last_name"] = last_name

        return data

# -----------------------------
# Authentication Request Serializer
# -----------------------------
class AuthSerializer(serializers.Serializer):
    phone = serializers.CharField(
        required=True,
        validators=[validate_phone_number],
    )


# -----------------------------
# Natural User Profile Serializer
# -----------------------------
class UserProfileSerializer(serializers.ModelSerializer):
    base_user = serializers.PrimaryKeyRelatedField(
        queryset=BaseUser.objects.all(),
        write_only=True,
    )
    phone_number = serializers.CharField(
        source='base_user.phone_number',
        read_only=True,
    )
    wallet_balance = serializers.DecimalField(
        source='base_user.wallet.balance',
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = NaturalProfile
        fields = [
            'base_user',
            'phone_number',
            'first_name',
            'last_name',
            'email',
            'national_code',
            'image',
            'postal_code',
            'address',
            'wallet_balance',
        ]
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'national_code': {'required': True},
        }


# -----------------------------
# Juridical Profile Serializer
# -----------------------------
class JuridicalProfileSerializer(serializers.ModelSerializer):
    natural_profile = serializers.PrimaryKeyRelatedField(
        queryset=NaturalProfile.objects.all(),
        write_only=True,
    )

    class Meta:
        model = JuridicalProfile
        fields = [
            'natural_profile',
            'organization_name',
            'national_id',
            'registeration_number',
            'economical_code',
            'phone_number',
            'postal_code',
            'address',
            'email',
            'image',
            'status',
            'reject_reason',
        ]
        extra_kwargs = {
            'organization_name': {'required': True},
            'national_id': {'required': True},
            'registeration_number': {'required': True},
            'economical_code': {'required': True},
            'phone_number': {'required': True},
            'postal_code': {'required': True},
            'reject_reason': {'read_only': True},
        }


# -----------------------------
# Juridical Profile Document Serializer
# -----------------------------
class JuridicalProfileDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = JuridicalProfileDocument
        fields = ['profile', 'file']
        extra_kwargs = {
            'profile': {'write_only': True},
        }
