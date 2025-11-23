from config.models import UserLevel
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, PasswordField
from rest_framework import exceptions, serializers
from rest_framework_simplejwt.settings import api_settings
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import update_last_login
from django.core.validators import RegexValidator
from django.db import IntegrityError
from rest_framework_simplejwt.tokens import RefreshToken

from safarname24.serializers import ErrorMessageSerializerMixin
from .validators import validate_phone_number
from .models import BaseUser, CardNumber, JuridicalCardNumber, NaturalProfile, JuridicalProfile, JuridicalProfileDocument

# -----------------------------
# Custom Token Serializer (Using phone and OTP)
# -----------------------------
class UserTokenObtainPairSerializer(TokenObtainPairSerializer, ErrorMessageSerializerMixin):
    username_field = "phone"  # فیلدی که به جای username استفاده می‌شود
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
        if api_settings.UPDATE_LAST_LOGIN:
            update_last_login(None, self.user)
        return data

# -----------------------------
# Authentication Request Serializer
# -----------------------------
class AuthSerializer(serializers.Serializer):
    phone = serializers.CharField(
        required=True,
        validators=[validate_phone_number],
        max_length=15,
    )


# -----------------------------
# Admin Panel Login Serializer (phone + panel_password)
# -----------------------------
class AdminPanelTokenObtainSerializer(serializers.Serializer):
    phone = serializers.CharField(required=True, validators=[validate_phone_number], max_length=15)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        phone = attrs.get('phone')
        password = attrs.get('password')

        try:
            user = BaseUser.objects.get(phone_number=phone)
        except BaseUser.DoesNotExist:
            raise exceptions.AuthenticationFailed(_("کاربر یافت نشد."))

        admin = getattr(user, 'admin', None)
        if not admin:
            raise exceptions.AuthenticationFailed(_("شما ادمین سایت نیستید."))

        if not admin.check_panel_password(password):
            raise exceptions.AuthenticationFailed(_("رمز عبور نادرست است."))

        # تولید JWT tokens
        refresh = RefreshToken.for_user(user)
        data = {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }

        if api_settings.UPDATE_LAST_LOGIN:
            update_last_login(None, user)

        # نگهداری کاربر برای دسترسی در View در صورت نیاز
        self.user = user
        return data

# -----------------------------
# NaturalProfile Serializer
# -----------------------------
validate_national_code = RegexValidator(
    regex=r'^\d{10}$',
    message=_('کد ملی باید دقیقاً ۱۰ رقم باشد.')
)
validate_postal_code = RegexValidator(
    regex=r'^\d{10}$',
    message=_('کد پستی باید دقیقاً ۱۰ رقم باشد.')
)

class CardNumberSerializer(serializers.ModelSerializer):
    class Meta:
        model = CardNumber
        fields = ['id', 'card_number', 'iban', 'account_holder_name']
        extra_kwargs = {
            'card_number': {'validators': [RegexValidator(regex=r'^\d{16}$', message=_('شماره کارت باید دقیقاً ۱۶ رقم باشد.'))]},
            'iban': {'validators': [RegexValidator(regex=r'^\d{24}$', message=_('شماره شبا باید دقیقاً ۲۴ رقم باشد.'))], 'required': False, 'allow_null': True},
            'account_holder_name': {'validators': [RegexValidator(regex=r'^[\u0600-\u06FF\s]+$', message=_('نام صاحب حساب فقط می‌تواند شامل حروف فارسی و فاصله باشد.'))]},
        }

class NaturalProfileSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=False, allow_null=True)
    level_name = serializers.SerializerMethodField()
    level = serializers.PrimaryKeyRelatedField(
        queryset=UserLevel.objects.all(),
        required=False,
        allow_null=True,
    )
    card_numbers = serializers.SerializerMethodField()

    def get_card_numbers(self, obj):
        card_numbers = obj.card_numbers.all()
        return CardNumberSerializer(card_numbers, many=True).data
    phone_number = serializers.SerializerMethodField()  # فیلد جدید برای شماره موبایل

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
            'phone_number',  # اضافه کردن phone_number به فیلدها
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

    def get_phone_number(self, obj):
        """
        استخراج شماره موبایل از base_user.
        """
        return obj.base_user.phone_number if obj.base_user else None

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
        if 'card_numbers' in data and data.get('card_numbers'):
            card_numbers = data['card_numbers']
            if len(card_numbers) > 2:
                raise serializers.ValidationError({'card_numbers': _('هر کاربر تنها می‌تواند حداکثر ۲ شماره کارت ثبت کند.')})
            for card in card_numbers:
                if 'card_number' not in card or not card['card_number']:
                    raise serializers.ValidationError({'card_numbers': _('شماره کارت الزامی است.')})
                if 'iban' in card and card['iban'] and not isinstance(card['iban'], (type(None), str)) or len(str(card['iban'])) != 24:
                    raise serializers.ValidationError({'card_numbers': _('شماره شبا باید ۲۴ رقم باشد یا خالی باشد.')})
                if 'account_holder_name' not in card or not card['account_holder_name']:
                    raise serializers.ValidationError({'card_numbers': _('نام صاحب حساب الزامی است.')})
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
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if card_numbers_data is not None:
            card_number_ids = [card_data.get('id') for card_data in card_numbers_data if card_data.get('id')]
            instance.card_numbers.exclude(id__in=card_number_ids).delete()
            for card_data in card_numbers_data:
                card_id = card_data.get('id')
                if card_id:
                    try:
                        card = instance.card_numbers.get(id=card_id)
                        card.card_number = card_data.get('card_number', card.card_number)
                        card.iban = card_data.get('iban', card.iban)
                        card.account_holder_name = card_data.get('account_holder_name', card.account_holder_name)
                        card.save()
                    except CardNumber.DoesNotExist:
                        CardNumber.objects.create(profile=instance, **card_data)
                else:
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
class JuridicalCardNumberSerializer(serializers.ModelSerializer):
    class Meta:
        model = JuridicalCardNumber
        fields = ['id', 'card_number', 'iban', 'account_holder_name']
        extra_kwargs = {
            'card_number': {'validators': [RegexValidator(regex=r'^\d{16}$', message=_('شماره کارت باید دقیقاً ۱۶ رقم باشد.'))]},
            'iban': {'validators': [RegexValidator(regex=r'^\d{24}$', message=_('شماره شبا باید دقیقاً ۲۴ رقم باشد.'))], 'required': False, 'allow_null': True},
            'account_holder_name': {'validators': [RegexValidator(regex=r'^[\u0600-\u06FF\s]+$', message=_('نام صاحب حساب فقط می‌تواند شامل حروف فارسی و فاصله باشد.'))]},
        }

