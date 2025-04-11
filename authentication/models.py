from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth import password_validation
from django.utils.crypto import salted_hmac
from django.contrib.auth.hashers import (
    check_password,
    make_password,
)
from .managers import UserManager
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings
from django.core.validators import (
    MinLengthValidator,
    MaxLengthValidator,
)
from .validators import (
    validate_phone_number,
    validate_national_code,
    validate_postal_code,
    FileSizeValidator,
)
from config.models import (
    UserLevel,
)

LEGAL_PROFILE_STATUSES = (
    ('checking','در حال بررسی'),
    ('accpeted','تایید شده'),
    ('rejected','رد شده'),
)

class BaseUser(AbstractBaseUser, PermissionsMixin):
    phone_number = models.CharField(
        verbose_name=_('موبایل'),
        max_length=11,
        validators=(
            validate_phone_number,
        ),
        unique=True,
    )
    last_login = models.DateTimeField(
        verbose_name=_("last login"),
        blank=True,
        null=True,
    )
    date_joined = models.DateTimeField(
        verbose_name=_('تاریخ ثبت نام'),
        auto_now_add=True,
    )
    password = None

    @property
    def is_staff(self):
        return self.is_superuser

    objects = UserManager()

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "کاربر"
        verbose_name_plural = "کاربران"

    def __str__(self):
        return self.phone_number

class SuperUser(models.Model):
    base_user = models.OneToOneField(
        BaseUser,
        on_delete=models.CASCADE,
        related_name='superuser',
    )
    password = models.CharField(
        verbose_name=_('رمز عبور'),
        max_length=128,
    )
    # Stores the raw password if set_password() is called so that it can
    # be passed to password_changed() after the model is saved.
    _password = None

    class Meta:
        verbose_name = "ادمین جنگو"
        verbose_name_plural = "ادمین‌های جنگو"

    def __str__(self):
        return f'{self.base_user}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self._password is not None:
            password_validation.password_changed(self._password, self)
            self._password = None

    def set_password(self, raw_password):
        self.password = make_password(raw_password)
        self._password = raw_password

    def check_password(self, raw_password):
        def setter(raw_password):
            self.set_password(raw_password)
            # Password hash upgrades shouldn't be considered password changes.
            self._password = None
            self.save(update_fields=["password"])

        return check_password(raw_password, self.password, setter)

    def get_session_auth_hash(self):
        """
        Return an HMAC of the password field.
        """
        return self._get_session_auth_hash()

    def get_session_auth_fallback_hash(self):
        for fallback_secret in settings.SECRET_KEY_FALLBACKS:
            yield self._get_session_auth_hash(secret=fallback_secret)

    def _get_session_auth_hash(self, secret=None):
        key_salt = "authentication.SuperUser.get_session_auth_hash"
        return salted_hmac(
            key_salt,
            self.password,
            secret=secret,
            algorithm="sha256",
        ).hexdigest()
    
class Admin(models.Model):
    base_user = models.OneToOneField(
        BaseUser,
        on_delete=models.CASCADE,
        related_name='admin',
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
        validators=[
            FileSizeValidator(10),
        ],
    )
    signature = models.CharField(
        verbose_name=_('امضای ادمین'),
        max_length=512,
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "ادمین"
        verbose_name_plural = "ادمین‌ها"
    
    def __str__(self):
        return f'{self.base_user}'

class NaturalProfile(models.Model):
    base_user = models.OneToOneField(
        BaseUser,
        on_delete=models.CASCADE,
        related_name='natural_profile',
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
        validators=(
            validate_national_code,
        ),
        null=True,
        blank=True,
    )
    image = models.ImageField(
        verbose_name=_('عکس پروفایل'),
        upload_to='images/profiles/',
        null=True,
        blank=True,
        validators=[
            FileSizeValidator(10),
        ]
    )
    postal_code = models.CharField(
        verbose_name=_('کد پستی'),
        max_length=10,
        validators=(
            validate_postal_code,
        ),
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

    class Meta:
        verbose_name = "پروفایل کاربری"
        verbose_name_plural = "پروفایل‌های کاربری"
    
    def __str__(self):
        return f'{self.base_user}'
    
class OTP(models.Model):
    user = models.ForeignKey(
        BaseUser,
        verbose_name=_('user'),
        on_delete=models.CASCADE,
        related_name='otps',
    )
    code = models.CharField(
        verbose_name=_('code'),
        max_length=128,
    )
    created = models.DateTimeField(
        verbose_name=_('created'),
        auto_now_add=True,
    )

    class Meta:
        verbose_name = "رمز یک بار مصرف"
        verbose_name_plural = "رمزهای یک بار مصرف"
        ordering = ('-created',)
    
    @property
    def expired(self):
        return self.created + timezone.timedelta(minutes=settings.OTP_VALID_TIME)

    def set_code(self, code):
        self.code = make_password(code)

    def check_code(self, code):
        return check_password(code, self.code)

    def __str__(self):
        return f'OTP for {self.user}'

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
    registeration_number = models.CharField(
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
        validators=(
            validate_postal_code,
        ),
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
        validators=[
            FileSizeValidator(10),
        ]
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
        verbose_name = 'پروفایل حقوقی'
        verbose_name_plural = 'پروفایل‌های حقوقی'
    
    def clean(self):
        super().clean()

        if self.status == 'rejected' and not self.reject_reason.strip():
            raise ValidationError({
                'reject_reason': f'فیلد {self._meta.get_field('reject_reason').verbose_name} الزامی است.'
            })

    def __str__(self):
        return f'{self.organization_name}'

class JuridicalProfileDocument(models.Model):
    profile = models.ForeignKey(
        JuridicalProfile,
        on_delete=models.CASCADE,
        verbose_name=_('پروفایل حقوقی'),
        related_name='documents',
    )
    file = models.FileField(
        verbose_name=_('فایل مدارک'),
        upload_to='legal-profiles/documents/',
        validators=[
            FileSizeValidator(30),
        ],
    )

    class Meta:
        verbose_name = 'مدرک پروفایل حقوقی'
        verbose_name_plural = 'مدارک پروفایل حقوقی'

    def __str__(self):
        return f'مدرک {self.profile}'
