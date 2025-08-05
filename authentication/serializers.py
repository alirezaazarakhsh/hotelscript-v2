from config.models import UserLevel
from finance.models import BankCard
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, PasswordField
from django.contrib.auth import authenticate
from rest_framework import exceptions, serializers
from rest_framework_simplejwt.settings import api_settings
from django.contrib.auth.models import update_last_login
from django.utils.translation import gettext_lazy as _

from django.contrib.contenttypes.models import ContentType
from django.core.validators import MinLengthValidator, MaxLengthValidator  
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
class BankCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankCard
        fields = ['card_number', 'sheba_number']
        extra_kwargs = {
            'card_number': {'required': True, 'validators': [MinLengthValidator(16), MaxLengthValidator(16)]},
            'sheba_number': {'required': True, 'validators': [MinLengthValidator(24), MaxLengthValidator(24)]},
        }

class NaturalProfileSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=False, allow_null=True)
    image_url = serializers.SerializerMethodField()
    level_name = serializers.SerializerMethodField()
    level = serializers.PrimaryKeyRelatedField(
        queryset=UserLevel.objects.all(),
        required=False,
        allow_null=True,
    )
    bank_cards = serializers.SerializerMethodField()  # فیلد جدید برای کارت‌های بانکی

    class Meta:
        model = NaturalProfile
        fields = [
            'first_name',
            'last_name',
            'email',
            'national_code',
            'image',
            'image_url',
            'postal_code',
            'address',
            'level',
            'level_name',
            'bank_cards',  # اضافه کردن فیلد کارت‌های بانکی
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

    def get_bank_cards(self, obj):
        # دریافت ContentType برای NaturalProfile
        content_type = ContentType.objects.get_for_model(NaturalProfile)
        # فیلتر کردن کارت‌های بانکی مرتبط با پروفایل حقیقی
        bank_cards = BankCard.objects.filter(
            profile_content_type=content_type,
            profile_object_id=obj.id
        )[:2]  # محدودیت به حداکثر دو کارت
        return BankCardSerializer(bank_cards, many=True).data

    def validate(self, data):
        # بررسی محدودیت تعداد کارت‌های بانکی هنگام به‌روزرسانی
        if self.instance:
            content_type = ContentType.objects.get_for_model(NaturalProfile)
            bank_cards_count = BankCard.objects.filter(
                profile_content_type=content_type,
                profile_object_id=self.instance.id
            ).count()
            # اگر داده‌های کارت‌های بانکی در درخواست وجود داشته باشد
            bank_cards_data = self.context['request'].data.get('bank_cards')
            if bank_cards_data:
                try:
                    import json
                    bank_cards = json.loads(bank_cards_data)
                    if len(bank_cards) + bank_cards_count > 2:
                        raise serializers.ValidationError(
                            {"bank_cards": "هر پروفایل حقیقی حداکثر می‌تواند دو کارت بانکی داشته باشد."}
                        )
                except (ValueError, TypeError):
                    raise serializers.ValidationError(
                        {"bank_cards": "فرمت کارت‌های بانکی نامعتبر است."}
                    )
        return data

    def create(self, validated_data):
        # ایجاد پروفایل حقیقی
        profile = NaturalProfile.objects.create(
            base_user=self.context['request'].user,
            **validated_data
        )
        # افزودن کارت‌های بانکی در صورت وجود
        bank_cards_data = self.context['request'].data.get('bank_cards')
        if bank_cards_data:
            try:
                import json
                bank_cards = json.loads(bank_cards_data)[:2]  # حداکثر دو کارت
                content_type = ContentType.objects.get_for_model(NaturalProfile)
                for card_data in bank_cards:
                    BankCard.objects.create(
                        profile_content_type=content_type,
                        profile_object_id=profile.id,
                        card_number=card_data['card_number'],
                        sheba_number=card_data['sheba_number']
                    )
            except (ValueError, KeyError):
                raise serializers.ValidationError(
                    {"bank_cards": "فرمت کارت‌های بانکی نامعتبر است."}
                )
        return profile

    def update(self, instance, validated_data):
        # به‌روزرسانی فیلدهای پروفایل
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # مدیریت کارت‌های بانکی
        bank_cards_data = self.context['request'].data.get('bank_cards')
        if bank_cards_data:
            try:
                import json
                bank_cards = json.loads(bank_cards_data)[:2]  # حداکثر دو کارت
                content_type = ContentType.objects.get_for_model(NaturalProfile)
                # حذف کارت‌های قبلی
                BankCard.objects.filter(
                    profile_content_type=content_type,
                    profile_object_id=instance.id
                ).delete()
                # افزودن کارت‌های جدید
                for card_data in bank_cards:
                    BankCard.objects.create(
                        profile_content_type=content_type,
                        profile_object_id=instance.id,
                        card_number=card_data['card_number'],
                        sheba_number=card_data['sheba_number']
                    )
            except (ValueError, KeyError):
                raise serializers.ValidationError(
                    {"bank_cards": "فرمت کارت‌های بانکی نامعتبر است."}
                )

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