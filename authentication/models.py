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
    """
    افزودن فیلدهای اضافی به Group برای گروه‌بندی اپلیکیشن‌ها
    """
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


# حذف مدل AppGroup قدیمی - حالا از GroupExtension استفاده می‌کنیم



LEGAL_PROFILE_STATUSES = (
    ('checking','در حال بررسی'),
    ('accpeted','تایید شده'),
    ('rejected','رد شده'),
)



class BaseUser(AbstractBaseUser, PermissionsMixin):
    phone_number = models.CharField(
        verbose_name=_('موبایل'),
        max_length=11,
        unique=True,
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
    # Stores the raw password if set_password() is called so that it can
    # be passed to password_changed() after the model is saved.
    _password = None

    objects = UserManager()

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "کاربر"
        verbose_name_plural = "کاربران"

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

    @property
    def is_staff(self):
        # اگر ادمین سایت باشد (Admin) یا سوپر یوزر باشد -> is_staff = True
        return self.is_superuser or hasattr(self, 'admin')

    def save(self, *args, **kwargs):
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
            # Password hash upgrades shouldn't be considered password changes.
            self._password = None
            self.save(update_fields=["password"])
        return check_password(raw_password, self.password, setter)

    def get_session_auth_hash(self):
        """Return an HMAC of the password field."""
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





#مدل پروفایل ادمین ها 
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
        verbose_name = "ادمین"
        verbose_name_plural = "ادمین‌ها"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    # مدیریت رمز عبور پنل گرافیکی
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
            if self.pk:  # اگر object ذخیره شده، update_fields استفاده کن
                self.save(update_fields=["panel_password"])
            else:
                self.save()
        return check_password(raw_password, self.panel_password, setter)
    
    
    


#پروفایل حقیقی کاربران
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
        help_text=_('اگر خالی باشد، سطح دائمی است. در غیر این صورت، پس از این تاریخ سطح به قبلی برمی‌گردد.'),
    )
    previous_level = models.ForeignKey(
        UserLevel,
        on_delete=models.SET_NULL,
        verbose_name=_('سطح قبلی'),
        related_name='previous_natural_profile',
        null=True,
        blank=True,
        help_text=_('سطح قبلی کاربر قبل از ارتقای موقتی'),
    )
    auto_renewal_enabled = models.BooleanField(
        default=False,
        verbose_name=_('تمدید خودکار اشتراک'),
        help_text=_('اگر فعال باشد، اشتراک به صورت خودکار از کیف پول تمدید می‌شود'),
    )
    manual_level_override = models.BooleanField(
        default=False,
        verbose_name=_('بازنویسی دستی سطح'),
        help_text=_('اگر فعال باشد، سطح کاربری بر اساس خرید آپدیت نمی‌شود و سطح دستی حفظ می‌گردد'),
    )
    subscription_package = models.ForeignKey(
        'user_subscription_settings.SubscriptionPackage',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('پکیج اشتراک فعلی'),
        help_text=_('پکیج اشتراکی که کاربر خریداری کرده'),
    )
    progress_target = models.DecimalField(
        verbose_name=_('هدف پیشرفت خرید'),
        max_digits=15,
        decimal_places=0,
        null=True,
        blank=True,
        help_text=_('مبلغ هدف برای ارتقای سطح در دوره زمانی مشخص'),
    )
    progress_deadline = models.DateField(
        verbose_name=_('ددلاین پیشرفت'),
        null=True,
        blank=True,
        help_text=_('تاریخ پایان دوره پیشرفت'),
    )

    class Meta:
        verbose_name = "پروفایل حقیقی"
        verbose_name_plural = "پروفایل‌ های حقیقی"
    
    def update_level(self):
        """به‌روزرسانی سطح کاربری بر اساس مجموع خرید"""
        from config.models import UserLevel
        from django.utils import timezone
        
        # اگر بازنویسی دستی فعال باشد، سطح را تغییر نده
        if self.manual_level_override:
            return
        
        # اول چک انقضا
        if self.expiration_date and self.expiration_date < timezone.now().date() and self.previous_level:
            self.level = self.previous_level
            self.previous_level = None
            self.expiration_date = None
            self.save(update_fields=['level', 'previous_level', 'expiration_date'])
            return
        
        # سپس ارتقا بر اساس خرید
        try:
            # اگر progress_target وجود داشته باشد، بر اساس آن ارتقا بده
            if self.progress_target and self.progress_deadline and timezone.now().date() <= self.progress_deadline:
                if self.total_purchase >= self.progress_target:
                    if self.level.title == 'میهمان':
                        level_title = 'نقره‌ای'
                    elif self.level.title == 'نقره‌ای':
                        level_title = 'طلایی'
                    else:
                        level_title = self.level.title  # بدون تغییر
                else:
                    level_title = self.level.title  # بدون تغییر
            else:
                # ارتقا بر اساس مجموع خرید (منطق قدیمی)
                if self.total_purchase >= 500000000:  # ۵۰۰ میلیون
                    level_title = 'طلایی'
                elif self.total_purchase >= 300000000:  # ۳۰۰ میلیون
                    level_title = 'نقره‌ای'
                else:
                    level_title = 'میهمان'
            
            level = UserLevel.objects.get(title=level_title)
            if self.level != level:
                self.level = level
                self.save(update_fields=['level'])
            
            # تنظیم هدف پیشرفت بر اساس سطح فعلی
            from datetime import timedelta
            if self.level.title == 'میهمان':
                self.progress_target = 300000000  # ۳۰۰ میلیون برای ارتقا به نقره‌ای
                self.progress_deadline = timezone.now().date() + timedelta(days=30)
            elif self.level.title == 'نقره‌ای':
                self.progress_target = 500000000  # ۵۰۰ میلیون برای ارتقا به طلایی
                self.progress_deadline = timezone.now().date() + timedelta(days=30)
            else:
                self.progress_target = None
                self.progress_deadline = None
            self.save(update_fields=['progress_target', 'progress_deadline'])
        except Exception as e:
            # اگر سطح وجود ندارد یا خطای دیگری رخ داد، لاگ کن
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"خطا در آپدیت سطح برای کاربر {self.base_user.phone_number}: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def __str__(self):
        return f'{self.base_user}'
    
    
    

#مدل ارسال رمز یکبار مصرف otp        
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





#مدل پروفایل حقوقی 
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
                'reject_reason': f'فیلد {self._meta.get_field("reject_reason").verbose_name} الزامی است.'
            })

    def __str__(self):
        return f'{self.organization_name}'


def juridical_profile_document_upload_to(instance, filename):
        try:
            return f'legal-profiles/documents/{instance.profile.natural_profile.base_user.pk}/{filename}'
        except:
            return f'legal-profiles/documents/default/{filename}'




#مدل مدارک حقوقی کاربران 
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
        validators=[
            FileSizeValidator(30),
        ],
    )

    class Meta:
        verbose_name = 'مدرک پروفایل حقوقی'
        verbose_name_plural = 'مدارک پروفایل حقوقی'

    def __str__(self):
        return f'مدرک {self.profile}'
    
    
    
    
    
    
# مدل شماره کارت های حقیقی 
# اعتبارسنجی برای شماره کارت (دقیقاً ۱۶ رقم)
validate_card_number = RegexValidator(
    regex=r'^\d{16}$',
    message=_('شماره کارت باید دقیقاً ۱۶ رقم باشد.')
)

# اعتبارسنجی برای شماره شبا (دقیقاً ۲۴ رقم)
validate_iban = RegexValidator(
    regex=r'^\d{24}$',
    message=_('شماره شبا باید دقیقاً ۲۴ رقم باشد.')
)

# اعتبارسنجی برای نام صاحب حساب (حروف فارسی و فاصله)
validate_account_holder_name = RegexValidator(
    regex=r'^[\u0600-\u06FF\s]+$',
    message=_('نام صاحب حساب فقط می‌تواند شامل حروف فارسی و فاصله باشد.')
)

