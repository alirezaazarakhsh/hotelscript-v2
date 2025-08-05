from config.models import UserLevel
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
# Custom Token Serializer (Using phone and OTP)
# -----------------------------
class UserTokenObtainPairSerializer(TokenObtainPairSerializer, ErrorMessageSerializerMixin):
    username_field = "phone"  # فیلدی که به جای username استفاده می‌شود
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # تغییر رمز به OTP
        self.password_field = "otp"
        self.fields[self.password_field] = PasswordField(write_only=True)
        if "password" in self.fields:
            del self.fields["password"]

        self.fields[self.username_field].label = _('phone')
        self.fields[self.password_field].label = _('otp')

        ErrorMessageSerializerMixin.__init__(self, *args, **kwargs)

    def validate(self, attrs):
        authenticate_kwargs = {
            self.username_field: attrs.get(self.username_field),
            self.password_field: attrs.get(self.password_field),
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
        data["phone_number"] = getattr(self.user, "phone_number", "")
        data["first_name"] = first_name
        data["last_name"] = last_name

        return data


# -----------------------------
# Authentication Request Serializer (برای درخواست ارسال OTP)
# -----------------------------
class AuthSerializer(serializers.Serializer):
    phone = serializers.CharField(
        required=True,
        validators=[validate_phone_number],
        max_length=15,
    )


# -----------------------------
# NaturalProfile Serializer
# -----------------------------
from rest_framework import serializers
from .models import NaturalProfile, UserLevel

class NaturalProfileSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=False, allow_null=True)  # برای آپلود و ویرایش عکس
    image_url = serializers.SerializerMethodField()  # برای نمایش URL عکس
    level_name = serializers.SerializerMethodField()
    level = serializers.PrimaryKeyRelatedField(
        queryset=UserLevel.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = NaturalProfile
        fields = [
            'first_name',
            'last_name',
            'email',
            'national_code',
            'image',
            'image_url',  # فیلد جدید برای URL
            'postal_code',
            'address',
            'level',
            'level_name',
        ]
        extra_kwargs = {
            'email': {'required': False, 'allow_null': True},
            'national_code': {'required': False, 'allow_null': True},
            'postal_code': {'required': False, 'allow_null': True},
            'address': {'required': False, 'allow_null': True},
            'level': {'required': False, 'allow_null': True},
        }

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None

    def get_level_name(self, obj):
        try:
            return obj.level.title if obj.level else None
        except Exception:
            return None

    def create(self, validated_data):
        return NaturalProfile.objects.create(user=self.context['request'].user, **validated_data)

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


# -----------------------------
# JuridicalProfileDocument Serializer
# -----------------------------
class JuridicalProfileDocumentSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField()
    file = serializers.FileField(write_only=True)
    file_url = serializers.SerializerMethodField(read_only=True)
    profile = serializers.PrimaryKeyRelatedField(
        read_only=True,
        label='پروفایل حقوقی'
    )

    class Meta:
        model = JuridicalProfileDocument
        fields = ['id', 'file', 'file_url', 'profile']
        read_only_fields = ['id', 'profile', 'file_url']

    def get_file_url(self, obj):
        if not obj.file:
            return None

        try:
            url = obj.file.url
        except ValueError:
            return None

        request = self.context.get('request')
        if request is not None:
            return request.build_absolute_uri(url)
        return url

    def validate(self, data):
        # Reject 'id' and 'profile' if included in the input data
        if 'id' in data:
            raise serializers.ValidationError(
                {'id': 'فیلد id نباید در بدنه درخواست ارسال شود.'}
            )
        if 'profile' in data:
            raise serializers.ValidationError(
                {'profile': 'فیلد profile نباید در بدنه درخواست ارسال شود.'}
            )
        return data



# -----------------------------
# JuridicalProfile Serializer
# -----------------------------
class JuridicalProfileSerializer(serializers.ModelSerializer):
    documents = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = JuridicalProfile
        fields = [
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
            'documents',
        ]
        extra_kwargs = {
            'address': {'required': False, 'allow_null': True},
            'email': {'required': False, 'allow_null': True},
            'reject_reason': {'required': False, 'allow_blank': True},
        }

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None

    def get_documents(self, obj):
        request = self.context.get('request')
        documents = obj.documents.all()
        return JuridicalProfileDocumentSerializer(documents, many=True, context={'request': request}).data

    def validate(self, data):
        if data.get('status') == 'rejected' and not data.get('reject_reason', '').strip():
            raise serializers.ValidationError({
                'reject_reason': _('فیلد دلیل رد برای وضعیت رد شده الزامی است.')
            })
        return data

    def create(self, validated_data):
        return JuridicalProfile.objects.create(user=self.context['request'].user, **validated_data)

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance