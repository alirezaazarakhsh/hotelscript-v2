from config.models import UserLevel
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, PasswordField
from django.contrib.auth import authenticate
from rest_framework import exceptions, serializers
from rest_framework_simplejwt.settings import api_settings
from django.contrib.auth.models import update_last_login
from django.utils.translation import gettext_lazy as _

from safarname24.serializers import ErrorMessageSerializerMixin
from django.core.validators import RegexValidator

from .validators import validate_phone_number
from .models import BaseUser, CardNumber, JuridicalCardNumber, NaturalProfile, JuridicalProfile, JuridicalProfileDocument


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
validate_national_code = RegexValidator(
    regex=r'^\d{10}$',
    message=_('کد ملی باید دقیقاً ۱۰ رقم باشد.')
)

# اعتبارسنجی برای کد پستی
validate_postal_code = RegexValidator(
    regex=r'^\d{10}$',
    message=_('کد پستی باید دقیقاً ۱۰ رقم باشد.')
)

class CardNumberSerializer(serializers.ModelSerializer):
    class Meta:
        model = CardNumber
        fields = ['id', 'card_number', 'iban']
        extra_kwargs = {
            'card_number': {'validators': [RegexValidator(regex=r'^\d{16}$', message=_('شماره کارت باید دقیقاً ۱۶ رقم باشد.'))]},
            'iban': {'validators': [RegexValidator(regex=r'^\d{24}$', message=_('شماره شبا باید دقیقاً ۲۴ رقم باشد.'))], 'required': False, 'allow_null': True},
        }

class NaturalProfileSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=False, allow_null=True)
    level_name = serializers.SerializerMethodField()
    level = serializers.PrimaryKeyRelatedField(
        queryset=UserLevel.objects.all(),
        required=False,
        allow_null=True,
    )
    card_numbers = CardNumberSerializer(many=True, required=False)

    class Meta:
        model = NaturalProfile
        fields = [
            'first_name',
            'last_name',
            'email',
            'national_code',
            'image',
            'postal_code',
            'address',
            'level',
            'level_name',
            'card_numbers',
        ]
        extra_kwargs = {
            'email': {'required': False, 'allow_null': True},
            'national_code': {'required': False, 'allow_null': True, 'validators': [validate_national_code]},
            'postal_code': {'required': False, 'allow_null': True, 'validators': [validate_postal_code]},
            'address': {'required': False, 'allow_null': True},
            'level': {'required': False, 'allow_null': True},
        }

    def get_level_name(self, obj):
        return obj.level.title if obj.level else None

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['image'] = self.get_image(instance)
        return representation

    def validate(self, data):
        """
        اعتبارسنجی کلی داده‌ها برای اطمینان از سازگاری
        """
        if 'card_numbers' in data and data.get('card_numbers'):
            card_numbers = data['card_numbers']
            if len(card_numbers) > 2:
                raise serializers.ValidationError({'card_numbers': _('هر کاربر تنها می‌تواند حداکثر ۲ شماره کارت ثبت کند.')})
            
            for card in card_numbers:
                if 'card_number' not in card or not card['card_number']:
                    raise serializers.ValidationError({'card_numbers': _('شماره کارت الزامی است.')})
                if 'iban' in card and card['iban'] and not isinstance(card['iban'], (type(None), str)) or len(str(card['iban'])) != 24:
                    raise serializers.ValidationError({'card_numbers': _('شماره شبا باید ۲۴ رقم باشد یا خالی باشد.')})
                if 'id' in card and card['id']:
                    try:
                        CardNumber.objects.get(id=card['id'], profile__base_user=self.context['request'].user)
                    except CardNumber.DoesNotExist:
                        raise serializers.ValidationError({'card_numbers': _('شماره کارت با این id یافت نشد.')})
        return data

    def create(self, validated_data):
        card_numbers_data = validated_data.pop('card_numbers', [])
        profile = NaturalProfile.objects.create(base_user=self.context['request'].user, **validated_data)
        for card_data in card_numbers_data:
            CardNumber.objects.create(profile=profile, **card_data)
        return profile

    def update(self, instance, validated_data):
        card_numbers_data = validated_data.pop('card_numbers', None)
        
        # به‌روزرسانی سایر فیلدهای پروفایل
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if card_numbers_data is not None:
            # نگه‌داری لیستی از idهای شماره‌های کارت ارسالی
            card_number_ids = [card_data.get('id') for card_data in card_numbers_data if card_data.get('id')]
            
            # حذف شماره‌های کارتی که در ورودی جدید نیستند
            instance.card_numbers.exclude(id__in=card_number_ids).delete()

            # به‌روزرسانی یا ایجاد شماره‌های کارت
            for card_data in card_numbers_data:
                card_id = card_data.get('id')
                if card_id:
                    # اگر id وجود دارد، شماره کارت را به‌روزرسانی کنید
                    try:
                        card = instance.card_numbers.get(id=card_id)
                        card.card_number = card_data.get('card_number', card.card_number)
                        card.iban = card_data.get('iban', card.iban)
                        card.save()
                    except CardNumber.DoesNotExist:
                        # اگر id وجود نداشته باشد، شماره کارت جدید ایجاد کنید
                        CardNumber.objects.create(profile=instance, **card_data)
                else:
                    # اگر id وجود ندارد، شماره کارت جدید ایجاد کنید
                    CardNumber.objects.create(profile=instance, **card_data)
        
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



class JuridicalCardNumberSerializer(serializers.ModelSerializer):
    class Meta:
        model = JuridicalCardNumber
        fields = ['id', 'card_number', 'iban']
        extra_kwargs = {
            'card_number': {'validators': [RegexValidator(regex=r'^\d{16}$', message=_('شماره کارت باید دقیقاً ۱۶ رقم باشد.'))]},
            'iban': {'validators': [RegexValidator(regex=r'^\d{24}$', message=_('شماره شبا باید دقیقاً ۲۴ رقم باشد.'))], 'required': False, 'allow_null': True},
        }


# -----------------------------
# JuridicalProfile Serializer
# -----------------------------
class JuridicalProfileSerializer(serializers.ModelSerializer):
    documents = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    card_numbers = JuridicalCardNumberSerializer(many=True, required=False)  # اضافه کردن فیلد شماره کارت‌ها

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
            'card_numbers',  # اضافه کردن card_numbers به fields
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
        # اعتبارسنجی برای وضعیت رد شده
        if data.get('status') == 'rejected' and not data.get('reject_reason', '').strip():
            raise serializers.ValidationError({
                'reject_reason': _('فیلد دلیل رد برای وضعیت رد شده الزامی است.')
            })

        # اعتبارسنجی شماره‌های کارت
        if 'card_numbers' in data and data.get('card_numbers'):
            card_numbers = data['card_numbers']
            if len(card_numbers) > 2:
                raise serializers.ValidationError({'card_numbers': _('هر پروفایل حقوقی تنها می‌تواند حداکثر ۲ شماره کارت ثبت کند.')})

            for card in card_numbers:
                if 'card_number' not in card or not card['card_number']:
                    raise serializers.ValidationError({'card_numbers': _('شماره کارت الزامی است.')})
                if 'iban' in card and card['iban'] and not isinstance(card['iban'], (type(None), str)) or len(str(card['iban'])) != 24:
                    raise serializers.ValidationError({'card_numbers': _('شماره شبا باید ۲۴ رقم باشد یا خالی باشد.')})
                if 'id' in card and card['id']:
                    try:
                        JuridicalCardNumber.objects.get(id=card['id'], profile__natural_profile__base_user=self.context['request'].user)
                    except JuridicalCardNumber.DoesNotExist:
                        raise serializers.ValidationError({'card_numbers': _('شماره کارت با این id یافت نشد.')})
        return data

    def create(self, validated_data):
        card_numbers_data = validated_data.pop('card_numbers', [])
        # ایجاد پروفایل حقوقی
        profile = JuridicalProfile.objects.create(**validated_data)
        # ایجاد شماره‌های کارت
        for card_data in card_numbers_data:
            JuridicalCardNumber.objects.create(profile=profile, **card_data)
        return profile

    def update(self, instance, validated_data):
        card_numbers_data = validated_data.pop('card_numbers', None)

        # به‌روزرسانی سایر فیلدهای پروفایل
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if card_numbers_data is not None:
            # نگه‌داری لیستی از idهای شماره‌های کارت ارسالی
            card_number_ids = [card_data.get('id') for card_data in card_numbers_data if card_data.get('id')]

            # حذف شماره‌های کارتی که در ورودی جدید نیستند
            instance.card_numbers.exclude(id__in=card_number_ids).delete()

            # به‌روزرسانی یا ایجاد شماره‌های کارت
            for card_data in card_numbers_data:
                card_id = card_data.get('id')
                if card_id:
                    # اگر id وجود دارد، شماره کارت را به‌روزرسانی کنید
                    try:
                        card = instance.card_numbers.get(id=card_id)
                        card.card_number = card_data.get('card_number', card.card_number)
                        card.iban = card_data.get('iban', card.iban)
                        card.save()
                    except JuridicalCardNumber.DoesNotExist:
                        # اگر id وجود نداشته باشد، شماره کارت جدید ایجاد کنید
                        JuridicalCardNumber.objects.create(profile=instance, **card_data)
                else:
                    # اگر id وجود ندارد، شماره کارت جدید ایجاد کنید
                    JuridicalCardNumber.objects.create(profile=instance, **card_data)

        return instance