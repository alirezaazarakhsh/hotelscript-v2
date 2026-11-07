from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from .managers import UserManager
from setting_sms.models import SMSPattern
from icons.models import IconShortcut
from django.db import models
from django.conf import settings
from django.utils import timezone
from django_jalali.db import models as jmodels
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import password_validation
from django.utils.crypto import salted_hmac
from django.contrib.auth.hashers import (
    check_password,
    make_password,
)

from django.core.validators import (
    MinLengthValidator,
    MaxLengthValidator,
)

from .validators import (
    validate_national_code,
    validate_postal_code,
    FileSizeValidator,
)
from config.models import (
    UserLevel,
)


# مدل گروه‌بندی اپلیکیشن‌ها - حالا به Group متصل می‌شود
class GroupExtension(models.Model):
    group = models.OneToOneField(
        Group,
        on_delete=models.CASCADE,
        related_name='extension',
        verbose_name=_('گروه')
    )
    icon = models.ForeignKey(
        IconShortcut,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('آیکون'),
        help_text=_('آیکون این گروه')
    )
    order = models.IntegerField(
        default=0,
        verbose_name=_('ترتیب نمایش'),
        help_text=_('عدد کوچکتر = اولویت بالاتر')
    )
    display_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('نام نمایشی فارسی'),
        help_text=_('نام فارسی گروه برای نمایش')
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('توضیحات'),
    )

    class Meta:
        verbose_name = "تنظیمات گروه"
        verbose_name_plural = "تنظیمات گروه‌ها"
        ordering = ['order', 'group__name']

    def __str__(self):
        return self.display_name or self.group.name


LEGAL_PROFILE_STATUSES = (
    ('checking','در حال بررسی'),
    ('accpeted','تایید شده'),
    ('rejected','رد شده'),
)


# ۱. کاربران پایه (بالاترین اولویت)
class BaseUser(AbstractBaseUser, PermissionsMixin):
    phone_number = models.CharField(
        verbose_name=_('موبایل'),
        max_length=11,
        unique=True,
    )
    is_active = models.BooleanField(
        verbose_name=_('فعال'),
        default=True,
    )
    is_staff = models.BooleanField(
        verbose_name=_('کارمند / دسترسی پنل'),
        default=False,
    )
    date_joined = jmodels.jDateTimeField(
        verbose_name=_('تاریخ ثبت نام'),
        auto_now_add=True,
    )
    last_login = jmodels.jDateTimeField(
        verbose_name=_('آخرین ورود'),
        null=True,
        blank=True,
    )
    password = models.CharField(
        verbose_name=_('رمز عبور جنگو'),
        max_length=128,
        null=True,
        blank=True,
        help_text=_('رمز عبور برای ورود به پنل جنگو (فقط برای سوپر یوزرها)')
    )
    _password = None

    objects = UserManager()

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "01- کاربر پایه"
        verbose_name_plural = "01- کاربران پایه"

    def __str__(self):
        profile_name = ""
        if hasattr(self, 'natural_profile') and self.natural_profile:
            profile_name = f"{self.natural_profile.first_name or ''} {self.natural_profile.last_name or ''}".strip()
        elif hasattr(self, 'admin') and self.admin:
            profile_name = f"{self.admin.first_name or ''} {self.admin.last_name or ''}".strip()
        
        if profile_name:
            return f"{self.phone_number} ({profile_name})"
        return self.phone_number

    @property
    def first_name(self):
        if hasattr(self, 'admin') and self.admin:
            return self.admin.first_name
        elif hasattr(self, 'natural_profile') and self.natural_profile:
            return self.natural_profile.first_name
        return None

    @property
    def last_name(self):
        if hasattr(self, 'admin') and self.admin:
            return self.admin.last_name
        elif hasattr(self, 'natural_profile') and self.natural_profile:
            return self.natural_profile.last_name
        return None

    def save(self, *args, **kwargs):
        if self.is_superuser or hasattr(self, 'admin') and self.admin:
            self.is_staff = True
            
        super().save(*args, **kwargs)
        if self._password is not None:
            password_validation.password_changed(self._password, self)
            self._password = None

    def set_password(self, raw_password):
        self.password = make_password(raw_password)
        self._password = raw_password

    def check_password(self, raw_password):
        if not self.password:
            return False
        def setter(raw_password):
            self.set_password(raw_password)
            self._password = None
            self.save(update_fields=["password"])
        return check_password(raw_password, self.password, setter)

    def get_session_auth_hash(self):
        return self._get_session_auth_hash()

    def get_session_auth_fallback_hash(self):
        for fallback_secret in settings.SECRET_KEY_FALLBACKS:
            yield self._get_session_auth_hash(secret=fallback_secret)

    def _get_session_auth_hash(self, secret=None):
        key_salt = "authentication.BaseUser.get_session_auth_hash"
        return salted_hmac(
            key_salt,
            self.password or '',
            secret=secret,
            algorithm="sha256",
        ).hexdigest()


