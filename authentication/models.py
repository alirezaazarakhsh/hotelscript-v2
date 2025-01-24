from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import (
    check_password,
    make_password,
)
from .managers import UserManager
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings
from .validators import validate_phone_number, validate_national_code


class User(AbstractBaseUser, PermissionsMixin):
    first_name = models.CharField(verbose_name=_('نام'), max_length=32, null=True, blank=True)
    last_name = models.CharField(verbose_name=_('نام خانوادگی'), max_length=32, null=True, blank=True)
    password = models.CharField(verbose_name=_('رمز عبور'), max_length=128, null=True, blank=True)
    email = models.EmailField(verbose_name=_('ایمیل'), unique=True, null=True, blank=True)
    phone_number = models.CharField(verbose_name=_('موبایل'), max_length=11, validators=(validate_phone_number,), unique=True, null=True, blank=True)
    national_code = models.CharField(verbose_name=_('کد ملی'), max_length=10, validators=(validate_national_code,), unique=True, null=True, blank=True)
    is_staff = models.BooleanField(verbose_name=_('دسترسی به ادمین جنگو'), default=False)
    is_active = models.BooleanField(verbose_name=_('فعال'), default=True)
    date_joined = models.DateTimeField(verbose_name=_('تاریخ ثبت نام'), auto_now_add=True)

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        pass

    def clean(self):
        qs = User.objects.exclude(pk=self.pk).filter(phone_number=self.phone_number)
        if self.phone_number and qs.exists():
            raise ValidationError({
                'phone_number':'User with this Phone number already exists.'
            })
        qs = User.objects.exclude(pk=self.pk).filter(email=self.email)
        if self.email and qs.exists():
            raise ValidationError({
                'email':'User with this Email already exists.'
            })
        if not (self.email or self.phone_number):
            raise ValidationError('Email or Phone number is required')
    
    def __str__(self):
        return self.phone_number or self.email
    
class OTP(models.Model):
    user = models.ForeignKey(User, verbose_name=_('user'), on_delete=models.CASCADE, related_name='otps')
    code = models.CharField(verbose_name=_('code'), max_length=128)
    created = models.DateTimeField(verbose_name=_('created'), auto_now_add=True)

    class Meta:
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