class JuridicalProfileSerializer(serializers.ModelSerializer):
    documents = serializers.SerializerMethodField()
    image = serializers.ImageField(required=False, allow_empty_file=False, allow_null=True)
    card_numbers = serializers.SerializerMethodField()

    def get_card_numbers(self, obj):
        card_numbers = obj.card_numbers.all()
        return JuridicalCardNumberSerializer(card_numbers, many=True).data

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
            'card_numbers',
        ]
        extra_kwargs = {
            'address': {'required': False, 'allow_null': True},
            'email': {'required': False, 'allow_null': True},
            'reject_reason': {'required': False, 'allow_blank': True},
        }

    def get_image(self, obj):
        return obj.image.url if obj.image else None

    def get_documents(self, obj):
        request = self.context.get('request')
        documents = obj.documents.all()
        return JuridicalProfileDocumentSerializer(documents, many=True, context={'request': request}).data

    def validate(self, data):
        if data.get('status') == 'rejected' and not data.get('reject_reason', '').strip():
            raise serializers.ValidationError({
                'reject_reason': _('فیلد دلیل رد برای وضعیت رد شده الزامی است.')
            })

        if 'card_numbers' in data and data.get('card_numbers'):
            card_numbers = data['card_numbers']
            if len(card_numbers) > 2:
                raise serializers.ValidationError({'card_numbers': _('هر پروفایل حقوقی تنها می‌تواند حداکثر ۲ شماره کارت ثبت کند.')})

            for card in card_numbers:
                if 'card_number' not in card or not card['card_number']:
                    raise serializers.ValidationError({'card_numbers': _('شماره کارت الزامی است.')})
                if 'iban' in card and card['iban'] and not isinstance(card['iban'], (type(None), str)) or len(str(card['iban'])) != 24:
                    raise serializers.ValidationError({'card_numbers': _('شماره شبا باید ۲۴ رقم باشد یا خالی باشد.')})
                if 'account_holder_name' not in card or not card['account_holder_name']:
                    raise serializers.ValidationError({'card_numbers': _('نام صاحب حساب الزامی است.')})
                if 'id' in card and card['id']:
                    if self.instance:  # برای ویرایش، بررسی instance
                        try:
                            self.instance.card_numbers.get(id=card['id'])
                        except JuridicalCardNumber.DoesNotExist:
                            raise serializers.ValidationError({'card_numbers': _('شماره کارت با این id یافت نشد.')})
                    else:  # برای ایجاد، id نباید ارسال شود
                        raise serializers.ValidationError({'card_numbers': _('برای ایجاد جدید، id ارسال نکنید.')})
        return data

    def create(self, validated_data):
        card_numbers_data = validated_data.pop('card_numbers', [])
        image_data = validated_data.pop('image', None)
        profile = JuridicalProfile.objects.create(**validated_data)
        if image_data:
            profile.image = image_data
            profile.save()
        for card_data in card_numbers_data:
            try:
                JuridicalCardNumber.objects.create(profile=profile, **card_data)
            except IntegrityError as e:
                raise serializers.ValidationError({'card_numbers': _(f'خطا در ایجاد شماره کارت: {str(e)}')})
        return profile

    def update(self, instance, validated_data):
        card_numbers_data = validated_data.pop('card_numbers', None)
        image_data = validated_data.pop('image', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if image_data:
            instance.image = image_data
        instance.save()

        if card_numbers_data is not None:
            card_number_ids = [card_data.get('id') for card_data in card_numbers_data if card_data.get('id')]
            instance.card_numbers.exclude(id__in=card_number_ids).delete()

            for card_data in card_numbers_data:
                card_id = card_data.get('id')
                if card_id:
                    try:
                        card = instance.card_numbers.get(id=card_id)
                        card.card_number = card_data.get('card_number', card.card_number)
                        card.iban = card_data.get('iban', card.iban)
                        card.account_holder_name = card_data.get('account_holder_name', card.account_holder_name)
                        try:
                            card.save()
                        except IntegrityError as e:
                            raise serializers.ValidationError({'card_numbers': _(f'خطا در به‌روزرسانی شماره کارت: {str(e)}')})
                    except JuridicalCardNumber.DoesNotExist:
                        try:
                            JuridicalCardNumber.objects.create(profile=instance, **card_data)
                        except IntegrityError as e:
                            raise serializers.ValidationError({'card_numbers': _(f'خطا در ایجاد شماره کارت: {str(e)}')})
                else:
                    try:
                        JuridicalCardNumber.objects.create(profile=instance, **card_data)
                    except IntegrityError as e:
                        raise serializers.ValidationError({'card_numbers': _(f'خطا در ایجاد شماره کارت: {str(e)}')})
        return instance


# -----------------------------
# Card Number Management Serializers
# -----------------------------

class CardNumberSerializer(serializers.ModelSerializer):
    """
    سریالایزر برای مدیریت شماره کارت‌های حقیقی
    """
    class Meta:
        model = CardNumber
        fields = ['id', 'card_number', 'iban', 'account_holder_name']
        read_only_fields = ['id']

    def validate(self, attrs):
        """اعتبارسنجی محدودیت تعداد کارت‌ها"""
        request = self.context.get('request')
        profile = self.context.get('profile')
        
        # اگر در حال ایجاد هستیم (نه ویرایش)
        if not self.instance and profile:
            existing_count = profile.card_numbers.count()
            if existing_count >= 2:
                raise serializers.ValidationError(
                    _('هر کاربر تنها می‌تواند حداکثر ۲ شماره کارت ثبت کند.')
                )
        
        return attrs


class JuridicalCardNumberSerializer(serializers.ModelSerializer):
    """
    سریالایزر برای مدیریت شماره کارت‌های حقوقی
    """
    class Meta:
        model = JuridicalCardNumber
        fields = ['id', 'card_number', 'iban', 'account_holder_name']
        read_only_fields = ['id']

    def validate(self, attrs):
        """اعتبارسنجی محدودیت تعداد کارت‌ها"""
        profile = self.context.get('profile')
        
        # اگر در حال ایجاد هستیم (نه ویرایش)
        if not self.instance and profile:
            existing_count = profile.card_numbers.count()
            if existing_count >= 2:
                raise serializers.ValidationError(
                    _('هر پروفایل حقوقی تنها می‌تواند حداکثر ۲ شماره کارت ثبت کند.')
                )
        
        return attrs