# ۲. ادمین‌های سایت
class Admin(models.Model):
    base_user = models.OneToOneField(
        BaseUser,  
        on_delete=models.CASCADE,
        related_name='admin',
        verbose_name=_('کاربر گرامی '),
    )
    first_name = models.CharField(
        verbose_name=_('نام'),
        max_length=32,
        null=True,
        blank=True,
    )
    last_name = models.CharField(
        verbose_name=_('نام خانوادگی'),
        max_length=32,
        null=True,
        blank=True,
    )
    image = models.ImageField(
        verbose_name=_('عکس پروفایل'),
        upload_to='images/profiles/',
        null=True,
        blank=True,
        validators=[FileSizeValidator(10)],
    )
    signature = models.CharField(
        verbose_name=_('امضای ادمین'),
        max_length=512,
        null=True,
        blank=True,
    )
    panel_password = models.CharField(
        verbose_name=_('رمز عبور پنل گرافیکی'),
        max_length=128,
        null=True,
        blank=True,
        help_text=_('رمز عبور برای ورود به پنل گرافیکی ادمین (غیر از پنل جنگو)')
    )
    sms_patterns = models.ManyToManyField(
        SMSPattern,
        verbose_name="پترن‌های پیامکی فعال",
        blank=True,
        help_text="پترن‌های پیامکی که برای این ادمین فعال هستند را انتخاب کنید."
    )

    class Meta:
        verbose_name = "02- ادمین سایت"
        verbose_name_plural = "02- ادمین‌های سایت"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    _password = None

    def set_panel_password(self, raw_password):
        self.panel_password = make_password(raw_password)
        self._password = raw_password

    def check_panel_password(self, raw_password):
        if not self.panel_password:
            return False
        def setter(raw_password):
            self.set_panel_password(raw_password)
            self._password = None
            if self.pk:
                self.save(update_fields=["panel_password"])
            else:
                self.save()
        return check_password(raw_password, self.panel_password, setter)