class CardNumber(models.Model):
    profile = models.ForeignKey(
        NaturalProfile,
        on_delete=models.CASCADE,
        related_name='card_numbers',
        verbose_name=_('پروفایل کاربر'),
    )
    card_number = models.CharField(
        verbose_name=_('شماره کارت'),
        max_length=16,
        validators=(validate_card_number,),
        unique=True,
    )
    iban = models.CharField(
        verbose_name=_('شماره شبا'),
        max_length=24,
        validators=(validate_iban,),
        unique=True,
        null=True,
        blank=True,
    )
    account_holder_name = models.CharField(
        verbose_name=_('نام صاحب حساب'),
        max_length=100,
        validators=(validate_account_holder_name,),
        default='ناشناس',
    )

    class Meta:
        verbose_name = _('شماره کارت')
        verbose_name_plural = _('شماره‌های کارت')

    def clean(self):
        """
        هر کاربر فقط می‌تواند حداکثر ۲ شماره کارت داشته باشد.
        این اعتبارسنجی فقط زمانی انجام می‌شود که پروفایل ذخیره شده باشد.
        """
        if not self.profile_id or not self.profile.pk:
            return  # پروفایل هنوز ذخیره نشده، بررسی لازم نیست

        if self.pk is None and self.profile.card_numbers.count() >= 2:
            raise ValidationError(_('هر کاربر تنها می‌تواند حداکثر ۲ شماره کارت ثبت کند.'))

    def save(self, *args, **kwargs):
        # قبل از ذخیره اعتبارسنجی انجام بده
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        profile_str = f'Profile-{self.profile.pk}' if self.profile_id else "بدون پروفایل"
        return f'{self.card_number} - {self.account_holder_name} - {profile_str}'

    
    
    
    
    
# مدل شماره کارت های حقوقی 
# اعتبارسنجی برای شماره کارت (دقیقاً ۱۶ رقم)
validate_card_number = RegexValidator(
    regex=r'^\d{16}$',
    message=_('شماره کارت باید دقیقاً ۱۶ رقم باشد.')
)

# اعتبارسنجی برای شماره شبا (دقیقاً ۲۴ رقم)
validate_iban = RegexValidator(
    regex=r'^\d{24}$',
    message=_('شماره شبا باید دقیقاً ۲۴ رقم باشد.')
)

# اعتبارسنجی برای نام صاحب حساب (حروف فارسی و فاصله)
validate_account_holder_name = RegexValidator(
    regex=r'^[\u0600-\u06FF\s]+$',
    message=_('نام صاحب حساب فقط می‌تواند شامل حروف فارسی و فاصله باشد.')
)

class JuridicalCardNumber(models.Model):
    profile = models.ForeignKey(
        JuridicalProfile,
        on_delete=models.CASCADE,
        related_name='card_numbers',
        verbose_name=_('پروفایل حقوقی'),
    )
    card_number = models.CharField(
        verbose_name=_('شماره کارت'),
        max_length=16,
        validators=(validate_card_number,),
        unique=True,
    )
    iban = models.CharField(
        verbose_name=_('شماره شبا'),
        max_length=24,
        validators=(validate_iban,),
        unique=True,
        null=True,
        blank=True,
    )
    account_holder_name = models.CharField(
        verbose_name=_('نام صاحب حساب'),
        max_length=100,
        validators=(validate_account_holder_name,),
        
    )

    class Meta:
        verbose_name = _('شماره کارت حقوقی')
        verbose_name_plural = _('شماره‌های کارت حقوقی')

    def clean(self):
        # بررسی محدودیت تعداد کارت‌ها (حداکثر ۲ کارت)
        if self.profile.card_numbers.count() >= 2 and not self.pk:
            raise ValidationError(_('هر پروفایل حقوقی تنها می‌تواند حداکثر ۲ شماره کارت ثبت کند.'))

    def save(self, *args, **kwargs):
        # اجرای اعتبارسنجی قبل از ذخیره
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.card_number} - {self.account_holder_name} - {self.profile}'