# ۳. پروفایل حقیقی کاربران
class NaturalProfile(models.Model):
    base_user = models.OneToOneField(
        BaseUser,
        on_delete=models.CASCADE,
        related_name='natural_profile',
        verbose_name=_('کاربرگرامی'),
    )
    first_name = models.CharField(
        verbose_name=_('نام'),
        max_length=32,
        null=True,
        blank=True,
    )
    last_name = models.CharField(
        verbose_name=_('نام خانوادگی'),
        max_length=32,
        null=True,
        blank=True,
    )
    email = models.EmailField(
        verbose_name=_('ایمیل'),
        null=True,
        blank=True,
    )
    national_code = models.CharField(
        verbose_name=_('کد ملی'),
        max_length=10,
        validators=(validate_national_code,),
        null=True,
        blank=True,
    )
    image = models.ImageField(
        verbose_name=_('عکس پروفایل'),
        upload_to='images/profiles/',
        null=True,
        blank=True,
        validators=[FileSizeValidator(10)]
    )
    postal_code = models.CharField(
        verbose_name=_('کد پستی'),
        max_length=10,
        validators=(validate_postal_code,),
        null=True,
        blank=True,
    )
    address = models.CharField(
        verbose_name=_('آدرس مسکونی'),
        max_length=256,
        null=True,
        blank=True,
    )
    created = models.DateTimeField(
        verbose_name=_('تاریخ ایجاد'),
        auto_now_add=True,
    )
    level = models.ForeignKey(
        UserLevel,
        on_delete=models.SET_NULL,
        verbose_name=_('سطح کاربری'),
        related_name='natural_profile',
        null=True,
    )
    total_purchase = models.DecimalField(
        verbose_name=_('مجموع خرید'),
        max_digits=15,
        decimal_places=0,
        default=0,
        help_text=_('مجموع مبلغ خریدهای موفق (تومان)'),
    )
    expiration_date = jmodels.jDateField(
        verbose_name=_('تاریخ انقضای سطح'),
        null=True,
        blank=True,
        help_text=_('اگر خالی باشد، سطح دائمی است.'),
    )
    previous_level = models.ForeignKey(
        UserLevel,
        on_delete=models.SET_NULL,
        verbose_name=_('سطح قبلی'),
        related_name='previous_natural_profile',
        null=True,
        blank=True,
    )
    auto_renewal_enabled = models.BooleanField(
        default=False,
        verbose_name=_('تمدید خودکار اشتراک'),
    )
    manual_level_override = models.BooleanField(
        default=False,
        verbose_name=_('بازنویسی دستی سطح'),
    )
    subscription_package = models.ForeignKey(
        'user_subscription_settings.SubscriptionPackage',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('پکیج اشتراک فعلی'),
    )
    progress_target = models.DecimalField(
        verbose_name=_('هدف پیشرفت خرید'),
        max_digits=15,
        decimal_places=0,
        null=True,
        blank=True,
    )
    progress_deadline = models.DateField(
        verbose_name=_('ددلاین پیشرفت'),
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "03- پروفایل حقیقی"
        verbose_name_plural = "03- پروفایل‌های حقیقی"

    def __str__(self):
        return f'{self.base_user}'


# ۴. پروفایل حقوقی
class JuridicalProfile(models.Model):
    natural_profile = models.OneToOneField(
        NaturalProfile,
        on_delete=models.CASCADE,
        verbose_name=_('پروفایل حقیقی'),
        related_name='juridical_profile',
    )
    organization_name = models.CharField(
        verbose_name=_('نام شرکت'),
        max_length=64,
    )
    national_id = models.CharField(
        verbose_name=_('شناسه ملی'),
        max_length=11,
        unique=True,
        validators=(
            MinLengthValidator(11, 'شناسه ملی 11 رقمی است.'),
            MaxLengthValidator(11, 'شناسه ملی 11 رقمی است.'),
        ),
    )
    registration_number = models.CharField(
        verbose_name=_('شماره ثبت'),
        max_length=16,
    )
    economical_code = models.CharField(
        verbose_name=_('کد اقتصادی'),
        max_length=16,
    )
    phone_number = models.CharField(
        verbose_name=_('شماره تماس'),
        max_length=11,
    )
    postal_code = models.CharField(
        verbose_name=_('کد پستی'),
        max_length=10,
        validators=(validate_postal_code,),
    )
    address = models.CharField(
        verbose_name=_('آدرس'),
        max_length=256,
        null=True,
        blank=True,
    )
    email = models.EmailField(
        verbose_name=_('ایمیل'),
        null=True,
        blank=True,
    )
    image = models.ImageField(
        verbose_name=_('عکس شرکت'),
        upload_to='images/juridical-profiles/',
        null=True,
        blank=True,
        validators=[FileSizeValidator(10)]
    )
    status = models.CharField(
        verbose_name=_('وضعیت'),
        max_length=16,
        choices=LEGAL_PROFILE_STATUSES,
        default='checking',
    )
    reject_reason = models.TextField(
        verbose_name=_('دلیل رد'),
        blank=True,
        default='',
    )
    created = models.DateTimeField(
        verbose_name=_('تاریخ ثبت نام'),
        auto_now_add=True,
    )

    class Meta:
        verbose_name = '04- پروفایل حقوقی'
        verbose_name_plural = '04- پروفایل‌های حقوقی'

    def clean(self):
        super().clean()
        if self.status == 'rejected' and not self.reject_reason.strip():
            raise ValidationError({
                'reject_reason': f'فیلد {self._meta.get_field("reject_reason").verbose_name} الزامی است.'
            })

    def __str__(self):
        return f'{self.organization_name}'


def juridical_profile_document_upload_to(instance, filename):
    try:
        return f'legal-profiles/documents/{instance.profile.natural_profile.base_user.pk}/{filename}'
    except:
        return f'legal-profiles/documents/default/{filename}'


class JuridicalProfileDocument(models.Model):
    profile = models.ForeignKey(
        JuridicalProfile,
        on_delete=models.CASCADE,
        verbose_name=_('پروفایل حقوقی'),
        related_name='documents',
    )
    file = models.FileField(
        verbose_name=_('فایل مدارک'),
        upload_to=juridical_profile_document_upload_to,
        validators=[FileSizeValidator(30)],
    )

    class Meta:
        verbose_name = '05- مدرک پروفایل حقوقی'
        verbose_name_plural = '05- مدارک پروفایل‌های حقوقی'

    def __str__(self):
        return f'مدرک {self.profile}'


# ۵. کارت‌ها و سایر موارد
validate_card_number = RegexValidator(regex=r'^\d{16}$', message=_('شماره کارت باید دقیقاً ۱۶ رقم باشد.'))
validate_iban = RegexValidator(regex=r'^\d{24}$', message=_('شماره شبا باید دقیقاً ۲۴ رقم باشد.'))
validate_account_holder_name = RegexValidator(regex=r'^[\u0600-\u06FF\s]+$', message=_('نام صاحب حساب فقط می‌تواند شامل حروف فارسی و فاصله باشد.'))

class CardNumber(models.Model):
    profile = models.ForeignKey(NaturalProfile, on_delete=models.CASCADE, related_name='card_numbers', verbose_name=_('پروفایل کاربر'))
    card_number = models.CharField(verbose_name=_('شماره کارت'), max_length=16, validators=(validate_card_number,), unique=True)
    iban = models.CharField(verbose_name=_('شماره شبا'), max_length=24, validators=(validate_iban,), unique=True, null=True, blank=True)
    account_holder_name = models.CharField(verbose_name=_('نام صاحب حساب'), max_length=100, validators=(validate_account_holder_name,), default='ناشناس')

    class Meta:
        verbose_name = _('06- شماره کارت حقیقی')
        verbose_name_plural = _('06- شماره‌های کارت حقیقی')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.card_number}'


class JuridicalCardNumber(models.Model):
    profile = models.ForeignKey(JuridicalProfile, on_delete=models.CASCADE, related_name='card_numbers', verbose_name=_('پروفایل حقوقی'))
    card_number = models.CharField(verbose_name=_('شماره کارت'), max_length=16, validators=(validate_card_number,), unique=True)
    iban = models.CharField(verbose_name=_('شماره شبا'), max_length=24, validators=(validate_iban,), unique=True, null=True, blank=True)
    account_holder_name = models.CharField(verbose_name=_('نام صاحب حساب'), max_length=100, validators=(validate_account_holder_name,))

    class Meta:
        verbose_name = _('07- شماره کارت حقوقی')
        verbose_name_plural = _('07- شماره‌های کارت حقوقی')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.card_number}'


class OTP(models.Model):
    user = models.ForeignKey(BaseUser, verbose_name=_('user'), on_delete=models.CASCADE, related_name='otps')
    code = models.CharField(verbose_name=_('code'), max_length=128)
    created = models.DateTimeField(verbose_name=_('created'), auto_now_add=True)

    class Meta:
        verbose_name = "08- رمز یک بار مصرف"
        verbose_name_plural = "08- رمزهای یک بار مصرف"
        ordering = ('-created',)

    def __str__(self):
        return f'OTP for {self.user}'